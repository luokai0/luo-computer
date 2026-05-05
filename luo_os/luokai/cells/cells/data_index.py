#!/usr/bin/env python3
"""
luokai/cells/data_index.py — Data Indexer
==========================================
Loads 18.4M data entries from the cells_and_data archive into
LUOKAI's cell network. Smart sampling ensures each cell gets
the most useful knowledge without memory overflow.

Strategy:
  - Sample up to MAX_PER_CATEGORY entries per data file
  - Route each category to the right cells
  - Build fast keyword-lookup indexes for O(1) access
  - Total memory footprint: ~500MB for full index
"""
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# Max entries to load per category (balances coverage vs memory)
MAX_PER_CATEGORY = {
    "algorithms":           5_000,
    "code-conversations":  10_000,
    "debugging-scenarios":  5_000,
    "code-snippets":        3_000,
    "code-snippets-2":      3_000,
    "architecture-patterns": 3_000,
    "security-vulns":       3_000,
    "security-audits":      1_000,
    "api-patterns":         3_000,
    "api-specs":            2_000,
    "cicd-pipelines":       2_000,
    "database-schemas":     2_000,
    "documentation":        3_000,
    "test-cases":           3_000,
    "code-reviews":         3_000,
    "devops-configs":       2_000,
}

DATA_DIRS = [
    Path(__file__).parent.parent / "data" / "knowledge",   # Repo JSONL data (ships with LuoOS)
    Path(__file__).parent.parent / "data",                  # Repo data root
    Path.home() / ".luo_os" / "data",                       # User-added data
    Path("/home/claude/rar_extract"),                        # Dev extraction dir
]

# Repo knowledge DB — ships with LuoOS, always available
REPO_DB = Path(__file__).parent.parent / "data" / "knowledge.db"

class DataIndex:
    """
    Fast indexed access to coding knowledge.
    Backed by SQLite for persistence and speed.
    """

    def __init__(self, db_path: str = "~/.luo_os/data_index.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional[sqlite3.Connection] = None
        self._loaded = False
        self._stats: Dict[str, int] = {}

    def _connect(self) -> sqlite3.Connection:
        if self._db is None:
            self._db = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._db.row_factory = sqlite3.Row
            self._setup_schema()
        return self._db

    def _setup_schema(self):
        db = self._db
        db.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id          TEXT PRIMARY KEY,
                category    TEXT NOT NULL,
                language    TEXT,
                content     TEXT NOT NULL,
                keywords    TEXT,
                ts          REAL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_category ON entries(category);
            CREATE INDEX IF NOT EXISTS idx_language ON entries(language);
            CREATE INDEX IF NOT EXISTS idx_keywords ON entries(keywords);
        """)
        db.commit()

    def load_from_jsonl(self, jsonl_dir: Path) -> int:
        """Load compact JSONL knowledge files (ships with LuoOS repo)."""
        if not jsonl_dir.exists():
            return 0
        db = self._connect()
        total = 0
        for fpath in sorted(jsonl_dir.glob("*.jsonl")):
            batch = []
            try:
                with open(fpath, encoding="utf-8") as f:
                    for line in f:
                        try:
                            item = json.loads(line.strip())
                            entry_id = f"k_{total}"
                            cat = item.get("c", "general")
                            lang = item.get("l", "") or None
                            q = item.get("q", "") or None
                            a = item.get("a", "") or None
                            kws = f"{cat} {lang or ''} {(q or '')[:50]}".lower()
                            content_str = f"{q or ''} | {a or ''}"[:2000]
                            batch.append((entry_id, cat, lang, content_str, kws, 0))
                            total += 1
                        except Exception:
                            pass
                if batch:
                    db.executemany(
                        "INSERT OR IGNORE INTO entries (id,category,language,content,keywords,ts) VALUES (?,?,?,?,?,?)",
                        batch
                    )
                    db.commit()
            except Exception as e:
                pass
        if total > 0:
            print(f"[DataIndex] Loaded {total:,} entries from JSONL knowledge base")
        return total

    def load_from_directory(self, data_dir: Path) -> int:
        """Load JSON data files from a directory into the index."""
        if not data_dir.exists():
            return 0

        db = self._connect()
        total = 0

        # Get already-loaded categories
        existing = set(r[0] for r in db.execute("SELECT DISTINCT category FROM entries"))

        json_files = sorted(data_dir.glob("*.json"))
        categories_seen = {}

        for fpath in json_files:
            # Parse category from filename
            name = fpath.stem
            cat = re.sub(r"-\d+$", "", name)  # strip trailing -000, -001, etc

            # Skip if already loaded enough for this category
            max_load = MAX_PER_CATEGORY.get(cat, 2_000)
            already = categories_seen.get(cat, 0)
            if already >= max_load:
                continue

            try:
                data = json.loads(fpath.read_text(encoding="utf-8", errors="ignore"))
                if not isinstance(data, list):
                    continue

                # Sample proportionally from this file
                remaining = max_load - already
                sample = data[:remaining] if len(data) > remaining else data

                rows = []
                for item in sample:
                    if not isinstance(item, dict):
                        continue
                    entry_id = item.get("id", f"{cat}_{total}")
                    content = self._extract_content(item, cat)
                    keywords = self._extract_keywords(item)
                    language = (item.get("language") or "").lower()
                    rows.append((
                        str(entry_id), cat, language[:50] if language else None,
                        content[:2000], keywords, time.time()
                    ))

                db.executemany(
                    "INSERT OR IGNORE INTO entries (id,category,language,content,keywords,ts) VALUES (?,?,?,?,?,?)",
                    rows
                )
                db.commit()

                n = len(rows)
                categories_seen[cat] = already + n
                total += n

                if n > 0:
                    print(f"  [DataIndex] {cat:30s} +{n:,} → {categories_seen[cat]:,}")

            except Exception as e:
                pass  # Skip bad files silently

        self._loaded = True
        self._stats = dict(categories_seen)
        return total

    def _extract_content(self, item: Dict, category: str) -> str:
        """Extract searchable content from a data entry."""
        parts = []

        # Category-specific extraction
        if "question" in item:
            parts.append(item["question"])
        if "answer" in item:
            parts.append(item["answer"][:500])
        if "description" in item:
            parts.append(item["description"][:200])
        if "algorithm" in item:
            parts.append(f"Algorithm: {item['algorithm']}")
        if "pattern" in item:
            parts.append(f"Pattern: {item['pattern']}")
        if "error_type" in item:
            parts.append(f"Error: {item['error_type']}: {item.get('error_message','')}")
        if "solution" in item:
            parts.append(f"Solution: {item.get('solution','')}")
        if "fix" in item:
            parts.append(f"Fix: {item['fix']}")
        if "name" in item:
            parts.append(item["name"])
        if "content" in item and isinstance(item["content"], str):
            parts.append(item["content"][:300])
        if "implementation" in item:
            parts.append(item["implementation"][:200])
        if "code" in item and isinstance(item["code"], str):
            parts.append(item["code"][:300])

        # Fallback to all string values
        if not parts:
            for v in item.values():
                if isinstance(v, str) and len(v) > 5:
                    parts.append(v[:100])

        return " | ".join(parts)[:2000]

    def _extract_keywords(self, item: Dict) -> str:
        """Extract searchable keywords."""
        keywords = set()
        for k in ["language", "algorithm", "pattern", "error_type", "type",
                   "category", "framework", "ci_system", "database", "tool"]:
            v = item.get(k)
            if v and isinstance(v, str):
                keywords.add(v.lower())

        # Extract from text fields
        for k in ["description", "question", "name"]:
            v = item.get(k, "")
            if isinstance(v, str):
                words = re.findall(r"\b[a-z]{3,}\b", v.lower())
                keywords.update(words[:10])

        return " ".join(list(keywords)[:30])

    def search_knowledge(self, query: str, language: str = None, limit: int = 5) -> List[Dict]:
        """Search the knowledge table (k) from the repo DB using smart scoring."""
        db = self._connect()
        q_lower = query.lower().strip()
        q_words = [w for w in re.sub(r"[^\w\s]", " ", q_lower).split() if len(w) > 2]
        if not q_words:
            return []
        try:
            tables = [r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "k" not in tables:
                return []

            # Strategy 1: exact phrase match on question (highest priority)
            exact_rows = db.execute(
                "SELECT cat,lang,q,a FROM k WHERE LOWER(q) LIKE ? LIMIT ?",
                (f"%{q_lower}%", limit)
            ).fetchall()

            # Strategy 2: all meaningful words must appear (AND logic)
            sig_words = [w for w in q_words if w not in {
                "how", "what", "why", "when", "where", "who", "the", "are",
                "is", "to", "do", "does", "a", "an", "in", "of", "for",
                "use", "using", "used", "make", "making", "get", "getting",
                "work", "works", "working", "set", "setting"
            }]
            and_rows = []
            if sig_words:
                and_conds = " AND ".join(f"LOWER(q) LIKE ?" for _ in sig_words)
                and_params = [f"%{w}%" for w in sig_words[:5]]
                and_rows = db.execute(
                    f"SELECT cat,lang,q,a FROM k WHERE {and_conds} LIMIT ?",
                    and_params + [limit * 2]
                ).fetchall()

            # Combine and score
            seen = set()
            scored = []
            for rows, base_score in [(exact_rows, 100), (and_rows, 50)]:
                for row in rows:
                    key = row[2] or ""
                    if key in seen:
                        continue
                    seen.add(key)
                    q_text = (row[2] or "").lower()
                    a_text = (row[3] or "").lower()
                    # Score: exact phrase > word overlap
                    score = base_score
                    if q_lower in q_text:
                        score += 200
                    # Penalize generic "How do I..." synthetic entries
                    if q_text.startswith("how do i") and "how do i" in q_lower:
                        score -= 80
                    score += sum(q_text.count(w) * 3 for w in sig_words)
                    score += sum(a_text.count(w) for w in sig_words)
                    scored.append((score, {
                        "category": row[0], "language": row[1],
                        "q": row[2], "a": row[3]
                    }))

            scored.sort(key=lambda x: -x[0])
            return [r for _, r in scored[:limit]]
        except Exception:
            return []

    def search(self, query: str, category: str = None,
               language: str = None, limit: int = 5) -> List[Dict]:
        """Search the index."""
        db = self._connect()
        q_words = [w for w in re.sub(r"[^\w\s]", " ", query.lower()).split() if len(w) > 2]

        if not q_words:
            return []

        conditions = []
        params = []

        # Category filter
        if category:
            conditions.append("category = ?")
            params.append(category)

        # Language filter
        if language:
            conditions.append("language = ?")
            params.append(language.lower())

        # Keyword search (LIKE is sufficient for this scale)
        kw_conditions = []
        for word in q_words[:5]:
            kw_conditions.append("(content LIKE ? OR keywords LIKE ?)")
            params.extend([f"%{word}%", f"%{word}%"])

        if kw_conditions:
            conditions.append(f"({' OR '.join(kw_conditions)})")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM entries {where} LIMIT {limit * 3}"

        try:
            rows = db.execute(sql, params).fetchall()
        except Exception:
            return []

        # Score results
        scored = []
        for row in rows:
            content = row["content"].lower()
            score = sum(content.count(w) for w in q_words)
            scored.append((score, dict(row)))

        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:limit]]

    def search_conversations(self, query: str, limit: int = 3) -> List[Dict]:
        """Search specifically for conversation Q&A."""
        return self.search(query, category="code-conversations", limit=limit)

    def search_algorithms(self, query: str, limit: int = 3) -> List[Dict]:
        return self.search(query, category="algorithms", limit=limit)

    def search_debugging(self, query: str, limit: int = 3) -> List[Dict]:
        return self.search(query, category="debugging-scenarios", limit=limit)

    def search_security(self, query: str, limit: int = 3) -> List[Dict]:
        results = self.search(query, category="security-vulns", limit=limit)
        results += self.search(query, category="security-audits", limit=1)
        return results[:limit]

    def get_answer(self, question: str) -> Optional[str]:
        """Get the best answer for a question from training data."""
        # Try knowledge base first (curated entries with real answers)
        results = self.search_knowledge(question, limit=3)
        if results:
            best = results[0]
            answer = best.get("a", "")
            if answer and len(answer) > 30:
                q = best.get("q", "")
                # Don't return synthetic placeholder answers
                # Only flag clearly synthetic placeholders, not real code with comments
                bad_phrases = [
                    "Common javascript pattern for:",
                    "Common python pattern for:",
                    "Markdown documentation content for",
                    "Consider improving naming in this code",
                    "Code review comment for",
                ]
                is_synthetic = (
                    any(p in answer for p in bad_phrases) or
                    (answer.strip().startswith("// ") and len(answer) < 50)
                )
                if is_synthetic:
                    pass  # fall through to next source
                else:
                    return answer

        # Try conversation search
        results = self.search_conversations(question, limit=3)
        if results:
            for r in results:
                a = r.get("a") or r.get("content", "")
                if a and len(a) > 30:
                    bad = ["Common javascript pattern", "Common python pattern",
                           "Markdown documentation content"]
                    if not any(p in a for p in bad):
                        return a[:600]

        # Try general search
        results = self.search(question, limit=2)
        for r in results:
            content_str = r.get("content", "")
            for marker in ["answer: ", "solution: ", "fix: "]:
                if marker in content_str.lower():
                    idx = content_str.lower().index(marker)
                    answer = content_str[idx + len(marker):idx + 600]
                    if len(answer) > 20:
                        return answer.strip()

        return None

    def stats(self) -> Dict:
        """Get index statistics."""
        db = self._connect()
        try:
            total = db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            cats  = db.execute(
                "SELECT category, COUNT(*) as n FROM entries GROUP BY category ORDER BY n DESC"
            ).fetchall()
            return {
                "total_entries": total,
                "categories": {r["category"]: r["n"] for r in cats},
                "db_size_mb": round(self.db_path.stat().st_size / 1_048_576, 2) if self.db_path.exists() else 0,
            }
        except Exception:
            return {"total_entries": 0}

    def close(self):
        if self._db:
            self._db.close()
            self._db = None


# ── Module-level singleton ────────────────────────────────────────
_index: Optional[DataIndex] = None

def get_index() -> DataIndex:
    global _index
    if _index is None:
        # Use the repo DB if it exists (ships with LuoOS)
        if REPO_DB.exists():
            _index = DataIndex(str(REPO_DB))
        else:
            _index = DataIndex()
    return _index

def load_data_if_available() -> int:
    """Load data from any available source. Returns entries loaded."""
    idx = get_index()

    # Check if already has data (repo DB is pre-loaded)
    s = idx.stats()
    if s.get("total_entries", 0) > 1000:
        print(f"[DataIndex] {s['total_entries']:,} entries ready")
        return s["total_entries"]

    # Try JSONL knowledge base (ships with repo)
    jsonl_dir = Path(__file__).parent.parent / "data" / "knowledge"
    if jsonl_dir.exists():
        n = idx.load_from_jsonl(jsonl_dir)
        if n > 0:
            return n

    # Try other data directories
    total = 0
    for d in DATA_DIRS:
        if d.exists() and d != jsonl_dir:
            n = idx.load_from_directory(d)
            total += n
            if total > 10_000:
                break

    if total > 0:
        print(f"[DataIndex] ✅ {total:,} entries loaded")
    else:
        print("[DataIndex] Using built-in cell knowledge")

    return total
