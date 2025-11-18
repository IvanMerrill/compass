"""Orient phase - hypothesis ranking and synthesis for COMPASS.

This module ranks and deduplicates hypotheses from multiple specialist agents,
identifying the most promising hypotheses to investigate.

Design:
- Rank by confidence score (simple, no complex scoring)
- Deduplicate similar hypotheses using keyword similarity
- Identify conflicts between mutually exclusive hypotheses
- Return top N hypotheses with reasoning
- No LLM synthesis (YAGNI - defer to Phase 4+)
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

import structlog

from compass.core.investigation import Investigation
from compass.core.scientific_framework import Hypothesis

logger = structlog.get_logger(__name__)


@dataclass
class RankedHypothesis:
    """Hypothesis with rank and reasoning.

    Attributes:
        rank: Rank number (1 = highest confidence)
        hypothesis: The hypothesis object
        reasoning: Why this hypothesis was ranked here
    """

    rank: int
    hypothesis: Hypothesis
    reasoning: str


@dataclass
class RankingResult:
    """Result of hypothesis ranking.

    Attributes:
        ranked_hypotheses: List of ranked hypotheses (sorted by rank)
        deduplicated_count: Number of hypotheses deduplicated
        conflicts: List of conflict descriptions between hypotheses
    """

    ranked_hypotheses: List[RankedHypothesis]
    deduplicated_count: int
    conflicts: List[str]


class HypothesisRanker:
    """Ranks and deduplicates hypotheses from multiple agents.

    Uses simple confidence-based ranking with keyword similarity for
    deduplication. No complex NLP or LLM synthesis (YAGNI).

    Example:
        >>> ranker = HypothesisRanker(top_n=5, similarity_threshold=0.7)
        >>> result = ranker.rank(hypotheses, investigation)
        >>> print(f"Top hypothesis: {result.ranked_hypotheses[0].hypothesis.statement}")
    """

    def __init__(
        self,
        top_n: int = 5,
        similarity_threshold: float = 0.7,
    ):
        """Initialize HypothesisRanker.

        Args:
            top_n: Maximum number of hypotheses to return (default: 5)
            similarity_threshold: Threshold for similarity detection 0.0-1.0 (default: 0.7)
        """
        self.top_n = top_n
        self.similarity_threshold = similarity_threshold

    def rank(
        self,
        hypotheses: List[Hypothesis],
        investigation: Investigation,
    ) -> RankingResult:
        """Rank hypotheses by confidence and deduplicate similar ones.

        Args:
            hypotheses: List of hypotheses from agents
            investigation: Investigation context

        Returns:
            RankingResult with ranked hypotheses, deduplication stats, conflicts
        """
        logger.info(
            "orient.ranking.started",
            investigation_id=investigation.id,
            hypothesis_count=len(hypotheses),
            top_n=self.top_n,
        )

        if not hypotheses:
            return RankingResult(
                ranked_hypotheses=[],
                deduplicated_count=0,
                conflicts=[],
            )

        # Step 1: Sort by confidence (highest first)
        sorted_hypotheses = sorted(
            hypotheses,
            key=lambda h: h.initial_confidence,
            reverse=True,
        )

        # Step 2: Deduplicate similar hypotheses
        unique_hypotheses, deduplicated_count = self._deduplicate(sorted_hypotheses)

        # Step 3: Identify conflicts
        conflicts = self._identify_conflicts(unique_hypotheses)

        # Step 4: Limit to top N
        top_hypotheses = unique_hypotheses[: self.top_n]

        # Step 5: Create ranked hypotheses with reasoning
        ranked_hypotheses = []
        for rank, hypothesis in enumerate(top_hypotheses, start=1):
            reasoning = self._generate_reasoning(rank, hypothesis, len(hypotheses))
            ranked_hypotheses.append(
                RankedHypothesis(
                    rank=rank,
                    hypothesis=hypothesis,
                    reasoning=reasoning,
                )
            )

        logger.info(
            "orient.ranking.completed",
            investigation_id=investigation.id,
            ranked_count=len(ranked_hypotheses),
            deduplicated_count=deduplicated_count,
            conflict_count=len(conflicts),
        )

        return RankingResult(
            ranked_hypotheses=ranked_hypotheses,
            deduplicated_count=deduplicated_count,
            conflicts=conflicts,
        )

    def _deduplicate(
        self,
        hypotheses: List[Hypothesis],
    ) -> Tuple[List[Hypothesis], int]:
        """Deduplicate similar hypotheses using keyword similarity.

        Args:
            hypotheses: List of hypotheses (already sorted by confidence)

        Returns:
            Tuple of (unique_hypotheses, deduplicated_count)
        """
        unique: List[Hypothesis] = []
        deduplicated = 0

        for hypothesis in hypotheses:
            # Check if similar to any existing unique hypothesis
            is_duplicate = False
            for existing in unique:
                if self._is_similar(hypothesis.statement, existing.statement):
                    is_duplicate = True
                    deduplicated += 1
                    logger.debug(
                        "orient.hypothesis.deduplicated",
                        kept=existing.statement,
                        removed=hypothesis.statement,
                    )
                    break

            if not is_duplicate:
                unique.append(hypothesis)

        return unique, deduplicated

    def _is_similar(self, statement1: str, statement2: str) -> bool:
        """Check if two hypothesis statements are similar.

        Uses simple keyword-based similarity (no embeddings or LLM).

        Args:
            statement1: First hypothesis statement
            statement2: Second hypothesis statement

        Returns:
            True if statements are similar above threshold
        """
        # Normalize: lowercase, split into words
        words1 = self._normalize_statement(statement1)
        words2 = self._normalize_statement(statement2)

        if not words1 or not words2:
            return False

        # Check for subset relationship (one is completely contained in the other)
        # This handles cases like "Pool exhausted" vs "Connection pool exhausted"
        if words1.issubset(words2) or words2.issubset(words1):
            return True

        # Calculate Jaccard similarity: intersection / union
        intersection = words1.intersection(words2)
        union = words1.union(words2)

        similarity = len(intersection) / len(union)

        return similarity >= self.similarity_threshold

    def _normalize_statement(self, statement: str) -> Set[str]:
        """Normalize statement by removing stopwords and handling abbreviations.

        Args:
            statement: Hypothesis statement

        Returns:
            Set of normalized keywords
        """
        # Common stopwords to remove
        stopwords = {
            "the",
            "is",
            "are",
            "was",
            "were",
            "been",
            "being",
            "have",
            "has",
            "had",
            "a",
            "an",
        }

        # Common abbreviations
        abbreviations = {
            "db": "database",
            "conn": "connection",
        }

        # Lowercase and split
        words = statement.lower().split()

        # Expand abbreviations and remove stopwords
        normalized = set()
        for word in words:
            # Expand abbreviation if exists
            expanded = abbreviations.get(word, word)
            # Skip stopwords
            if expanded not in stopwords:
                normalized.add(expanded)

        return normalized

    def _identify_conflicts(self, hypotheses: List[Hypothesis]) -> List[str]:
        """Identify conflicting hypotheses.

        Args:
            hypotheses: List of hypotheses

        Returns:
            List of conflict descriptions
        """
        conflicts: List[str] = []

        # Check for explicit conflicts in metadata
        for i, hyp1 in enumerate(hypotheses):
            conflicts_with = hyp1.metadata.get("conflicts_with", [])
            if not conflicts_with:
                continue

            for hyp2 in hypotheses[i + 1 :]:
                # Check if hyp2 statement matches any conflict pattern
                for conflict_pattern in conflicts_with:
                    # Use keyword overlap for conflict detection
                    # Normalize both pattern and statement
                    pattern_words = self._normalize_statement(conflict_pattern)
                    statement_words = self._normalize_statement(hyp2.statement)

                    # If any keywords from pattern appear in statement, flag as conflict
                    if pattern_words and statement_words:
                        overlap = pattern_words.intersection(statement_words)
                        if len(overlap) > 0:
                            conflict_msg = (
                                f"Conflict: '{hyp1.statement}' vs '{hyp2.statement}' "
                                f"(confidence: {hyp1.initial_confidence:.2f} vs {hyp2.initial_confidence:.2f})"
                            )
                            conflicts.append(conflict_msg)
                            logger.warning(
                                "orient.conflict.detected",
                                hypothesis1=hyp1.statement,
                                hypothesis2=hyp2.statement,
                            )
                            break  # Only add one conflict per hypothesis pair

        return conflicts

    def _generate_reasoning(
        self,
        rank: int,
        hypothesis: Hypothesis,
        total_hypotheses: int,
    ) -> str:
        """Generate reasoning for why hypothesis has this rank.

        Args:
            rank: Rank number (1-based)
            hypothesis: The hypothesis
            total_hypotheses: Total number of hypotheses before ranking

        Returns:
            Reasoning string
        """
        confidence_pct = hypothesis.initial_confidence * 100

        if rank == 1:
            return (
                f"Ranked #1: Highest confidence ({confidence_pct:.0f}%) "
                f"among {total_hypotheses} hypotheses from agent '{hypothesis.agent_id}'"
            )
        else:
            return (
                f"Ranked #{rank}: Confidence {confidence_pct:.0f}% "
                f"from agent '{hypothesis.agent_id}'"
            )
