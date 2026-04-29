#!/usr/bin/env python3
"""Luo OS REST API v0.2 — Port 8080"""
import json, os, sys, subprocess, urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_core.agent_identity import LuoIdentity

VERSION = "0.2"
PORT    = 8080

class LuoRESTHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] REST {args[0]} {args[1]}")
    def send_json(self, data, code=200):
        body = json.dumps(data, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
    def _token(self):
        auth  = self.headers.get("Authorization","").replace("Bearer ","").strip()
        token = auth or self.headers.get("X-Luo-Token","").strip()
        return LuoIdentity.validate_token(token) if token else {}
    def _params(self): return parse_qs(urlparse(self.path).query)
    def _body(self):
        n = int(self.headers.get("Content-Length",0))
        return json.loads(self.rfile.read(n)) if n else {}
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type,Authorization,X-Luo-Token")
        self.end_headers()
    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path=="/":
            self.send_json({"name":"Luo OS REST API","version":VERSION,
                "author":"Abd El-Rahman Abbas (Mr. Kai)","port":PORT,
                "endpoints":{"GET /":"info","GET /status":"status","GET /agents":"agents",
                "GET /files?path=/":"list dir","GET /read?path=/f":"read file",
                "POST /provision":"get identity","POST /run":"run command (token)",
                "POST /ai":"ask AI (token)","POST /memory/write":"save fact (token)",
                "GET /memory/read":"read memory (token)"}})
        elif path=="/status":
            self.send_json({"status":"running","os":"Luo OS","version":VERSION,
                "time":datetime.now().isoformat(),"agents":len(LuoIdentity.list_agents())})
        elif path=="/agents":
            agents=LuoIdentity.list_agents()
            self.send_json({"count":len(agents),"agents":[
                {"id":a["agent_id"],"name":a["agent_name"],"model":a["model"],"runs":a["run_count"]} for a in agents]})
        elif path=="/files":
            p=self._params().get("path",["/"])[0]
            try:
                items=[{"name":i,"type":"dir" if os.path.isdir(os.path.join(p,i)) else "file",
                        "size":os.path.getsize(os.path.join(p,i)) if os.path.isfile(os.path.join(p,i)) else 0}
                       for i in sorted(os.listdir(p))]
                self.send_json({"path":p,"items":items})
            except Exception as e: self.send_json({"error":str(e)},400)
        elif path=="/read":
            fp=self._params().get("path",[""])[0]
            try: self.send_json({"path":fp,"content":Path(fp).read_text(errors="replace")})
            except Exception as e: self.send_json({"error":str(e)},400)
        elif path=="/memory/read":
            agent=self._token()
            if not agent: self.send_json({"error":"Token required"},401); return
            try: self.send_json({"memory":(Path(agent["memory_dir"])/"MEMORY.md").read_text()})
            except Exception as e: self.send_json({"error":str(e)},500)
        else: self.send_json({"error":"Not found"},404)
    def do_POST(self):
        path=urlparse(self.path).path.rstrip("/"); body=self._body()
        if path=="/provision":
            try:
                identity=LuoIdentity.provision(agent_name=body.get("agent_name",""),
                    model=body.get("model",""),agent_type=body.get("agent_type","unknown"))
                self.send_json({"agent_id":identity.agent_id,"api_token":identity.api_token,
                    "memory_dir":str(identity.memory_dir),"run_count":identity.run_count,
                    "message":f"Welcome to Luo OS, {identity.agent_name}!"})
            except Exception as e: self.send_json({"error":str(e)},500)
            return
        agent=self._token()
        if not agent:
            self.send_json({"error":"Token required. POST /provision first."},401); return
        if path=="/run":
            cmd=body.get("command","")
            if not cmd: self.send_json({"error":"No command"},400); return
            try:
                r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=30)
                self.send_json({"stdout":r.stdout,"stderr":r.stderr,"returncode":r.returncode})
            except Exception as e: self.send_json({"error":str(e)},500)
        elif path=="/ai":
            prompt=body.get("prompt",""); model=body.get("model","tinyllama")
            if not prompt: self.send_json({"error":"No prompt"},400); return
            try:
                payload=json.dumps({"model":model,"messages":[
                    {"role":"system","content":"You are Luo, the AI core of Luo OS. Be concise."},
                    {"role":"user","content":prompt}],"stream":False,"options":{"num_predict":512}}).encode()
                req=urllib.request.Request("http://127.0.0.1:3000/api/chat",data=payload,
                    headers={"Content-Type":"application/json"})
                with urllib.request.urlopen(req,timeout=120) as r:
                    result=json.loads(r.read())
                self.send_json({"response":result.get("message",{}).get("content","").strip()})
            except Exception as e: self.send_json({"error":f"AI unavailable: {e}"},503)
        elif path=="/memory/write":
            fact=body.get("fact","")
            if not fact: self.send_json({"error":"No fact"},400); return
            try:
                mem=Path(agent["memory_dir"])/"MEMORY.md"
                with open(mem,"a") as f: f.write(f"- [{datetime.now().strftime('%Y-%m-%d %H:%M')}] {fact.strip()}\n")
                self.send_json({"status":"ok"})
            except Exception as e: self.send_json({"error":str(e)},500)
        else: self.send_json({"error":"Not found"},404)

def start_rest_api():
    server=HTTPServer(("0.0.0.0",PORT),LuoRESTHandler)
    print(f"Luo OS REST API v{VERSION} — http://0.0.0.0:{PORT}")
    server.serve_forever()

if __name__=="__main__": start_rest_api()
