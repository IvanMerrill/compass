"""Tests for Orient phase - hypothesis ranking and synthesis."""

from datetime import datetime, timezone

import pytest

from compass.core.investigation import Investigation, InvestigationContext
from compass.core.phases.orient import (
    HypothesisRanker,
    RankedHypothesis,
    RankingResult,
)
from compass.core.scientific_framework import Hypothesis


class TestHypothesisRanker:
    """Tests for ranking and deduplicating hypotheses."""

    def test_ranks_hypotheses_by_confidence(self):
        """Verify hypotheses are ranked by confidence (highest first)."""
        hyp1 = Hypothesis(
            agent_id="agent1",
            statement="Connection pool exhausted",
            initial_confidence=0.9,
        )
        hyp2 = Hypothesis(
            agent_id="agent2",
            statement="Slow database queries",
            initial_confidence=0.7,
        )
        hyp3 = Hypothesis(
            agent_id="agent3",
            statement="Network latency spike",
            initial_confidence=0.8,
        )

        ranker = HypothesisRanker()
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([hyp1, hyp2, hyp3], investigation)

        # Should be ranked: 0.9, 0.8, 0.7
        assert result.ranked_hypotheses[0].hypothesis.initial_confidence == 0.9
        assert result.ranked_hypotheses[1].hypothesis.initial_confidence == 0.8
        assert result.ranked_hypotheses[2].hypothesis.initial_confidence == 0.7

    def test_limits_to_top_n_hypotheses(self):
        """Verify only top N hypotheses are returned."""
        hypotheses = [
            Hypothesis(
                agent_id=f"agent{i}",
                statement=f"Hypothesis {i}",
                initial_confidence=0.9 - (i * 0.1),
            )
            for i in range(10)
        ]

        ranker = HypothesisRanker(top_n=5)
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank(hypotheses, investigation)

        # Should return only top 5
        assert len(result.ranked_hypotheses) == 5
        assert result.ranked_hypotheses[0].hypothesis.initial_confidence == 0.9
        assert result.ranked_hypotheses[4].hypothesis.initial_confidence == 0.5

    def test_deduplicates_similar_hypotheses(self):
        """Verify similar hypotheses are deduplicated."""
        hyp1 = Hypothesis(
            agent_id="agent1",
            statement="Database connection pool is exhausted",
            initial_confidence=0.9,
        )
        hyp2 = Hypothesis(
            agent_id="agent2",
            statement="Connection pool exhausted",  # Very similar
            initial_confidence=0.8,
        )
        hyp3 = Hypothesis(
            agent_id="agent3",
            statement="Network timeout errors",  # Different
            initial_confidence=0.7,
        )

        ranker = HypothesisRanker(similarity_threshold=0.7)
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([hyp1, hyp2, hyp3], investigation)

        # Should have 2 hypotheses (hyp1 and hyp3, hyp2 deduplicated)
        assert len(result.ranked_hypotheses) == 2
        statements = [rh.hypothesis.statement for rh in result.ranked_hypotheses]
        assert "Database connection pool is exhausted" in statements
        assert "Network timeout errors" in statements
        assert "Connection pool exhausted" not in statements

    def test_tracks_deduplicated_hypotheses(self):
        """Verify deduplicated hypotheses are tracked."""
        hyp1 = Hypothesis(
            agent_id="agent1",
            statement="Connection pool exhausted",
            initial_confidence=0.9,
        )
        hyp2 = Hypothesis(
            agent_id="agent2",
            statement="Pool exhausted",  # Similar
            initial_confidence=0.7,
        )

        ranker = HypothesisRanker(similarity_threshold=0.7)
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([hyp1, hyp2], investigation)

        # Should track that hyp2 was deduplicated
        assert result.deduplicated_count == 1
        assert len(result.ranked_hypotheses) == 1

    def test_identifies_conflicting_hypotheses(self):
        """Verify conflicting hypotheses are identified."""
        hyp1 = Hypothesis(
            agent_id="agent1",
            statement="Database is overloaded",
            initial_confidence=0.8,
            metadata={"conflicts_with": ["Network issue"]},
        )
        hyp2 = Hypothesis(
            agent_id="agent2",
            statement="Network latency spike",
            initial_confidence=0.7,
        )

        ranker = HypothesisRanker()
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([hyp1, hyp2], investigation)

        # Should identify conflict
        assert len(result.conflicts) > 0

    def test_assigns_rank_numbers(self):
        """Verify each hypothesis gets a rank number."""
        hypotheses = [
            Hypothesis(
                agent_id=f"agent{i}",
                statement=f"Hypothesis {i}",
                initial_confidence=0.9 - (i * 0.1),
            )
            for i in range(3)
        ]

        ranker = HypothesisRanker()
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank(hypotheses, investigation)

        # Verify rank numbers
        assert result.ranked_hypotheses[0].rank == 1
        assert result.ranked_hypotheses[1].rank == 2
        assert result.ranked_hypotheses[2].rank == 3

    def test_handles_empty_hypothesis_list(self):
        """Verify ranking handles empty input gracefully."""
        ranker = HypothesisRanker()
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([], investigation)

        assert len(result.ranked_hypotheses) == 0
        assert result.deduplicated_count == 0

    def test_handles_single_hypothesis(self):
        """Verify ranking handles single hypothesis."""
        hyp = Hypothesis(
            agent_id="agent1",
            statement="Database issue",
            initial_confidence=0.8,
        )

        ranker = HypothesisRanker()
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([hyp], investigation)

        assert len(result.ranked_hypotheses) == 1
        assert result.ranked_hypotheses[0].rank == 1
        assert result.ranked_hypotheses[0].hypothesis.statement == "Database issue"

    def test_adds_ranking_reasoning(self):
        """Verify each ranked hypothesis includes reasoning."""
        hyp = Hypothesis(
            agent_id="agent1",
            statement="Connection pool exhausted",
            initial_confidence=0.9,
        )

        ranker = HypothesisRanker()
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([hyp], investigation)

        # Should have reasoning for why it was ranked #1
        assert result.ranked_hypotheses[0].reasoning is not None
        assert len(result.ranked_hypotheses[0].reasoning) > 0


class TestSimilarityDetection:
    """Tests for hypothesis similarity detection."""

    def test_detects_exact_duplicates(self):
        """Verify exact duplicate statements are detected."""
        hyp1 = Hypothesis(
            agent_id="agent1",
            statement="Connection pool exhausted",
            initial_confidence=0.9,
        )
        hyp2 = Hypothesis(
            agent_id="agent2",
            statement="Connection pool exhausted",  # Exact match
            initial_confidence=0.7,
        )

        ranker = HypothesisRanker(similarity_threshold=0.9)
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([hyp1, hyp2], investigation)

        # Should deduplicate exact match
        assert len(result.ranked_hypotheses) == 1

    def test_detects_similar_with_different_wording(self):
        """Verify similar hypotheses with different wording are detected."""
        hyp1 = Hypothesis(
            agent_id="agent1",
            statement="The database connection pool has been exhausted",
            initial_confidence=0.9,
        )
        hyp2 = Hypothesis(
            agent_id="agent2",
            statement="DB pool is exhausted",
            initial_confidence=0.7,
        )

        ranker = HypothesisRanker(similarity_threshold=0.6)
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([hyp1, hyp2], investigation)

        # Should detect similarity and deduplicate
        assert len(result.ranked_hypotheses) == 1

    def test_keeps_distinct_hypotheses(self):
        """Verify distinct hypotheses are not deduplicated."""
        hyp1 = Hypothesis(
            agent_id="agent1",
            statement="Database connection pool exhausted",
            initial_confidence=0.9,
        )
        hyp2 = Hypothesis(
            agent_id="agent2",
            statement="Network latency increased",
            initial_confidence=0.7,
        )

        ranker = HypothesisRanker(similarity_threshold=0.7)
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        result = ranker.rank([hyp1, hyp2], investigation)

        # Should keep both (not similar)
        assert len(result.ranked_hypotheses) == 2


class TestRankingResult:
    """Tests for RankingResult dataclass."""

    def test_creates_ranking_result(self):
        """Verify RankingResult can be created."""
        hyp = Hypothesis(
            agent_id="agent1",
            statement="Test",
            initial_confidence=0.8,
        )
        ranked = RankedHypothesis(
            rank=1,
            hypothesis=hyp,
            reasoning="Highest confidence",
        )

        result = RankingResult(
            ranked_hypotheses=[ranked],
            deduplicated_count=2,
            conflicts=[],
        )

        assert len(result.ranked_hypotheses) == 1
        assert result.deduplicated_count == 2
        assert len(result.conflicts) == 0


class TestRankedHypothesis:
    """Tests for RankedHypothesis dataclass."""

    def test_creates_ranked_hypothesis(self):
        """Verify RankedHypothesis stores rank and reasoning."""
        hyp = Hypothesis(
            agent_id="agent1",
            statement="Connection pool exhausted",
            initial_confidence=0.9,
        )

        ranked = RankedHypothesis(
            rank=1,
            hypothesis=hyp,
            reasoning="Highest confidence and matches symptoms",
        )

        assert ranked.rank == 1
        assert ranked.hypothesis.statement == "Connection pool exhausted"
        assert "Highest confidence" in ranked.reasoning
