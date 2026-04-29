#!/usr/bin/env python3
"""
LUOKAI Skills Library — skills_library.py
==========================================
Loads and serves 4,146 real skills from the index built from:
  github.com/luokai0/ai-agent-skills-by-luo-kai

All skills are indexed at startup (fast JSON load, ~2MB).
Search is O(n) over descriptions — good enough for 4,146 skills.
For production, swap _search for a vector search over embeddings.
"""
import json
import re
from pathlib import Path
from typing import Optional

_INDEX_PATH = Path(__file__).parent / "skills_index.json"


class SkillsLibrary:
    """
    Singleton-style skills library.
    Load once, query many times.
    """

    def __init__(self):
        self._skills: list[dict] = []
        self._by_id: dict[str, dict] = {}
        self._categories: dict[str, list[dict]] = {}
        self._loaded = False
        self._load()

    # ── Loading ──────────────────────────────────────────────────────

    def _load(self):
        """Load the skills index from disk."""
        if not _INDEX_PATH.exists():
            print(f"[SkillsLibrary] ⚠️  Index not found at {_INDEX_PATH}")
            return

        try:
            with open(_INDEX_PATH, encoding="utf-8") as f:
                self._skills = json.load(f)

            for skill in self._skills:
                self._by_id[skill["id"]] = skill
                cat = skill.get("category", "uncategorized")
                self._categories.setdefault(cat, []).append(skill)

            self._loaded = True
            print(
                f"[SkillsLibrary] ✅ Loaded {len(self._skills):,} skills "
                f"across {len(self._categories)} categories"
            )
        except Exception as e:
            print(f"[SkillsLibrary] ❌ Failed to load: {e}")

    # ── Public API ───────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return summary statistics."""
        return {
            "total":      len(self._skills),
            "categories": len(self._categories),
            "loaded":     self._loaded,
            "category_counts": {
                cat: len(skills)
                for cat, skills in sorted(
                    self._categories.items(), key=lambda x: -len(x[1])
                )
            },
        }

    def categories(self) -> list[str]:
        """Return sorted category names."""
        return sorted(self._categories.keys())

    def list_category(self, category: str, limit: int = 50) -> list[dict]:
        """Return skills in a category (case-insensitive partial match)."""
        cat_lower = category.lower()
        for cat, skills in self._categories.items():
            if cat_lower in cat.lower():
                return [self._slim(s) for s in skills[:limit]]
        return []

    def get(self, skill_id: str) -> Optional[dict]:
        """Get a skill by its ID/slug."""
        skill = self._by_id.get(skill_id)
        if skill:
            return skill
        # Fuzzy: try partial match
        skill_id_lower = skill_id.lower()
        for sid, s in self._by_id.items():
            if skill_id_lower in sid.lower():
                return s
        return None

    def search(self, query: str, limit: int = 10, category: str = "") -> list[dict]:
        """
        Search skills by keyword.
        Searches: name, description, preview, id, category, subcategory.
        Optionally filter by category.
        Returns scored results sorted by relevance.
        """
        if not query:
            return []

        q = query.lower()
        terms = q.split()
        pool = self._skills

        if category:
            cat_lower = category.lower()
            pool = [
                s for s in pool
                if cat_lower in s.get("category", "").lower()
            ]

        scored = []
        for skill in pool:
            score = self._score(skill, q, terms)
            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: -x[0])
        return [self._slim(s) for _, s in scored[:limit]]

    def random_skills(self, n: int = 5, category: str = "") -> list[dict]:
        """Return n random skills, optionally from a category."""
        import random
        pool = self._categories.get(category, self._skills) if category else self._skills
        sample = random.sample(pool, min(n, len(pool)))
        return [self._slim(s) for s in sample]

    def invoke(self, skill_id: str, context: str = "") -> dict:
        """
        'Invoke' a skill — returns its full description and preview
        so the agent can use it as context/instruction.
        """
        skill = self.get(skill_id)
        if not skill:
            return {
                "ok": False,
                "error": f"Skill '{skill_id}' not found",
                "suggestion": self.search(skill_id, limit=3),
            }
        return {
            "ok":          True,
            "skill":       skill,
            "instruction": (
                f"Apply the '{skill['name']}' skill.\n"
                f"Category: {skill['category']}\n"
                f"Description: {skill['description']}\n"
                f"Context: {skill.get('preview', '')}"
            ),
        }

    # ── Internal helpers ─────────────────────────────────────────────

    def _score(self, skill: dict, query: str, terms: list[str]) -> int:
        """Score a skill against a query. Higher = more relevant."""
        score = 0
        name     = skill.get("name", "").lower()
        desc     = skill.get("description", "").lower()
        preview  = skill.get("preview", "").lower()
        sid      = skill.get("id", "").lower()
        cat      = skill.get("category", "").lower()
        subcat   = skill.get("subcategory", "").lower()
        full_text = f"{name} {sid} {desc} {preview} {cat} {subcat}"

        # Exact name match
        if query == name:
            score += 100
        # Name starts with query
        elif name.startswith(query):
            score += 50
        # Name contains query
        elif query in name:
            score += 30

        # All terms in description
        if all(t in desc for t in terms):
            score += 20
        # Any term in description
        score += sum(5 for t in terms if t in desc)

        # Category match
        if query in cat or query in subcat:
            score += 15

        # ID match
        if query in sid:
            score += 25

        # Preview match
        score += sum(2 for t in terms if t in preview)

        return score

    def _slim(self, skill: dict) -> dict:
        """Return a lightweight version for listings (no full preview)."""
        return {
            "id":          skill["id"],
            "name":        skill["name"],
            "category":    skill["category"],
            "subcategory": skill.get("subcategory", ""),
            "description": skill["description"][:120] + "..."
                           if len(skill.get("description", "")) > 120
                           else skill.get("description", ""),
        }


# ── Module-level singleton ───────────────────────────────────────────
_library: Optional[SkillsLibrary] = None


def get_library() -> SkillsLibrary:
    """Get or create the singleton SkillsLibrary."""
    global _library
    if _library is None:
        _library = SkillsLibrary()
    return _library
