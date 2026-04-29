import os
#!/usr/bin/env python3
"""
luokai/cells/coding.py — Coding Cells
======================================
Port of coding-cells.js — specialized code intelligence cells.
Feeds from 18M data entries: algorithms, code-conversations,
debugging-scenarios, code-reviews, security-vulns, architecture-patterns.

Cells: DebugCell, SyntaxCell, LogicCell, RefactorCell,
       OptimizationCell, CodeGeneratorCell, AlgorithmCell, SecurityCell
"""
import re
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from .base import BaseCell


# ══════════════════════════════════════════════════════════════════
# DEBUG CELL
# ══════════════════════════════════════════════════════════════════

class DebugCell(BaseCell):
    """Diagnose and explain errors from learned debugging scenarios."""
    category = "coding"

    # Common error → solution map (from debugging-scenarios data)
    KNOWN_ERRORS = {
        "keyerror": "You're accessing a dictionary key that doesn't exist. Use .get(key, default) or check 'if key in dict' first.",
        "indexerror": "List index is out of range. Check len(list) before accessing, or use try/except.",
        "typeerror": "Wrong type passed to function. Check variable types with type() and convert if needed.",
        "valueerror": "Invalid value for the operation. Check input validation and constraints.",
        "attributeerror": "Object doesn't have that attribute/method. Check spelling and that you have the right object type.",
        "nameerror": "Variable not defined. Check scope — is it defined before use?",
        "importerror": "Module not found. Run: pip install <module> or check the module name.",
        "syntaxerror": "Python syntax is invalid. Check for missing colons, brackets, or indentation.",
        "zerodivisionerror": "Division by zero. Add: if denominator != 0: before dividing.",
        "recursionerror": "Infinite recursion. Check your base case — it must be reachable.",
        "memoryerror": "Out of memory. Process data in chunks or use generators instead of lists.",
        "filenotfounderror": "File doesn't exist. Check the path with Path(path).exists() first.",
        "permissionerror": "No permission to access file/directory. Check file permissions.",
        "connectionerror": "Network connection failed. Check connectivity and retry with exponential backoff.",
        "timeouterror": "Operation timed out. Increase timeout or optimize the operation.",
        "nullpointerexception": "NoneType object accessed. Add None check: if obj is not None: before accessing.",
        "sql injection": "Sanitize user input. Use parameterized queries: cursor.execute('SELECT * FROM t WHERE id=?', (id,))",
        "cors": "Add CORS headers to your server response. Use flask-cors or equivalent middleware.",
        "404": "Route/resource not found. Check the URL, method (GET/POST), and server routing.",
        "500": "Server error. Check server logs for the root cause. Add error handling around the failing code.",
        "401": "Unauthorized. Include valid authentication token in the Authorization header.",
        "403": "Forbidden. User is authenticated but lacks permission. Check role/scope requirements.",
    }

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if isinstance(signal, str):
            return self.diagnose(signal)
        return signal

    def diagnose(self, error_text: str) -> Dict:
        """Diagnose an error and suggest a fix."""
        err_lower = error_text.lower()

        # Check known errors
        for error_type, solution in self.KNOWN_ERRORS.items():
            if error_type in err_lower:
                self.state += 1
                return {
                    "error_type": error_type,
                    "solution": solution,
                    "source": "built-in",
                    "confidence": 0.9,
                }

        # Search learned debugging scenarios
        results = self.search(error_text, limit=2)
        if results:
            r = results[0]
            self.state += 1
            return {
                "error_type": r.get("error_type", "unknown"),
                "solution": r.get("solution", "Check the error context carefully."),
                "difficulty": r.get("difficulty", "medium"),
                "source": "learned",
                "confidence": 0.7,
            }

        return {
            "error_type": "unknown",
            "solution": "Check the full error traceback. Look at the line number and the exact error message.",
            "source": "fallback",
            "confidence": 0.3,
        }

    def format_response(self, query: str) -> str:
        """Format a user-friendly debug response."""
        result = self.diagnose(query)
        lines = [f"**Debugging: {result['error_type'].title()}**\n"]
        lines.append(f"**Fix:** {result['solution']}")
        if result.get("difficulty"):
            lines.append(f"*Difficulty: {result['difficulty']}*")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# SYNTAX CELL
# ══════════════════════════════════════════════════════════════════

class SyntaxCell(BaseCell):
    """Understand and validate code syntax patterns."""
    category = "coding"

    SYNTAX_PATTERNS = {
        "python": {
            "function":     r"def\s+\w+\s*\([^)]*\)\s*(?:->\s*\w+)?\s*:",
            "class":        r"class\s+\w+(?:\([^)]*\))?\s*:",
            "import":       r"(?:from\s+\S+\s+)?import\s+\S+",
            "list_comp":    r"\[.+\s+for\s+\w+\s+in\s+.+\]",
            "decorator":    r"@\w+(?:\([^)]*\))?",
            "type_hint":    r"\w+\s*:\s*(?:Optional\[|List\[|Dict\[|Union\[)?\w+",
            "f_string":     r'f["\'][^"\']*\{[^}]+\}[^"\']*["\']',
            "async":        r"async\s+def\s+\w+",
            "lambda":       r"lambda\s+[^:]+:\s*.+",
        },
        "javascript": {
            "arrow":        r"(?:const|let|var)\s+\w+\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>",
            "async_await":  r"async\s+function\s+\w+|async\s+\([^)]*\)\s*=>",
            "destructure":  r"const\s*\{[^}]+\}\s*=|const\s*\[[^\]]+\]\s*=",
            "class":        r"class\s+\w+(?:\s+extends\s+\w+)?\s*\{",
            "template":     r"`[^`]*\$\{[^}]+\}[^`]*`",
            "spread":       r"\.\.\.\w+",
            "optional_chain": r"\?(?:\.|[\[)])",
        },
        "sql": {
            "select":       r"SELECT\s+.+\s+FROM\s+\w+",
            "join":         r"(?:INNER|LEFT|RIGHT|FULL)?\s*JOIN\s+\w+\s+ON",
            "window":       r"OVER\s*\([^)]*\)",
            "cte":          r"WITH\s+\w+\s+AS\s*\(",
            "index":        r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+\w+\s+ON\s+\w+",
        },
    }

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def detect_language(self, code: str) -> str:
        """Detect programming language from code."""
        checks = {
            "python":     [r"\bdef \w+\(", r"\bimport \w+", r"\bclass \w+:", r"print\("],
            "javascript": [r"\bconst \w+\s*=", r"=>\s*\{", r"console\.log", r"\bfunction\b"],
            "typescript": [r":\s*(?:string|number|boolean|any)\b", r"interface \w+", r"<\w+>"],
            "rust":       [r"\bfn \w+\(", r"\blet mut\b", r"\bimpl \w+", r"->.*\{"],
            "go":         [r"\bfunc \w+\(", r"\bpackage \w+", r":=", r"fmt\.Print"],
            "sql":        [r"\bSELECT\b", r"\bFROM\b", r"\bWHERE\b", r"\bJOIN\b"],
            "bash":       [r"^#!/bin/bash", r"\$\{?\w+\}?", r"\becho\b", r"\bif \["],
        }
        scores = {}
        for lang, patterns in checks.items():
            score = sum(1 for p in patterns if re.search(p, code, re.MULTILINE))
            if score > 0:
                scores[lang] = score
        if not scores:
            return "unknown"
        return max(scores, key=scores.get)

    def extract_patterns(self, code: str, language: str = None) -> Dict[str, List[str]]:
        """Extract code patterns by type."""
        if not language:
            language = self.detect_language(code)
        patterns = self.SYNTAX_PATTERNS.get(language, {})
        found = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, code, re.MULTILINE)
            if matches:
                found[name] = matches[:3]  # max 3 examples
        return found


# ══════════════════════════════════════════════════════════════════
# LOGIC CELL
# ══════════════════════════════════════════════════════════════════

class LogicCell(BaseCell):
    """Evaluate logical expressions and code correctness."""
    category = "coding"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def evaluate_condition(self, condition: str, variables: Dict) -> Optional[bool]:
        """Safely evaluate a simple boolean condition."""
        # Only allow safe subset
        safe_condition = condition
        for var, val in variables.items():
            if isinstance(val, (int, float, bool, str)):
                safe_condition = safe_condition.replace(var, repr(val))
        try:
            # Restrict to comparisons only
            if re.match(r'^[\w\s\d\+\-\*\/\<\>\=\!\(\)\'\"\.and or not]+$', safe_condition):
                result = eval(safe_condition, {"__builtins__": {}}, {})  # noqa
                self.state += 1
                return bool(result)
        except Exception:
            pass
        return None

    def detect_logic_issues(self, code: str) -> List[str]:
        """Detect common logic issues in code."""
        issues = []
        # Off-by-one
        if re.search(r"range\(\s*\d+\s*\)", code) and "len(" in code:
            issues.append("Possible off-by-one: verify range() bounds match list length")
        # Mutable default argument
        if re.search(r"def\s+\w+\([^)]*=\s*[\[\{]", code):
            issues.append("Mutable default argument: use None and initialize inside function")
        # == None instead of is None
        if "== None" in code or "!= None" in code:
            issues.append("Use 'is None' or 'is not None' instead of == or !=")
        # Bare except
        if re.search(r"except\s*:", code):
            issues.append("Bare 'except:' catches everything including KeyboardInterrupt — be specific")
        # Global variable in function
        if re.search(r"\bglobal\s+\w+", code):
            issues.append("Using global variables — consider passing as parameter instead")
        return issues


# ══════════════════════════════════════════════════════════════════
# ALGORITHM CELL
# ══════════════════════════════════════════════════════════════════

class AlgorithmCell(BaseCell):
    """Knowledge about algorithms — complexity, implementation, use cases."""
    category = "coding"

    # Built-in algorithm knowledge
    ALGORITHMS = {
        "binary search": {
            "time": "O(log n)", "space": "O(1)",
            "use": "Search in sorted array",
            "impl": "def binary_search(arr,target):\n    l,r=0,len(arr)-1\n    while l<=r:\n        m=(l+r)//2\n        if arr[m]==target: return m\n        elif arr[m]<target: l=m+1\n        else: r=m-1\n    return -1",
        },
        "quicksort": {
            "time": "O(n log n) avg, O(n²) worst", "space": "O(log n)",
            "use": "General-purpose in-place sorting",
            "impl": "def quicksort(arr):\n    if len(arr)<=1: return arr\n    p=arr[len(arr)//2]\n    return quicksort([x for x in arr if x<p])+[x for x in arr if x==p]+quicksort([x for x in arr if x>p])",
        },
        "merge sort": {
            "time": "O(n log n)", "space": "O(n)",
            "use": "Stable sort, linked lists, external sort",
            "impl": "Divide array in half, sort each half recursively, merge sorted halves",
        },
        "bfs": {
            "time": "O(V+E)", "space": "O(V)",
            "use": "Shortest path (unweighted), level-order traversal, closest node",
            "impl": "from collections import deque\ndef bfs(graph,start):\n    visited=set(); queue=deque([start])\n    while queue:\n        node=queue.popleft()\n        if node not in visited:\n            visited.add(node); queue.extend(graph[node])\n    return visited",
        },
        "dfs": {
            "time": "O(V+E)", "space": "O(V)",
            "use": "Cycle detection, topological sort, connected components, maze solving",
            "impl": "def dfs(graph,start,visited=None):\n    if visited is None: visited=set()\n    visited.add(start)\n    for n in graph[start]:\n        if n not in visited: dfs(graph,n,visited)\n    return visited",
        },
        "dijkstra": {
            "time": "O((V+E) log V)", "space": "O(V)",
            "use": "Shortest path with non-negative weights",
            "impl": "import heapq\ndef dijkstra(graph,start):\n    dist={n:float('inf') for n in graph}; dist[start]=0\n    pq=[(0,start)]\n    while pq:\n        d,node=heapq.heappop(pq)\n        if d>dist[node]: continue\n        for nb,w in graph[node]:\n            if dist[node]+w<dist[nb]:\n                dist[nb]=dist[node]+w; heapq.heappush(pq,(dist[nb],nb))\n    return dist",
        },
        "dynamic programming": {
            "time": "Problem-dependent", "space": "Problem-dependent",
            "use": "Overlapping subproblems + optimal substructure",
            "impl": "Identify recurrence relation → memoize with @lru_cache or build bottom-up table",
        },
        "two pointers": {
            "time": "O(n)", "space": "O(1)",
            "use": "Array problems: two sum sorted, remove duplicates, container with water",
            "impl": "l,r=0,len(arr)-1\nwhile l<r:\n    if condition: l+=1\n    else: r-=1",
        },
        "sliding window": {
            "time": "O(n)", "space": "O(1) or O(k)",
            "use": "Subarray/substring problems with constraint",
            "impl": "Expand right pointer, contract left when constraint violated",
        },
    }

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if isinstance(signal, str):
            return self.lookup(signal)
        return signal

    def lookup(self, query: str) -> Optional[Dict]:
        """Look up algorithm information."""
        q = query.lower()
        # Direct match
        for algo, info in self.ALGORITHMS.items():
            if algo in q:
                self.state += 1
                return {"algorithm": algo, **info}
        # Learned data search
        results = self.search(query, limit=1)
        if results:
            r = results[0]
            self.state += 1
            return {
                "algorithm": r.get("algorithm", query),
                "time": r.get("time_complexity", "?"),
                "space": r.get("space_complexity", "?"),
                "description": r.get("description", ""),
                "language": r.get("language", ""),
                "implementation": r.get("implementation", ""),
                "source": "learned",
            }
        return None

    def format_response(self, query: str) -> Optional[str]:
        result = self.lookup(query)
        if not result:
            return None
        lines = [f"**Algorithm: {result['algorithm'].title()}**\n"]
        if result.get("time"):
            lines.append(f"⏱ Time: `{result['time']}`")
        if result.get("space"):
            lines.append(f"💾 Space: `{result['space']}`")
        if result.get("use"):
            lines.append(f"🎯 Use when: {result['use']}")
        if result.get("impl"):
            lines.append(f"\n```python\n{result['impl']}\n```")
        if result.get("description"):
            lines.append(f"\n{result['description'][:200]}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# SECURITY CELL
# ══════════════════════════════════════════════════════════════════

class SecurityCell(BaseCell):
    """Security vulnerability detection and mitigation."""
    category = "coding"

    VULNERABILITIES = {
        "sql injection": {
            "severity": "critical",
            "description": "User input embedded directly in SQL query",
            "fix": "Use parameterized queries: cursor.execute('SELECT * FROM t WHERE id=?', (id,))",
            "example_vuln": "query = 'SELECT * FROM users WHERE id=' + user_id",
            "example_safe": "cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))",
        },
        "xss": {
            "severity": "high",
            "description": "Unsanitized user input rendered as HTML",
            "fix": "Escape HTML: use template engines, never innerHTML with user data",
            "example_safe": "element.textContent = userInput; // not innerHTML",
        },
        "csrf": {
            "severity": "high",
            "description": "State-changing requests without CSRF token",
            "fix": "Add CSRF token to all state-changing forms/requests",
            "example_safe": "<input type='hidden' name='csrf_token' value='{{csrf_token}}'>",
        },
        "hardcoded secret": {
            "severity": "critical",
            "description": "Credentials/secrets in source code",
            "fix": "Use environment variables: os.environ.get('SECRET_KEY')",
        },
        "path traversal": {
            "severity": "high",
            "description": "User input used in file paths without sanitization",
            "fix": "Use Path(base_dir / safe_filename).resolve() and verify it's inside base_dir",
        },
        "insecure deserialization": {
            "severity": "critical",
            "description": "Deserializing untrusted data (pickle, yaml.load)",
            "fix": "Use json.loads() for untrusted data, never pickle.loads() on user input",
        },
        "open redirect": {
            "severity": "medium",
            "description": "Redirect URL taken from user input without validation",
            "fix": "Whitelist allowed redirect URLs or use relative paths only",
        },
        "mass assignment": {
            "severity": "high",
            "description": "User input directly sets model fields without allowlist",
            "fix": "Explicitly specify allowed fields: model.update(**{k:v for k,v in data.items() if k in ALLOWED})",
        },
    }

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if isinstance(signal, str):
            return self.scan(signal)
        return signal

    def scan(self, code_or_query: str) -> List[Dict]:
        """Scan code or answer query about vulnerabilities."""
        text = code_or_query.lower()
        found = []
        for vuln, info in self.VULNERABILITIES.items():
            if vuln in text:
                found.append({"vulnerability": vuln, **info})
        # Search learned vulnerability data
        if not found:
            results = self.search(code_or_query, limit=2)
            for r in results:
                found.append({
                    "vulnerability": r.get("name", r.get("cwe_id", "unknown")),
                    "severity": r.get("severity", "unknown"),
                    "fix": r.get("fix", "Review code carefully"),
                    "language": r.get("language", ""),
                })
        self.state += 1
        return found

    def audit_code(self, code: str) -> List[str]:
        """Quick security audit of code snippet."""
        issues = []
        # SQL injection patterns
        if re.search(r"[\"'].*SELECT.*[\"']\s*\+", code, re.IGNORECASE):
            issues.append("⚠️ SQL Injection: string concatenation in SQL query")
        # Hardcoded secrets
        if re.search(r"(?:password|secret|key|token)\s*=\s*[\"'][^\"']{4,}[\"']", code, re.IGNORECASE):
            issues.append("⚠️ Hardcoded secret: move to environment variable")
        # eval() usage
        if re.search(r"\beval\s*\(", code):
            issues.append("⚠️ eval() usage: potential code injection risk")
        # pickle on untrusted data
        if "pickle.loads" in code:
            issues.append("⚠️ pickle.loads() on potentially untrusted data")
        # shell=True
        if re.search(r"subprocess\.\w+\([^)]*shell\s*=\s*True", code):
            issues.append("⚠️ shell=True in subprocess: avoid with user input")
        # innerHTML
        if "innerHTML" in code and ("input" in code.lower() or "param" in code.lower()):
            issues.append("⚠️ innerHTML with user input: XSS risk, use textContent")
        return issues


# ══════════════════════════════════════════════════════════════════
# REFACTOR CELL
# ══════════════════════════════════════════════════════════════════

class RefactorCell(BaseCell):
    """Suggest code improvements and refactoring patterns."""
    category = "coding"

    CODE_SMELLS = {
        "long_function": {"pattern": r"def \w+[^:]+:\n(?:[ \t]+.+\n){20,}", "suggestion": "Function is too long (>20 lines). Extract smaller functions."},
        "magic_number":  {"pattern": r"(?<![.'\"\w])\d{2,}(?![.'\"\w])", "suggestion": "Magic number detected. Define as named constant."},
        "god_object":    {"pattern": r"class \w+[^:]*:\n(?:[ \t]+(?:def|self\.\w+\s*=)[^\n]+\n){15,}", "suggestion": "Class has too many responsibilities. Apply Single Responsibility Principle."},
        "duplicated":    {"pattern": None, "suggestion": "Duplicated code block. Extract to a shared function."},
    }

    REFACTORING_TIPS = [
        "Replace conditional with polymorphism",
        "Extract method: if you need a comment to explain a block, make it a function",
        "Replace nested conditionals with guard clauses (early return)",
        "Use list comprehensions instead of manual append loops",
        "Replace switch/if-elif chains with dictionary dispatch",
        "Use context managers for resource management",
        "Prefer composition over inheritance",
        "Make functions pure where possible (no side effects)",
    ]

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def suggest(self, code: str) -> List[str]:
        """Suggest refactoring improvements."""
        suggestions = []
        # Check for code smells
        for smell, info in self.CODE_SMELLS.items():
            if info["pattern"] and re.search(info["pattern"], code, re.MULTILINE):
                suggestions.append(info["suggestion"])
        # Add general tips based on code content
        if len(code.split("\n")) > 50:
            suggestions.append("File is long. Consider splitting into modules.")
        if code.count("if") > 8:
            suggestions.append("Many conditionals. Consider strategy pattern or dispatch dict.")
        if "copy.copy" not in code and "[" in code and "append" in code and "for" in code:
            suggestions.append("Manual list building: consider list comprehension or map()")
        # Add learned suggestions
        results = self.search(code[:100], limit=1)
        if results:
            r = results[0]
            if r.get("suggestion"):
                suggestions.append(r["suggestion"])
        self.state += 1
        return suggestions[:5]


# ══════════════════════════════════════════════════════════════════
# CODING ENGINE — orchestrates all coding cells
# ══════════════════════════════════════════════════════════════════

class CodingEngine:
    """Orchestrates all coding cells for code intelligence."""

    def __init__(self):
        self.debug     = DebugCell("debug")
        self.syntax    = SyntaxCell("syntax")
        self.logic     = LogicCell("logic")
        self.algorithm = AlgorithmCell("algorithm")
        self.security  = SecurityCell("security")
        self.refactor  = RefactorCell("refactor")

        self.cells = [self.debug, self.syntax, self.logic,
                      self.algorithm, self.security, self.refactor]
        print(f"[CodingEngine] {len(self.cells)} coding cells active")

    def analyze(self, query: str, code: str = None) -> Dict:
        """Comprehensive code analysis."""
        result = {"query": query}

        # Detect language
        if code:
            result["language"] = self.syntax.detect_language(code)
            result["patterns"] = self.syntax.extract_patterns(code, result["language"])
            result["logic_issues"] = self.logic.detect_logic_issues(code)
            result["security_issues"] = self.security.audit_code(code)
            result["refactor_tips"] = self.refactor.suggest(code)

        # Algorithm lookup
        algo = self.algorithm.format_response(query)
        if algo:
            result["algorithm_info"] = algo

        # Debug info
        if any(w in query.lower() for w in ["error","exception","bug","fail","crash"]):
            result["debug_info"] = self.debug.format_response(query)

        return result

    def respond(self, query: str) -> Optional[str]:
        """Generate a coding response from cell knowledge."""
        q = query.lower()

        # Algorithm questions
        if any(w in q for w in ["algorithm","complexity","sort","search","graph","bfs","dfs","dijkstra","dynamic"]):
            return self.algorithm.format_response(query)

        # Debug/error questions
        if any(w in q for w in ["error","exception","bug","traceback","fix","debug","crash"]):
            return self.debug.format_response(query)

        # Security questions
        if any(w in q for w in ["secure","vulnerability","inject","xss","csrf","auth","hash","encrypt"]):
            vulns = self.security.scan(query)
            if vulns:
                v = vulns[0]
                lines = [f"**Security: {v['vulnerability'].title()}**",
                         f"Severity: {v.get('severity','unknown')}",
                         f"Fix: {v.get('fix','')}"]
                if v.get("example_safe"):
                    lines.append(f"```\n{v['example_safe']}\n```")
                return "\n".join(lines)

        return None

    def load_data(self, entries: List[Dict], category: str) -> None:
        """Load data entries into appropriate cells."""
        for entry in entries:
            if category in ("debugging", "debugging-scenarios"):
                self.debug.learn(entry)
            elif category in ("algorithms",):
                self.algorithm.learn(entry)
            elif category in ("security-vulns", "security-audits"):
                self.security.learn(entry)
            elif category in ("code-reviews", "coding-patterns"):
                self.refactor.learn(entry)
            elif category in ("code-conversations",):
                # Load into all cells
                for cell in self.cells:
                    cell.learn(entry)

    def status(self) -> Dict:
        return {
            "cells": len(self.cells),
            "learned": {c.name: len(c.specialized_data) for c in self.cells},
            "total_activations": sum(c._activations for c in self.cells),
        }
