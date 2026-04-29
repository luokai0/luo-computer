#!/usr/bin/env python3
"""
Luo OS — Search Engine Wrapper
Tries SearXNG (local) first, falls back to DuckDuckGo.
To run SearXNG locally:
  docker run -d -p 8888:8080 searxng/searxng
"""
import urllib.request, urllib.parse, json, re
from typing import List, Dict

SEARXNG_URL = "http://localhost:8888"
DDG_URL     = "https://html.duckduckgo.com/html/"

def _searxng(query: str, n: int = 5) -> List[Dict]:
    try:
        params  = urllib.parse.urlencode({"q":query,"format":"json","engines":"google,bing,duckduckgo"})
        url     = f"{SEARXNG_URL}/search?{params}"
        req     = urllib.request.Request(url, headers={"User-Agent":"LuoOS/0.1"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data    = json.loads(r.read())
        results = data.get("results", [])[:n]
        return [{"title":r.get("title",""), "snippet":r.get("content",""), "url":r.get("url","")} for r in results]
    except Exception:
        return []

def _duckduckgo(query: str, n: int = 5) -> List[Dict]:
    try:
        url  = f"{DDG_URL}?q={urllib.parse.quote(query)}"
        req  = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        clean   = lambda s: re.sub(r"<[^>]+>","",s).strip()
        titles  = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
        snippets= re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        return [{"title":clean(t),"snippet":clean(s),"url":""}
                for t,s in zip(titles[:n],snippets[:n])]
    except Exception as e:
        return [{"title":"Search error","snippet":str(e),"url":""}]

def search(query: str, n: int = 5) -> List[Dict]:
    """Search — tries SearXNG first, falls back to DuckDuckGo."""
    results = _searxng(query, n)
    if results:
        return results
    return _duckduckgo(query, n)

def search_text(query: str, n: int = 5) -> str:
    """Search and return formatted text for agent injection."""
    results = search(query, n)
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        if r["snippet"]:
            lines.append(f"   {r['snippet'][:200]}")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Luo OS open source"
    print(f"Searching: {q}\n")
    print(search_text(q))
