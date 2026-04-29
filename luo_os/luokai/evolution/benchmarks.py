#!/usr/bin/env python3
"""
LUOKAI Benchmark Library
========================
Comprehensive benchmarks for evaluating AI capabilities across domains.

This library provides:
- Domain-specific challenges with difficulty scaling
- Standardized evaluation criteria
- Progression tracking
- Training data generation

Created by Luo Kai (luokai25) — Enhanced by Claude Code
"""
import json
import random
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class Challenge:
    """A single challenge with question and evaluation criteria."""
    id: str
    domain: str
    difficulty: int  # 1-10
    question: str
    expected_approach: str
    scoring_criteria: List[str]
    time_limit: int = 60  # seconds
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class BenchmarkLibrary:
    """
    Library of benchmarks across multiple domains.
    Each domain has challenges at different difficulty levels.
    """

    VERSION = "2.0"

    def __init__(self, data_dir: str = "~/.luo_os/benchmarks"):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._challenges: Dict[str, List[Challenge]] = {}
        self._load_builtin_challenges()

    def _load_builtin_challenges(self):
        """Load all built-in challenges."""
        # Reasoning challenges
        self._add_reasoning_challenges()

        # Coding challenges
        self._add_coding_challenges()

        # Math challenges
        self._add_math_challenges()

        # Language challenges
        self._add_language_challenges()

        # Planning challenges
        self._add_planning_challenges()

        # Tool use challenges
        self._add_tool_use_challenges()

        # Multi-step logic
        self._add_logic_challenges()

        # Creative writing
        self._add_creative_challenges()

        # Summarization
        self._add_summarization_challenges()

        # Debate challenges
        self._add_debate_challenges()

    def _add_reasoning_challenges(self):
        """Add reasoning domain challenges."""
        challenges = [
            # Difficulty 1-3: Basic
            Challenge(
                id="reasoning_01",
                domain="reasoning",
                difficulty=1,
                question="If all cats are mammals, and all mammals are animals, what can we conclude about cats?",
                expected_approach="Apply transitive property of logic: A ⊆ B and B ⊆ C implies A ⊆ C",
                scoring_criteria=["correct conclusion", "clear reasoning", "no logical fallacies"]
            ),
            Challenge(
                id="reasoning_02",
                domain="reasoning",
                difficulty=2,
                question="A farmer has 17 sheep. All but 9 run away. How many sheep does the farmer have left?",
                expected_approach="Understand that 'all but 9 run away' means 9 remain",
                scoring_criteria=["correct answer (9)", "explains reasoning", "catches linguistic trick"]
            ),
            Challenge(
                id="reasoning_03",
                domain="reasoning",
                difficulty=3,
                question="If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
                expected_approach="Recognize parallel processing: each machine makes 1 widget in 5 minutes",
                scoring_criteria=["correct answer (5 minutes)", "explains parallelism", "avoids linear scaling trap"]
            ),
            # Difficulty 4-6: Intermediate
            Challenge(
                id="reasoning_04",
                domain="reasoning",
                difficulty=5,
                question="You have 12 balls, one weighs differently (heavier or lighter). Using a balance scale only 3 times, how do you find the odd ball and determine if it's heavier or lighter?",
                expected_approach="Divide balls into groups, use elimination with each weighing",
                scoring_criteria=["correct algorithm", "works for both heavier/lighter", "efficient use of weighings"]
            ),
            Challenge(
                id="reasoning_05",
                domain="reasoning",
                difficulty=6,
                question="In a room of people, everyone shakes hands with everyone else exactly once. If there are 66 handshakes total, how many people are in the room?",
                expected_approach="Use combination formula: n(n-1)/2 = 66, solve for n",
                scoring_criteria=["correct answer (12)", "shows formula", "explains reasoning"]
            ),
            # Difficulty 7-10: Advanced
            Challenge(
                id="reasoning_06",
                domain="reasoning",
                difficulty=8,
                question="Three logicians walk into a bar. The bartender asks 'Does everyone want a beer?' The first says 'I don't know.' The second says 'I don't know.' The third says 'Yes!' Explain the logic.",
                expected_approach="Analyze the iterated knowledge: each must know all previous want beer to say yes",
                scoring_criteria=["correct explanation", "understands knowledge iteration", "clear logical steps"]
            ),
        ]
        self._challenges["reasoning"] = challenges

    def _add_coding_challenges(self):
        """Add coding domain challenges."""
        challenges = [
            # Difficulty 1-3: Basic
            Challenge(
                id="coding_01",
                domain="coding",
                difficulty=1,
                question="Write a function that returns the sum of two numbers.",
                expected_approach="Simple function with two parameters returning their sum",
                scoring_criteria=["correct syntax", "handles edge cases", "clear variable names"]
            ),
            Challenge(
                id="coding_02",
                domain="coding",
                difficulty=2,
                question="Write a function that reverses a string without using built-in reverse functions.",
                expected_approach="Iterate from end to start, or use slicing",
                scoring_criteria=["correct output", "no built-in reverse", "efficient implementation"]
            ),
            Challenge(
                id="coding_03",
                domain="coding",
                difficulty=3,
                question="Write a function that checks if a string is a palindrome.",
                expected_approach="Compare characters from start and end, handle case sensitivity",
                scoring_criteria=["correct logic", "handles edge cases", "efficient"]
            ),
            # Difficulty 4-6: Intermediate
            Challenge(
                id="coding_04",
                domain="coding",
                difficulty=5,
                question="Implement a function to find the longest palindromic substring in O(n²) time.",
                expected_approach="Expand around center for each position, track longest",
                scoring_criteria=["correct algorithm", "O(n²) time complexity", "handles edge cases"]
            ),
            Challenge(
                id="coding_05",
                domain="coding",
                difficulty=6,
                question="Write a function that validates if a Sudoku board is valid.",
                expected_approach="Check rows, columns, and 3x3 boxes for duplicates",
                scoring_criteria=["complete validation", "efficient data structures", "clear code"]
            ),
            # Difficulty 7-10: Advanced
            Challenge(
                id="coding_06",
                domain="coding",
                difficulty=8,
                question="Implement an LRU (Least Recently Used) cache with O(1) get and put operations.",
                expected_approach="Use doubly-linked list + hash map combination",
                scoring_criteria=["correct O(1) operations", "thread-safe optional", "clean implementation"]
            ),
        ]
        self._challenges["coding"] = challenges

    def _add_math_challenges(self):
        """Add math domain challenges."""
        challenges = [
            Challenge(
                id="math_01",
                domain="math",
                difficulty=1,
                question="What is 17 × 23?",
                expected_approach="Mental math or standard multiplication",
                scoring_criteria=["correct answer (391)", "shows work"]
            ),
            Challenge(
                id="math_02",
                domain="math",
                difficulty=3,
                question="Prove that the sum of angles in any triangle is 180 degrees.",
                expected_approach="Use parallel line properties and alternate interior angles",
                scoring_criteria=["correct proof", "clear steps", "uses Euclidean axioms"]
            ),
            Challenge(
                id="math_03",
                domain="math",
                difficulty=5,
                question="Find the derivative of f(x) = x³sin(x).",
                expected_approach="Apply product rule: 3x²sin(x) + x³cos(x)",
                scoring_criteria=["correct result", "shows product rule", "simplifies if possible"]
            ),
            Challenge(
                id="math_04",
                domain="math",
                difficulty=7,
                question="Find all solutions to x² + y² = 25 where x and y are integers.",
                expected_approach="List all Pythagorean triples with hypotenuse 5",
                scoring_criteria=["finds all solutions", "systematic approach", "verifies solutions"]
            ),
            Challenge(
                id="math_05",
                domain="math",
                difficulty=9,
                question="Prove that there are infinitely many prime numbers.",
                expected_approach="Euclid's proof by contradiction",
                scoring_criteria=["correct proof structure", "clear contradiction", "complete reasoning"]
            ),
        ]
        self._challenges["math"] = challenges

    def _add_language_challenges(self):
        """Add language domain challenges."""
        challenges = [
            Challenge(
                id="lang_01",
                domain="language",
                difficulty=1,
                question="Explain the difference between 'their', 'there', and 'they're'.",
                expected_approach="Define each word, give examples",
                scoring_criteria=["correct definitions", "clear examples", "memorable explanation"]
            ),
            Challenge(
                id="lang_02",
                domain="language",
                difficulty=3,
                question="Rewrite this sentence to be more concise: 'Due to the fact that it was raining heavily, we made the decision to stay inside.'",
                expected_approach="Remove wordiness: 'Because it was raining heavily, we stayed inside.'",
                scoring_criteria=["concise rewrite", "preserves meaning", "natural phrasing"]
            ),
            Challenge(
                id="lang_03",
                domain="language",
                difficulty=5,
                question="Identify and fix the ambiguity in: 'I saw the man with the telescope.'",
                expected_approach="Explain two readings: man has telescope vs. I used telescope",
                scoring_criteria=["identifies both meanings", "provides fixes", "clear explanation"]
            ),
            Challenge(
                id="lang_04",
                domain="language",
                difficulty=7,
                question="Translate this idiom to another language and explain if a literal translation would work: 'It's raining cats and dogs.'",
                expected_approach="Provide equivalent idiom or literal translation with cultural note",
                scoring_criteria=["correct translation", "cultural awareness", "explains idiom meaning"]
            ),
        ]
        self._challenges["language"] = challenges

    def _add_planning_challenges(self):
        """Add planning domain challenges."""
        challenges = [
            Challenge(
                id="planning_01",
                domain="planning",
                difficulty=2,
                question="Plan a 3-day trip to a city you've never visited. Include accommodation, activities, and meals.",
                expected_approach="Day-by-day breakdown with logical sequencing",
                scoring_criteria=["realistic timeline", "diverse activities", "practical logistics"]
            ),
            Challenge(
                id="planning_02",
                domain="planning",
                difficulty=4,
                question="Create a study plan for learning a new programming language in 30 days.",
                expected_approach="Progressive difficulty, hands-on practice, project milestones",
                scoring_criteria=["structured progression", "specific resources", "measurable goals"]
            ),
            Challenge(
                id="planning_03",
                domain="planning",
                difficulty=6,
                question="Design a backup and disaster recovery plan for a small business with 10 employees.",
                expected_approach="3-2-1 backup rule, recovery time objectives, cloud + local",
                scoring_criteria=["comprehensive coverage", "realistic costs", "clear procedures"]
            ),
            Challenge(
                id="planning_04",
                domain="planning",
                difficulty=8,
                question="Plan the launch of a new software product, including development timeline, marketing strategy, and go-to-market approach.",
                expected_approach="Phased approach with milestones, MVP definition, launch criteria",
                scoring_criteria=["realistic timeline", "complete marketing mix", "risk mitigation"]
            ),
        ]
        self._challenges["planning"] = challenges

    def _add_tool_use_challenges(self):
        """Add tool use domain challenges."""
        challenges = [
            Challenge(
                id="tool_01",
                domain="tool_use",
                difficulty=2,
                question="Read a file named 'data.txt' and count the number of lines containing the word 'error'.",
                expected_approach="Use file reading + string counting",
                scoring_criteria=["correct command", "efficient approach", "handles errors"]
            ),
            Challenge(
                id="tool_02",
                domain="tool_use",
                difficulty=4,
                question="Find all Python files in the current directory and subdirectories that contain the word 'import pandas'.",
                expected_approach="Use grep with find or ripgrep",
                scoring_criteria=["correct command", "recursive search", "file type filter"]
            ),
            Challenge(
                id="tool_03",
                domain="tool_use",
                difficulty=6,
                question="Extract all email addresses from a website's contact page.",
                expected_approach="Web fetch + regex pattern matching",
                scoring_criteria=["correct regex", "handles various formats", "ethical consideration"]
            ),
            Challenge(
                id="tool_04",
                domain="tool_use",
                difficulty=8,
                question="Set up a simple web server that serves files from a directory and logs all requests.",
                expected_approach="Use Python http.server or similar with logging",
                scoring_criteria=["working server", "proper logging", "security considerations"]
            ),
        ]
        self._challenges["tool_use"] = challenges

    def _add_logic_challenges(self):
        """Add multi-step logic challenges."""
        challenges = [
            Challenge(
                id="logic_01",
                domain="multi_step_logic",
                difficulty=3,
                question="A train leaves station A at 9am going 60mph. Another leaves station B at 10am going 80mph in the same direction. Stations A and B are 40 miles apart. When and where does the second train catch the first?",
                expected_approach="Calculate positions over time, solve for intersection",
                scoring_criteria=["correct time", "correct position", "shows work"]
            ),
            Challenge(
                id="logic_02",
                domain="multi_step_logic",
                difficulty=5,
                question="You have 8 balls. Seven weigh the same, one is heavier. Using a balance scale, find the heavy ball in exactly 2 weighings.",
                expected_approach="Divide into 3 groups: 3-3-2, compare two groups of 3",
                scoring_criteria=["correct algorithm", "exactly 2 weighings", "clear explanation"]
            ),
            Challenge(
                id="logic_03",
                domain="multi_step_logic",
                difficulty=7,
                question="A king places a gold or silver crown on each of three wise men. Each can see the other two crowns but not his own. The king says at least one crown is gold. He asks each in turn: 'Do you know your crown?' First says no, second says no. Does the third know?",
                expected_approach="Analyze the iterated knowledge: third deduces from others' ignorance",
                scoring_criteria=["correct answer", "shows logical steps", "understands knowledge iteration"]
            ),
        ]
        self._challenges["multi_step_logic"] = challenges

    def _add_creative_challenges(self):
        """Add creative writing challenges."""
        challenges = [
            Challenge(
                id="creative_01",
                domain="creative_writing",
                difficulty=2,
                question="Write a haiku about programming.",
                expected_approach="5-7-5 syllable structure, coding theme",
                scoring_criteria=["correct structure", "evocative imagery", "programming relevance"]
            ),
            Challenge(
                id="creative_02",
                domain="creative_writing",
                difficulty=4,
                question="Write a short story (100 words) that ends with '...and that's why I never trust cats.'",
                expected_approach="Build to punchline with coherent narrative",
                scoring_criteria=["engaging story", "logical ending", "exactly 100 words"]
            ),
            Challenge(
                id="creative_03",
                domain="creative_writing",
                difficulty=6,
                question="Write a dialogue between two characters who are secretly planning a surprise party for the reader.",
                expected_approach="Fourth-wall breaking, conspiratorial tone",
                scoring_criteria=["engaging dialogue", "clever premise", "suspense"]
            ),
            Challenge(
                id="creative_04",
                domain="creative_writing",
                difficulty=8,
                question="Write a science fiction story in exactly six words.",
                expected_approach="Hemingway-style extreme brevity with impact",
                scoring_criteria=["exactly six words", "complete story arc", "emotional impact"]
            ),
        ]
        self._challenges["creative_writing"] = challenges

    def _add_summarization_challenges(self):
        """Add summarization challenges."""
        challenges = [
            Challenge(
                id="summary_01",
                domain="summarization",
                difficulty=2,
                question="Summarize this paragraph in one sentence: 'The Internet has transformed how we communicate, work, and live. It began as a military project in the 1960s, evolved through academic networks, and became commercially available in the 1990s. Today, billions of people rely on it for everything from entertainment to education, making it one of humanity's most significant inventions.'",
                expected_approach="Extract key points: origin, evolution, global impact",
                scoring_criteria=["concise", "covers key points", "one sentence"]
            ),
            Challenge(
                id="summary_02",
                domain="summarization",
                difficulty=4,
                question="Create a bulleted summary of 3 key takeaways from a text about climate change.",
                expected_approach="Identify 3 distinct main points, present clearly",
                scoring_criteria=["distinct points", "accurate representation", "clear bullets"]
            ),
            Challenge(
                id="summary_03",
                domain="summarization",
                difficulty=6,
                question="Summarize a technical article for a non-technical audience without losing the core message.",
                expected_approach="Translate jargon, keep essence, use analogies",
                scoring_criteria=["accessible language", "preserves core message", "appropriate length"]
            ),
        ]
        self._challenges["summarization"] = challenges

    def _add_debate_challenges(self):
        """Add debate challenges."""
        challenges = [
            Challenge(
                id="debate_01",
                domain="debate",
                difficulty=3,
                question="Present two arguments for and two against: 'Social media does more harm than good.'",
                expected_approach="Balanced presentation of valid arguments on each side",
                scoring_criteria=["balanced", "valid arguments each side", "clear structure"]
            ),
            Challenge(
                id="debate_02",
                domain="debate",
                difficulty=5,
                question="Argue for a position you disagree with: 'Artificial intelligence will create more jobs than it destroys.' Present the strongest case.",
                expected_approach="Steel-man the opposing position with strongest arguments",
                scoring_criteria=["compelling arguments", "logical support", "no straw man"]
            ),
            Challenge(
                id="debate_03",
                domain="debate",
                difficulty=7,
                question="In a debate, your opponent says 'Correlation doesn't imply causation, so we can't conclude anything from this data.' Provide a nuanced response.",
                expected_approach="Acknowledge truth of statement but explain what can still be concluded",
                scoring_criteria=["nuanced response", "acknowledges point", "advances argument"]
            ),
        ]
        self._challenges["debate"] = challenges

    def get_challenge(
        self,
        domain: str = None,
        difficulty: int = None,
        exclude_ids: List[str] = None
    ) -> Challenge:
        """
        Get a random challenge, optionally filtered by domain and difficulty.

        Args:
            domain: Challenge domain (reasoning, coding, etc.)
            difficulty: Maximum difficulty level (1-10)
            exclude_ids: Challenge IDs to exclude

        Returns:
            A Challenge object
        """
        exclude_ids = exclude_ids or []

        if domain and domain in self._challenges:
            pool = [c for c in self._challenges[domain] if c.id not in exclude_ids]
        else:
            pool = [c for challenges in self._challenges.values() for c in challenges if c.id not in exclude_ids]

        if difficulty:
            pool = [c for c in pool if c.difficulty <= difficulty]

        if not pool:
            # Fallback to a generated challenge
            return self._generate_challenge(domain or "reasoning", difficulty or 5)

        return random.choice(pool)

    def _generate_challenge(self, domain: str, difficulty: int) -> Challenge:
        """Generate a simple challenge if pool is empty."""
        templates = {
            "reasoning": "Solve this logic puzzle: {puzzle}",
            "coding": "Write a function that {task}",
            "math": "Solve this problem: {problem}",
            "language": "Explain the difference between {concept1} and {concept2}.",
            "planning": "Create a plan for {goal}.",
        }

        template = templates.get(domain, "Complete this task: {task}")
        question = template.format(
            puzzle="A problem requiring logical deduction",
            task="performs a specific operation efficiently",
            problem="a mathematical equation or proof",
            concept1="concept A",
            concept2="concept B",
            goal="achieving a specific objective"
        )

        return Challenge(
            id=f"{domain}_gen_{hashlib.md5(question.encode()).hexdigest()[:8]}",
            domain=domain,
            difficulty=difficulty,
            question=question,
            expected_approach="Solve systematically",
            scoring_criteria=["correctness", "clarity", "efficiency"]
        )

    def get_domains(self) -> List[str]:
        """Get list of all challenge domains."""
        return list(self._challenges.keys())

    def get_difficulty_range(self, domain: str) -> Tuple[int, int]:
        """Get min and max difficulty for a domain."""
        if domain not in self._challenges or not self._challenges[domain]:
            return (1, 10)
        difficulties = [c.difficulty for c in self._challenges[domain]]
        return (min(difficulties), max(difficulties))

    def get_challenge_count(self, domain: str = None) -> int:
        """Get total number of challenges."""
        if domain and domain in self._challenges:
            return len(self._challenges[domain])
        return sum(len(c) for c in self._challenges.values())

    def export_training_data(self, output_file: str = None) -> List[Dict]:
        """
        Export challenges as training data format.
        Useful for fine-tuning models on these benchmarks.
        """
        training_data = []
        for domain, challenges in self._challenges.items():
            for challenge in challenges:
                training_data.append({
                    "id": challenge.id,
                    "domain": challenge.domain,
                    "difficulty": challenge.difficulty,
                    "instruction": challenge.question,
                    "expected_approach": challenge.expected_approach,
                    "scoring_criteria": challenge.scoring_criteria,
                    "tags": challenge.tags,
                })

        if output_file:
            Path(output_file).write_text(json.dumps(training_data, indent=2))

        return training_data


# Convenience functions
def get_random_challenge(domain: str = None, difficulty: int = None) -> Challenge:
    """Quick function to get a random challenge."""
    lib = BenchmarkLibrary()
    return lib.get_challenge(domain, difficulty)


def list_benchmark_domains() -> List[str]:
    """Quick function to list all domains."""
    lib = BenchmarkLibrary()
    return lib.get_domains()


if __name__ == "__main__":
    # Test the benchmark library
    lib = BenchmarkLibrary()

    print(f"Benchmark Library v{lib.VERSION}")
    print(f"Domains: {lib.get_domains()}")
    print(f"Total challenges: {lib.get_challenge_count()}")

    for domain in lib.get_domains():
        min_d, max_d = lib.get_difficulty_range(domain)
        print(f"  {domain}: {lib.get_challenge_count(domain)} challenges (difficulty {min_d}-{max_d})")

    print("\nSample challenges:")
    for domain in lib.get_domains()[:3]:
        challenge = lib.get_challenge(domain=domain)
        print(f"\n[{challenge.domain}] Difficulty {challenge.difficulty}/10")
        print(f"Q: {challenge.question}")
        print(f"Expected: {challenge.expected_approach}")