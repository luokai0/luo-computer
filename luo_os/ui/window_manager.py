import threading
import json
#!/usr/bin/env python3
"""
Luo OS Desktop Window Manager
Author: Abd El-Rahman Abbas (Mr. Kai)
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess, json, os, threading
from datetime import datetime
from pathlib import Path

BG="#0a0a1a"; BG2="#0f0f2a"; ACCENT="#00d4ff"; ACCENT2="#7c3aed"
TEXT="#e2e8f0"; DIM="#64748b"; GREEN="#22c55e"; RED="#ef4444"; YELLOW="#eab308"
FONT=("Courier",10); FONT_SM=("Courier",9); FONT_LG=("Courier",14)

class LuoWindow:
    def __init__(self, desktop, title, width=500, height=400):
        self.desktop=desktop
        self.frame=tk.Frame(desktop.canvas,bg=BG2,highlightbackground=ACCENT,highlightthickness=1)
        self.frame.place(x=100+len(desktop.windows)*30,y=80+len(desktop.windows)*30,width=width,height=height)
        self.titlebar=tk.Frame(self.frame,bg=ACCENT2,height=28)
        self.titlebar.pack(fill=tk.X); self.titlebar.pack_propagate(False)
        tk.Label(self.titlebar,text=title,bg=ACCENT2,fg=TEXT,font=FONT_SM).pack(side=tk.LEFT,padx=8)
        tk.Button(self.titlebar,text="x",bg=RED,fg="white",font=FONT_SM,relief=tk.FLAT,width=3,command=self.close).pack(side=tk.RIGHT,padx=2,pady=2)
        tk.Button(self.titlebar,text="-",bg=DIM,fg="white",font=FONT_SM,relief=tk.FLAT,width=3,command=self.minimize).pack(side=tk.RIGHT,padx=2,pady=2)
        self.content=tk.Frame(self.frame,bg=BG2); self.content.pack(fill=tk.BOTH,expand=True)
        self.titlebar.bind("<ButtonPress-1>",self._ds); self.titlebar.bind("<B1-Motion>",self._dm)
        self._dx=self._dy=0; desktop.windows.append(self)
    def _ds(self,e): self._dx,self._dy=e.x,e.y
    def _dm(self,e):
        x=self.frame.winfo_x()+e.x-self._dx; y=self.frame.winfo_y()+e.y-self._dy
        self.frame.place(x=x,y=y)
    def minimize(self): self.frame.place_forget()
    def close(self):
        self.frame.destroy()
        if self in self.desktop.windows: self.desktop.windows.remove(self)

class LuoDesktop:
    def __init__(self):
        self.root=tk.Tk(); self.root.title("Luo OS v0.1"); self.root.configure(bg=BG)
        sw=self.root.winfo_screenwidth(); sh=self.root.winfo_screenheight()
        self.root.geometry(f"{sw}x{sh}+0+0"); self.windows=[]
        self._setup_desktop(); self._setup_taskbar(); self._setup_icons(); self._clock_tick()

    def _setup_desktop(self):
        self.canvas=tk.Frame(self.root,bg=BG); self.canvas.pack(fill=tk.BOTH,expand=True)
        tk.Label(self.canvas,text="LUO OS",font=("Courier",48,"bold"),bg=BG,fg="#ffffff08").place(relx=0.5,rely=0.5,anchor=tk.CENTER)

    def _setup_taskbar(self):
        self.taskbar=tk.Frame(self.root,bg=BG2,height=48); self.taskbar.pack(side=tk.BOTTOM,fill=tk.X); self.taskbar.pack_propagate(False)
        tk.Button(self.taskbar,text=" Luo OS ",bg=ACCENT2,fg=TEXT,font=FONT,relief=tk.FLAT,command=self._launcher).pack(side=tk.LEFT,padx=4,pady=6)
        for label,cmd in [("Agent",self.open_ai),("Files",self.open_files),("Editor",self.open_editor),("Terminal",self.open_terminal),("Packages",self.open_pkg)]:
            tk.Button(self.taskbar,text=label,bg=BG,fg=ACCENT,font=FONT_SM,relief=tk.FLAT,command=cmd).pack(side=tk.LEFT,padx=2,pady=6)
        self.clock=tk.Label(self.taskbar,text="",bg=BG2,fg=DIM,font=FONT_SM); self.clock.pack(side=tk.RIGHT,padx=12)
        tk.Label(self.taskbar,text="Luo OS running",bg=BG2,fg=GREEN,font=FONT_SM).pack(side=tk.RIGHT,padx=8)

    def _setup_icons(self):
        icons=[("Agent",self.open_ai),("Files",self.open_files),("Editor",self.open_editor),
               ("Terminal",self.open_terminal),("Browser",self.open_browser),("Packages",self.open_pkg),("Settings",self.open_settings)]
        f=tk.Frame(self.canvas,bg=BG); f.place(x=20,y=20)
        for i,(label,cmd) in enumerate(icons):
            tk.Button(f,text=label,bg=BG,fg=TEXT,font=FONT_SM,relief=tk.FLAT,width=8,height=2,
                      activebackground=BG2,activeforeground=ACCENT,command=cmd).grid(row=i,column=0,pady=3,padx=4)

    def _clock_tick(self):
        self.clock.config(text=datetime.now().strftime("%H:%M:%S  %Y-%m-%d")); self.root.after(1000,self._clock_tick)

    def _launcher(self):
        win=LuoWindow(self,"Luo OS",300,380)
        for label,cmd in [("Luo Agent",self.open_ai),("File Manager",self.open_files),("Text Editor",self.open_editor),
                           ("Terminal",self.open_terminal),("Browser",self.open_browser),("Packages",self.open_pkg),("Settings",self.open_settings)]:
            tk.Button(win.content,text=label,bg=BG2,fg=TEXT,font=FONT,relief=tk.FLAT,anchor=tk.W,
                      activebackground=ACCENT2,activeforeground=TEXT,
                      command=lambda c=cmd:[c(),win.close()]).pack(fill=tk.X,padx=8,pady=2)

    def open_ai(self):
        win=LuoWindow(self,"Luo Agent",600,480)
        ctrl=tk.Frame(win.content,bg=BG2); ctrl.pack(fill=tk.X,padx=8,pady=4)
        tk.Label(ctrl,text="Model:",bg=BG2,fg=DIM,font=FONT_SM).pack(side=tk.LEFT)
        mv=tk.StringVar(value="tinyllama")
        ttk.Combobox(ctrl,textvariable=mv,values=["tinyllama","phi3:mini","gemma2:2b","qwen2.5:1.5b","mistral"],width=18,font=FONT_SM).pack(side=tk.LEFT,padx=4)
        chat=scrolledtext.ScrolledText(win.content,bg=BG,fg=TEXT,font=FONT_SM,relief=tk.FLAT,state=tk.DISABLED)
        chat.pack(fill=tk.BOTH,expand=True,padx=8,pady=4)
        chat.tag_config("you",foreground=ACCENT); chat.tag_config("luo",foreground=GREEN); chat.tag_config("err",foreground=RED)
        inf=tk.Frame(win.content,bg=BG2); inf.pack(fill=tk.X,padx=8,pady=4)
        inp=tk.Entry(inf,bg=BG,fg=TEXT,font=FONT,insertbackground=ACCENT,relief=tk.FLAT)
        inp.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=(0,4))
        def append(text,tag=""):
            chat.config(state=tk.NORMAL); chat.insert(tk.END,text,tag); chat.see(tk.END); chat.config(state=tk.DISABLED)
        def send(e=None):
            msg=inp.get().strip()
            if not msg: return
            inp.delete(0,tk.END); append(f"you > {msg}\n","you")
            model=mv.get()
            def _r():
                try:
                    import urllib.request
                    payload=json.dumps({"model":model,"messages":[{"role":"system","content":"You are Luo, AI core of Luo OS. Be concise."},{"role":"user","content":msg}],"stream":False,"options":{"num_predict":256}}).encode()
                    req=urllib.request.Request("http://localhost:3000/api/chat",data=payload,headers={"Content-Type":"application/json"})
                    with urllib.request.urlopen(req,timeout=120) as r: result=json.loads(r.read())
                    resp=result.get("message",{}).get("content","").strip()
                    win.content.after(0,lambda:append(f"luo  > {resp}\n\n","luo"))
                except Exception as ex:
                    win.content.after(0,lambda:append(f"[error] {ex}\n","err"))
            threading.Thread(target=_r,daemon=True).start()
        inp.bind("<Return>",send)
        tk.Button(inf,text="Send",bg=ACCENT2,fg=TEXT,font=FONT_SM,relief=tk.FLAT,command=send).pack(side=tk.RIGHT)
        append("Luo Agent ready. Type a message.\n\n"); inp.focus()

    def open_terminal(self):
        win=LuoWindow(self,"Terminal",600,400)
        out=scrolledtext.ScrolledText(win.content,bg="#000000",fg=GREEN,font=FONT,relief=tk.FLAT)
        out.pack(fill=tk.BOTH,expand=True,padx=4,pady=4)
        out.tag_config("err",foreground=RED); out.tag_config("p",foreground=ACCENT)
        inf=tk.Frame(win.content,bg="#000000"); inf.pack(fill=tk.X,padx=4,pady=4)
        tk.Label(inf,text="$",bg="#000000",fg=GREEN,font=FONT).pack(side=tk.LEFT)
        inp=tk.Entry(inf,bg="#000000",fg=GREEN,font=FONT,insertbackground=GREEN,relief=tk.FLAT)
        inp.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=4)
        def run(e=None):
            cmd=inp.get().strip()
            if not cmd: return
            inp.delete(0,tk.END); out.insert(tk.END,f"$ {cmd}\n","p")
            def _r():
                try:
                    r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=30)
                    if r.stdout: out.after(0,lambda:out.insert(tk.END,r.stdout))
                    if r.stderr: out.after(0,lambda:out.insert(tk.END,r.stderr,"err"))
                except Exception as ex:
                    out.after(0,lambda:out.insert(tk.END,f"[error] {ex}\n","err"))
                out.after(0,lambda:out.see(tk.END))
            threading.Thread(target=_r,daemon=True).start()
        inp.bind("<Return>",run)
        out.insert(tk.END,"Luo OS Terminal\n\n"); inp.focus()

    def open_files(self):
        win=LuoWindow(self,"File Manager",500,400)
        path_var=tk.StringVar(value=str(Path.cwd()))
        ctrl=tk.Frame(win.content,bg=BG2); ctrl.pack(fill=tk.X,padx=4,pady=4)
        path_entry=tk.Entry(ctrl,textvariable=path_var,bg=BG,fg=TEXT,font=FONT_SM,relief=tk.FLAT)
        path_entry.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=4)
        lb=tk.Listbox(win.content,bg=BG,fg=TEXT,font=FONT_SM,selectbackground=ACCENT2,relief=tk.FLAT)
        lb.pack(fill=tk.BOTH,expand=True,padx=8,pady=4)
        def refresh(e=None):
            lb.delete(0,tk.END)
            try:
                p=Path(path_var.get())
                lb.insert(tk.END,".. (up)")
                for item in sorted(p.iterdir()):
                    prefix="[D] " if item.is_dir() else "[F] "
                    lb.insert(tk.END,prefix+item.name)
            except Exception as ex:
                lb.insert(tk.END,f"Error: {ex}")
        def on_double(e):
            sel=lb.get(lb.curselection()); name=sel[4:] if sel.startswith("[") else ".."
            new=Path(path_var.get()).parent if name==".." else Path(path_var.get())/name
            if new.is_dir(): path_var.set(str(new)); refresh()
        path_entry.bind("<Return>",refresh); lb.bind("<Double-Button-1>",on_double)
        tk.Button(ctrl,text="Go",bg=ACCENT2,fg=TEXT,font=FONT_SM,relief=tk.FLAT,command=refresh).pack(side=tk.RIGHT)
        refresh()

    def open_editor(self):
        win=LuoWindow(self,"Text Editor",600,450)
        tb=tk.Frame(win.content,bg=BG2); tb.pack(fill=tk.X)
        fn=tk.StringVar(value="untitled.txt")
        tk.Entry(tb,textvariable=fn,bg=BG,fg=TEXT,font=FONT_SM,relief=tk.FLAT,width=24).pack(side=tk.LEFT,padx=4,pady=4)
        text=scrolledtext.ScrolledText(win.content,bg=BG,fg=TEXT,font=FONT,relief=tk.FLAT,insertbackground=ACCENT)
        text.pack(fill=tk.BOTH,expand=True,padx=4,pady=4)
        def save():
            try: Path(fn.get()).write_text(text.get("1.0",tk.END)); messagebox.showinfo("Saved",f"Saved: {fn.get()}")
            except Exception as e: messagebox.showerror("Error",str(e))
        def opn():
            try: text.delete("1.0",tk.END); text.insert("1.0",Path(fn.get()).read_text())
            except Exception as e: messagebox.showerror("Error",str(e))
        tk.Button(tb,text="Open",bg=BG,fg=ACCENT,font=FONT_SM,relief=tk.FLAT,command=opn).pack(side=tk.LEFT,padx=2)
        tk.Button(tb,text="Save",bg=ACCENT2,fg=TEXT,font=FONT_SM,relief=tk.FLAT,command=save).pack(side=tk.LEFT,padx=2)

    def open_browser(self):
        win=LuoWindow(self,"Browser",600,100)
        uv=tk.StringVar(value="https://google.com")
        bar=tk.Frame(win.content,bg=BG2); bar.pack(fill=tk.X,padx=4,pady=8)
        ue=tk.Entry(bar,textvariable=uv,bg=BG,fg=TEXT,font=FONT,relief=tk.FLAT)
        ue.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=4)
        def go(e=None): subprocess.Popen(["xdg-open",uv.get()])
        ue.bind("<Return>",go)
        tk.Button(bar,text="Go",bg=ACCENT2,fg=TEXT,font=FONT_SM,relief=tk.FLAT,command=go).pack(side=tk.RIGHT)
        tk.Label(win.content,text="Opens in system browser",bg=BG2,fg=DIM,font=FONT_SM).pack(pady=4)

    def open_pkg(self):
        win=LuoWindow(self,"Package Manager",560,460)
        sv=tk.StringVar()
        ctrl=tk.Frame(win.content,bg=BG2); ctrl.pack(fill=tk.X,padx=8,pady=4)
        tk.Entry(ctrl,textvariable=sv,bg=BG,fg=TEXT,font=FONT_SM,relief=tk.FLAT,width=20).pack(side=tk.LEFT,padx=4)
        out=scrolledtext.ScrolledText(win.content,bg=BG,fg=TEXT,font=FONT_SM,relief=tk.FLAT)
        out.pack(fill=tk.BOTH,expand=True,padx=8,pady=4)
        def run_pkg(args):
            out.delete("1.0",tk.END)
            def _r():
                r=subprocess.run(f"python3 shell/luo_pkg.py {args}",shell=True,capture_output=True,text=True)
                out.after(0,lambda:out.insert(tk.END,r.stdout+r.stderr))
            threading.Thread(target=_r,daemon=True).start()
        for label,args in [("Available","available"),("Installed","list"),("Search",f"search {sv.get()}")]:
            tk.Button(ctrl,text=label,bg=BG,fg=ACCENT,font=FONT_SM,relief=tk.FLAT,command=lambda a=args:run_pkg(a)).pack(side=tk.LEFT,padx=2)
        tk.Button(ctrl,text="Install",bg=ACCENT2,fg=TEXT,font=FONT_SM,relief=tk.FLAT,command=lambda:run_pkg(f"install {sv.get()}")).pack(side=tk.LEFT,padx=2)
        run_pkg("available")

    def open_settings(self):
        win=LuoWindow(self,"Settings",400,300)
        for k,v in [("Version","Luo OS v0.1"),("Author","Abd El-Rahman Abbas (Mr. Kai)"),
                    ("GitHub","github.com/luokai25"),("AI Backend","LUOKAI (native)"),
                    ("Agent API","localhost:7070"),("REST API","localhost:8080"),("License","Open Source")]:
            row=tk.Frame(win.content,bg=BG2); row.pack(fill=tk.X,padx=8,pady=3)
            tk.Label(row,text=f"{k}:",bg=BG2,fg=DIM,font=FONT_SM,width=14,anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row,text=v,bg=BG2,fg=TEXT,font=FONT_SM,anchor=tk.W).pack(side=tk.LEFT)

    def run(self): self.root.mainloop()

if __name__=="__main__":
    LuoDesktop().run()
