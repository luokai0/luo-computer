#!/usr/bin/env python3
"""
LUOKAI Tree of Thought (ToT) Reasoning Module
==============================================
Implements multi-path reasoning for complex problems.

Based on research from:
- LightAgent Tree of Thought patterns
- Google ADK reasoning chains
- DeepSeek-R1 reasoning models

The ToT approach explores multiple reasoning paths,
evaluates each one, and backtracks from failed paths
to find the optimal solution.

Created by Luo Kai (luokai25) — Enhanced by Claude Code
"""
import json
import time
import urllib.request
from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from heapq import heappush, heappop


class ThoughtState(Enum):
    PENDING = "pending"
    EXPLORING = "exploring"
    EVALUATED = "evaluated"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PRUNED = "pruned"


@dataclass
class Thought:
    """A single thought node in the reasoning tree."""
    id: str
    content: str
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    state: ThoughtState = ThoughtState.PENDING
    score: float = 0.0
    depth: int = 0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "parent_id": self.parent_id,
            "children": self.children,
            "state": self.state.value,
            "score": self.score,
            "depth": self.depth,
            "metadata": self.metadata
        }


@dataclass
class ReasoningPath:
    """A complete reasoning path from root to leaf."""
    thoughts: List[Thought]
    total_score: float
    final_answer: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "thoughts": [t.to_dict() for t in self.thoughts],
            "total_score": self.total_score,
            "final_answer": self.final_answer
        }


class TreeOfThought:
    """
    Tree of Thought reasoning engine.

    Explores multiple reasoning paths to solve complex problems.
    Uses branch-and-bound to prune low-value paths.

    Usage:
        tot = TreeOfThought()
        result = tot.solve("What is the best sorting algorithm for nearly-sorted data?")
    """

    def __init__(
        self,
        max_depth: int = 5,
        max_branches: int = 3,
        beam_width: int = 3,
        temperature: float = 0.7
    ):
        self.model = "luokai-1.0"
        self.max_depth = max_depth
        self.max_branches = max_branches
        self.beam_width = beam_width
        self.temperature = temperature

        self.thoughts: Dict[str, Thought] = {}
        self.root_id: Optional[str] = None
        self._thought_counter = 0

    def solve(
        self,
        problem: str,
        approaches: List[str] = None,
        on_thought: Callable[[Thought], None] = None
    ) -> ReasoningPath:
        """
        Solve a problem using Tree of Thought reasoning.

        Args:
            problem: The problem to solve
            approaches: List of reasoning approaches (default: analytical, creative, systematic)
            on_thought: Callback for each thought generated

        Returns:
            The best reasoning path found
        """
        # Initialize approaches
        if approaches is None:
            approaches = ["analytical", "creative", "systematic"]

        # Create root thought
        self.root_id = self._create_thought(
            content=f"Problem: {problem}",
            depth=0
        )

        # Generate initial thoughts for each approach
        initial_thoughts = []
        for approach in approaches:
            thought_content = self._generate_initial_thought(problem, approach)
            thought_id = self._create_thought(
                content=thought_content,
                parent_id=self.root_id,
                depth=1,
                metadata={"approach": approach}
            )
            initial_thoughts.append(thought_id)

        # Explore thoughts using beam search
        best_paths = self._beam_search(
            problem=problem,
            initial_thoughts=initial_thoughts,
            on_thought=on_thought
        )

        # Synthesize final answer from best paths
        if best_paths:
            best_path = best_paths[0]
            best_path.final_answer = self._synthesize_answer(problem, best_path)
            return best_path

        # Fallback: direct answer
        return ReasoningPath(
            thoughts=[self.thoughts[self.root_id]],
            total_score=0.0,
            final_answer=self._call_llm(f"Solve this problem directly: {problem}")
        )

    def _generate_initial_thought(self, problem: str, approach: str) -> str:
        """Generate an initial thought for an approach."""
        prompts = {
            "analytical": f"""Think about this problem step by step using logical analysis.

Problem: {problem}

Break it down into:
1. What are the key components?
2. What constraints exist?
3. What approaches might work?

Provide your initial analysis in 2-3 sentences.""",

            "creative": f"""Think about this problem creatively and explore unconventional solutions.

Problem: {problem}

Consider:
- What if we approached this differently?
- What analogies might help?
- What's an unexpected angle?

Provide a creative initial thought in 2-3 sentences.""",

            "systematic": f"""Think about this problem systematically using a structured approach.

Problem: {problem}

Apply:
1. Define the problem precisely
2. Identify inputs and outputs
3. Consider standard solutions

Provide your systematic analysis in 2-3 sentences."""
        }

        return self._call_llm(prompts.get(approach, prompts["analytical"]))

    def _beam_search(
        self,
        problem: str,
        initial_thoughts: List[str],
        on_thought: Callable = None
    ) -> List[ReasoningPath]:
        """Perform beam search through the thought tree."""
        beam = []  # (score, thought_id)

        # Add initial thoughts to beam
        for tid in initial_thoughts:
            score = self._evaluate_thought(self.thoughts[tid])
            heappush(beam, (-score, tid))

        completed_paths = []

        while beam and len(completed_paths) < self.beam_width:
            # Get best thought from beam
            neg_score, current_id = heappop(beam)
            current = self.thoughts[current_id]
            current.score = -neg_score

            if on_thought:
                on_thought(current)

            # Check if we've reached max depth
            if current.depth >= self.max_depth:
                current.state = ThoughtState.EVALUATED
                path = self._build_path(current_id)
                completed_paths.append(path)
                continue

            # Generate next thoughts
            current.state = ThoughtState.EXPLORING
            next_thoughts = self._generate_next_thoughts(problem, current)

            for next_content in next_thoughts:
                next_id = self._create_thought(
                    content=next_content,
                    parent_id=current_id,
                    depth=current.depth + 1
                )
                current.children.append(next_id)

                next_score = self._evaluate_thought(self.thoughts[next_id])

                # Prune low-scoring branches
                if next_score < 0.3:  # Threshold for pruning
                    self.thoughts[next_id].state = ThoughtState.PRUNED
                    continue

                heappush(beam, (-next_score, next_id))

        # If no paths completed, use current best
        if not completed_paths and beam:
            _, best_id = beam[0]
            completed_paths = [self._build_path(best_id)]

        return sorted(completed_paths, key=lambda p: p.total_score, reverse=True)

    def _generate_next_thoughts(self, problem: str, current: Thought) -> List[str]:
        """Generate next thoughts branching from current."""
        # Build context from path
        path = self._build_path(current.id)
        context = "\n".join([t.content for t in path.thoughts])

        prompt = f"""Given the problem and reasoning so far, what are the next logical steps?

Problem: {problem}

Reasoning so far:
{context}

Generate {self.max_branches} possible next steps. Each step should:
1. Build on previous reasoning
2. Explore a different aspect
3. Move closer to a solution

Format: One step per line, numbered."""

        response = self._call_llm(prompt)

        # Parse steps
        steps = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering
                step = line.lstrip('0123456789.-) ').strip()
                if step:
                    steps.append(step)

        return steps[:self.max_branches]

    def _evaluate_thought(self, thought: Thought) -> float:
        """Evaluate the quality of a thought."""
        prompt = f"""Evaluate this reasoning step on a scale of 0 to 1.

Reasoning step: {thought.content}

Evaluate based on:
- Logical coherence (0.25 weight)
- Progress toward solution (0.25 weight)
- Insight quality (0.25 weight)
- Actionability (0.25 weight)

Respond with just a number between 0 and 1."""

        try:
            response = self._call_llm(prompt).strip()
            # Extract number
            import re
            match = re.search(r'[0-9]*\.?[0-9]+', response)
            if match:
                return float(match.group())
        except Exception:
            pass

        return 0.5  # Default score

    def _synthesize_answer(self, problem: str, path: ReasoningPath) -> str:
        """Synthesize a final answer from a reasoning path."""
        thoughts_text = "\n".join([
            f"Step {i+1}: {t.content}"
            for i, t in enumerate(path.thoughts)
        ])

        prompt = f"""Based on the reasoning steps below, provide a clear, complete answer.

Problem: {problem}

Reasoning:
{thoughts_text}

Provide the final answer, synthesizing the insights from all steps:"""

        return self._call_llm(prompt)

    def _build_path(self, leaf_id: str) -> ReasoningPath:
        """Build a path from root to leaf."""
        thoughts = []
        current_id = leaf_id
        total_score = 0.0

        while current_id:
            thought = self.thoughts[current_id]
            thoughts.insert(0, thought)
            total_score += thought.score
            current_id = thought.parent_id

        return ReasoningPath(
            thoughts=thoughts,
            total_score=total_score
        )

    def _create_thought(
        self,
        content: str,
        parent_id: str = None,
        depth: int = 0,
        metadata: Dict = None
    ) -> str:
        """Create a new thought node."""
        self._thought_counter += 1
        thought_id = f"thought_{self._thought_counter}"

        thought = Thought(
            id=thought_id,
            content=content,
            parent_id=parent_id,
            depth=depth,
            metadata=metadata or {}
        )

        self.thoughts[thought_id] = thought
        return thought_id

    def _call_llm(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate using LUOKAI's native inference engine."""
        from luokai.core.inference import get_inference
        try:
            return get_inference().generate(
                [{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
        except Exception as e:
            return f"[Inference error: {e}]"

    def visualize(self) -> str:
        """Generate a text visualization of the thought tree."""
        lines = []

        def render_tree(thought_id: str, prefix: str = ""):
            thought = self.thoughts.get(thought_id)
            if not thought:
                return

            status = {
                ThoughtState.PENDING: "⚪",
                ThoughtState.EXPLORING: "🔵",
                ThoughtState.EVALUATED: "🟡",
                ThoughtState.SUCCEEDED: "🟢",
                ThoughtState.FAILED: "🔴",
                ThoughtState.PRUNED: "⚫"
            }.get(thought.state, "⚪")

            lines.append(f"{prefix}{status} [{thought.score:.2f}] {thought.content[:50]}...")

            for child_id in thought.children:
                render_tree(child_id, prefix + "  ")

        if self.root_id:
            render_tree(self.root_id)

        return "\n".join(lines)

    def export(self) -> Dict:
        """Export the thought tree as a dictionary."""
        return {
            "thoughts": {tid: t.to_dict() for tid, t in self.thoughts.items()},
            "root_id": self.root_id
        }


# Convenience function
def solve_with_tot(
    problem: str,
    approaches: List[str] = None
) -> Tuple[str, ReasoningPath]:
    """Solve a problem using Tree of Thought reasoning."""
    tot = TreeOfThought()
    path = tot.solve(problem, approaches=approaches)
    return path.final_answer, path


if __name__ == "__main__":
    # Test the Tree of Thought engine
    print("Tree of Thought Reasoning Engine")
    print("=" * 50)

    tot = TreeOfThought(model="mistral")

    problem = "What's the most efficient way to find the median of two sorted arrays?"
    print(f"\nProblem: {problem}")
    print("\nReasoning...")

    path = tot.solve(problem)

    print("\n" + "=" * 50)
    print("Reasoning Path:")
    for i, thought in enumerate(path.thoughts):
        print(f"  {i+1}. [{thought.score:.2f}] {thought.content[:80]}...")

    print(f"\nTotal Score: {path.total_score:.2f}")
    print(f"\nFinal Answer:\n{path.final_answer}")

    print("\n" + "=" * 50)
    print("Thought Tree:")
    print(tot.visualize())