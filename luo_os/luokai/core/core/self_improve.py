#!/usr/bin/env python3
"""
LUOKAI Self-Improvement Module
===============================
Implements continuous learning and self-improvement capabilities.

Features:
- Learning from interactions
- Storing successful patterns
- Analyzing failures
- Generating training data
- Prompt optimization

Created by Luo Kai (luokai25) — Enhanced by Claude Code
"""
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import urllib.request
import re


@dataclass
class Interaction:
    """A single interaction record."""
    id: str
    timestamp: str
    user_input: str
    response: str
    success: Optional[bool] = None
    feedback: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)
    response_time: float = 0.0
    tokens_used: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class Pattern:
    """A learned pattern."""
    id: str
    pattern_type: str  # "success", "failure", "tool_use", "reasoning"
    input_pattern: str  # Regex or description
    output_template: str
    success_rate: float
    usage_count: int
    last_used: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class TrainingExample:
    """A training example for fine-tuning."""
    instruction: str
    input: str
    output: str
    quality_score: float
    source: str  # Where this example came from
    metadata: Dict = field(default_factory=dict)


class SelfImprovementEngine:
    """
    Engine for continuous self-improvement.

    Tracks interactions, learns patterns, and generates training data.
    """

    def __init__(
        self,
        data_dir: str = "~/.luo_os/self_improve",
    ):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model = "luokai-1.0"

        # Data files
        self.interactions_file = self.data_dir / "interactions.jsonl"
        self.patterns_file = self.data_dir / "patterns.json"
        self.training_file = self.data_dir / "training_data.jsonl"
        self.metrics_file = self.data_dir / "metrics.json"

        # In-memory caches
        self._interactions: List[Interaction] = []
        self._patterns: List[Pattern] = []
        self._metrics: Dict = {}

        # Load existing data
        self._load_data()

        print(f"[SelfImprove] Engine initialized")
        print(f"[SelfImprove]   Interactions: {len(self._interactions)}")
        print(f"[SelfImprove]   Patterns: {len(self._patterns)}")

    def _load_data(self):
        """Load existing data from disk."""
        # Load interactions
        if self.interactions_file.exists():
            with open(self.interactions_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        self._interactions.append(Interaction(**data))
                    except Exception:
                        pass

        # Load patterns
        if self.patterns_file.exists():
            try:
                data = json.loads(self.patterns_file.read_text())
                self._patterns = [Pattern(**p) for p in data]
            except Exception:
                pass

        # Load metrics
        if self.metrics_file.exists():
            try:
                self._metrics = json.loads(self.metrics_file.read_text())
            except Exception:
                pass

    def _save_data(self):
        """Save data to disk."""
        # Save interactions
        with open(self.interactions_file, "a") as f:
            for interaction in self._interactions[-100:]:  # Save last 100
                f.write(json.dumps(interaction.__dict__) + "\n")

        # Save patterns
        self.patterns_file.write_text(json.dumps(
            [p.__dict__ for p in self._patterns],
            indent=2
        ))

        # Save metrics
        self.metrics_file.write_text(json.dumps(self._metrics, indent=2))

    def record_interaction(
        self,
        user_input: str,
        response: str,
        success: bool = None,
        feedback: str = None,
        tools_used: List[str] = None,
        response_time: float = 0.0,
        metadata: Dict = None
    ) -> Interaction:
        """Record an interaction for learning."""
        interaction = Interaction(
            id=hashlib.md5(f"{user_input}{time.time()}".encode()).hexdigest()[:8],
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            response=response,
            success=success,
            feedback=feedback,
            tools_used=tools_used or [],
            response_time=response_time,
            metadata=metadata or {}
        )

        self._interactions.append(interaction)

        # Update patterns
        self._extract_patterns(interaction)

        # Periodic save
        if len(self._interactions) % 10 == 0:
            self._save_data()

        return interaction

    def record_feedback(self, interaction_id: str, success: bool, feedback: str = None):
        """Record feedback on an interaction."""
        for interaction in self._interactions:
            if interaction.id == interaction_id:
                interaction.success = success
                interaction.feedback = feedback
                self._extract_patterns(interaction)
                break

    def _extract_patterns(self, interaction: Interaction):
        """Extract learnable patterns from an interaction."""
        # Skip if no feedback
        if interaction.success is None:
            return

        # Extract tool usage patterns
        if interaction.tools_used and interaction.success:
            for tool in interaction.tools_used:
                self._add_or_update_pattern(
                    pattern_type="tool_use",
                    input_pattern=self._extract_pattern(interaction.user_input),
                    output_template=tool,
                    success=interaction.success
                )

        # Extract response patterns
        if interaction.success:
            self._add_or_update_pattern(
                pattern_type="success",
                input_pattern=self._extract_pattern(interaction.user_input),
                output_template=self._extract_response_pattern(interaction.response),
                success=True
            )
        else:
            self._add_or_update_pattern(
                pattern_type="failure",
                input_pattern=self._extract_pattern(interaction.user_input),
                output_template=interaction.response[:100],
                success=False
            )

    def _extract_pattern(self, text: str) -> str:
        """Extract a pattern from text (simplified)."""
        # Lowercase and remove specifics
        pattern = text.lower()

        # Replace numbers with placeholder
        pattern = re.sub(r'\b\d+\b', '<NUM>', pattern)

        # Replace URLs with placeholder
        pattern = re.sub(r'https?://\S+', '<URL>', pattern)

        # Replace file paths with placeholder
        pattern = re.sub(r'/[\w/.-]+', '<PATH>', pattern)

        # Keep first 100 chars
        return pattern[:100]

    def _extract_response_pattern(self, response: str) -> str:
        """Extract a pattern from a successful response."""
        # Get the structure/outline
        lines = response.split('\n')

        # Remove specific content, keep structure
        structure = []
        for line in lines[:10]:  # First 10 lines
            if line.strip():
                if line.startswith('#'):
                    structure.append('# <HEADING>')
                elif line.startswith('-'):
                    structure.append('- <ITEM>')
                elif line.startswith('1.') or line.startswith('2.'):
                    structure.append('<NUM>. <ITEM>')
                elif ':' in line:
                    structure.append('<KEY>: <VALUE>')
                else:
                    structure.append('<TEXT>')

        return ' | '.join(structure[:5])  # Keep first 5 elements

    def _add_or_update_pattern(
        self,
        pattern_type: str,
        input_pattern: str,
        output_template: str,
        success: bool
    ):
        """Add or update a pattern."""
        # Find existing pattern
        for pattern in self._patterns:
            if (pattern.pattern_type == pattern_type and
                pattern.input_pattern == input_pattern):
                # Update existing
                pattern.usage_count += 1
                if success:
                    pattern.success_rate = (pattern.success_rate * 0.9) + 0.1
                else:
                    pattern.success_rate *= 0.95
                pattern.last_used = datetime.now().isoformat()
                return

        # Create new pattern
        pattern = Pattern(
            id=hashlib.md5(f"{pattern_type}{input_pattern}".encode()).hexdigest()[:8],
            pattern_type=pattern_type,
            input_pattern=input_pattern,
            output_template=output_template,
            success_rate=1.0 if success else 0.5,
            usage_count=1,
            last_used=datetime.now().isoformat()
        )

        self._patterns.append(pattern)

    def get_relevant_patterns(self, user_input: str, limit: int = 5) -> List[Pattern]:
        """Get patterns relevant to the current input."""
        input_lower = user_input.lower()

        # Score patterns by relevance
        scored = []
        for pattern in self._patterns:
            # Check if pattern matches
            if self._pattern_matches(input_lower, pattern.input_pattern):
                score = pattern.success_rate * pattern.usage_count
                scored.append((score, pattern))

        # Sort by score and return top
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for s, p in scored[:limit]]

    def _pattern_matches(self, text: str, pattern: str) -> bool:
        """Check if text matches a pattern."""
        # Simplified matching
        pattern_lower = pattern.lower()

        # Check for common keywords
        pattern_words = set(pattern_lower.split())
        text_words = set(text.split())

        overlap = len(pattern_words & text_words)
        return overlap >= min(3, len(pattern_words) // 2)

    def get_optimized_prompt(self, user_input: str) -> str:
        """Get an optimized prompt based on learned patterns."""
        relevant_patterns = self.get_relevant_patterns(user_input)

        if not relevant_patterns:
            return user_input

        # Build context from patterns
        context_parts = ["Based on successful patterns:"]

        for pattern in relevant_patterns[:3]:
            if pattern.pattern_type == "success":
                context_parts.append(f"- Similar input pattern: {pattern.input_pattern[:50]}...")
                context_parts.append(f"  Response structure: {pattern.output_template}")

        context_parts.append("")
        context_parts.append(f"Now answer: {user_input}")

        return "\n".join(context_parts)

    def generate_training_data(self) -> List[TrainingExample]:
        """Generate training examples from successful interactions."""
        examples = []

        for interaction in self._interactions:
            if interaction.success:
                # Determine quality score
                quality = 0.5
                if interaction.feedback and "great" in interaction.feedback.lower():
                    quality = 1.0
                elif interaction.feedback and "good" in interaction.feedback.lower():
                    quality = 0.8
                elif interaction.success:
                    quality = 0.7

                example = TrainingExample(
                    instruction="You are LUOKAI, a helpful AI assistant. Provide a helpful response.",
                    input=interaction.user_input,
                    output=interaction.response,
                    quality_score=quality,
                    source="self_improve"
                )

                examples.append(example)

        return examples

    def export_for_finetuning(self, output_file: str = None) -> str:
        """Export training data for fine-tuning."""
        examples = self.generate_training_data()

        output_path = Path(output_file or self.training_file)

        with open(output_path, "w") as f:
            for example in examples:
                data = {
                    "instruction": example.instruction,
                    "input": example.input,
                    "output": example.output,
                    "quality_score": example.quality_score
                }
                f.write(json.dumps(data) + "\n")

        return str(output_path)

    def analyze_performance(self) -> Dict:
        """Analyze overall performance metrics."""
        if not self._interactions:
            return {"status": "No interactions recorded"}

        total = len(self._interactions)
        successful = sum(1 for i in self._interactions if i.success)
        failed = sum(1 for i in self._interactions if i.success is False and i.success is not None)

        # Response time stats
        response_times = [i.response_time for i in self._interactions if i.response_time > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # Tool usage
        tool_counts = {}
        for interaction in self._interactions:
            for tool in interaction.tools_used:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

        # Pattern effectiveness
        successful_patterns = sum(1 for p in self._patterns if p.success_rate > 0.7)

        return {
            "total_interactions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "avg_response_time": avg_response_time,
            "most_used_tools": sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "learned_patterns": len(self._patterns),
            "effective_patterns": successful_patterns,
            "training_examples_available": len(self.generate_training_data())
        }

    def get_improvement_suggestions(self) -> List[str]:
        """Get suggestions for improvement based on analysis."""
        suggestions = []
        metrics = self.analyze_performance()

        # Check success rate
        if metrics["success_rate"] < 0.7:
            suggestions.append("Success rate is below 70%. Review failed interactions to identify common issues.")

        # Check response time
        if metrics["avg_response_time"] > 5:
            suggestions.append("Average response time is high. Consider optimizing prompts or caching.")

        # Check patterns
        if metrics["learned_patterns"] < 10:
            suggestions.append("Few patterns learned. Continue using the agent to build pattern knowledge.")

        if metrics["effective_patterns"] < metrics["learned_patterns"] * 0.5:
            suggestions.append("Many patterns have low success rates. Consider reviewing and pruning ineffective patterns.")

        # Check training data
        if metrics["training_examples_available"] > 100:
            suggestions.append("Sufficient training data available. Consider fine-tuning the model.")

        return suggestions

    def prune_patterns(self, min_success_rate: float = 0.3, min_usage: int = 2):
        """Remove ineffective patterns."""
        initial_count = len(self._patterns)

        self._patterns = [
            p for p in self._patterns
            if p.success_rate >= min_success_rate or p.usage_count >= min_usage
        ]

        pruned = initial_count - len(self._patterns)

        if pruned > 0:
            print(f"[SelfImprove] Pruned {pruned} ineffective patterns")
            self._save_data()

        return pruned


def create_self_improve_engine(
    data_dir: str = "~/.luo_os/self_improve"
) -> SelfImprovementEngine:
    """Create a self-improvement engine."""
    return SelfImprovementEngine(data_dir=data_dir)


if __name__ == "__main__":
    print("LUOKAI Self-Improvement Engine")
    print("=" * 50)

    engine = SelfImprovementEngine()

    # Simulate some interactions
    print("\nRecording interactions...")
    engine.record_interaction(
        user_input="What is the capital of France?",
        response="The capital of France is Paris.",
        success=True
    )

    engine.record_interaction(
        user_input="Read the file test.py",
        response="I'll read that file for you.",
        success=True,
        tools_used=["read_file"]
    )

    engine.record_interaction(
        user_input="Delete all files",
        response="I cannot delete all files without confirmation.",
        success=False,
        feedback="User wanted selective deletion"
    )

    # Analyze performance
    print("\nPerformance Analysis:")
    metrics = engine.analyze_performance()
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    # Get suggestions
    print("\nImprovement Suggestions:")
    for suggestion in engine.get_improvement_suggestions():
        print(f"  - {suggestion}")

    # Export training data
    print(f"\nTraining data exported to: {engine.export_for_finetuning()}")