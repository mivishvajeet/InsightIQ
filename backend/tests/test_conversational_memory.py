"""
Pytest Suite for Multi-Turn Conversational Memory & Context Resolution.

Tests:
1. ConversationalMemoryManager capacity, turns, summaries, and clearing.
2. AgentIntentClassifier coreference resolution and follow-up query rewriting.
3. OrchestratorAgent multi-turn execution and state persistence across turns.
"""

import pytest
from backend.app.agents.memory import ConversationalMemoryManager, ConversationTurn, get_session_memory
from backend.app.agents.intent_classifier import AgentIntentClassifier
from backend.app.agents.orchestrator import OrchestratorAgent


def test_conversational_memory_turn_addition_and_limit():
    """Verifies that conversation turns are recorded and sliding window limits enforced."""
    mem = ConversationalMemoryManager(session_id="test_session", max_turns=3)
    assert len(mem.turns) == 0

    mem.add_turn(user_query="Q1", final_answer="A1", sql_query="SELECT 1;")
    mem.add_turn(user_query="Q2", final_answer="A2", sql_query="SELECT 2;")
    assert len(mem.turns) == 2
    assert mem.get_last_sql() == "SELECT 2;"

    mem.add_turn(user_query="Q3", final_answer="A3", sql_query="SELECT 3;")
    mem.add_turn(user_query="Q4", final_answer="A4", sql_query="SELECT 4;")
    # Max turns is 3, so Q1 should be evicted
    assert len(mem.turns) == 3
    assert mem.turns[0].user_query == "Q2"
    assert mem.turns[-1].user_query == "Q4"
    assert mem.get_last_sql() == "SELECT 4;"


def test_conversational_memory_summary_and_clear():
    """Tests context summarization and memory flush."""
    mem = ConversationalMemoryManager(session_id="test_summary")
    mem.add_turn(user_query="What is total revenue?", final_answer="R$ 15,424,463.65", sql_query="SELECT sum(total);")

    summary = mem.get_context_summary(max_turns=2)
    assert "What is total revenue?" in summary
    assert "SELECT sum(total);" in summary

    mem.clear()
    assert len(mem.turns) == 0
    assert mem.get_last_turn() is None
    assert "No prior conversational context" in mem.get_context_summary()


def test_intent_classifier_follow_up_resolution():
    """Tests resolution of coreferences and follow-up questions."""
    classifier = AgentIntentClassifier()
    mem = ConversationalMemoryManager(session_id="test_rewriting")

    # Turn 1
    mem.add_turn(
        user_query="Which product categories generate the highest sales?",
        final_answer="Bed bath table generated the highest revenue.",
        sql_query="SELECT category, sum(revenue) FROM analytics.v_category_performance;",
        intent="sql",
    )

    # Turn 2: Follow-up with filter
    resolved_q, note = classifier.resolve_conversational_query("Filter that down to São Paulo", memory=mem)
    assert "são paulo" in resolved_q.lower()
    assert "Which product categories generate the highest sales" in resolved_q
    assert note is not None

    # Classification inherits/resolves effectively
    classification = classifier.classify("Filter that down to São Paulo", memory=mem)
    assert classification.rewritten_query is not None
    assert "sql_analytics_tool" in classification.tools_required

    # Turn 3: Follow-up with 'what about'
    resolved_q2, _ = classifier.resolve_conversational_query("What about health and beauty?", memory=mem)
    assert "health and beauty" in resolved_q2.lower()

    # Turn 4: Follow-up with 'break that down by'
    resolved_q3, _ = classifier.resolve_conversational_query("Break that down by state", memory=mem)
    assert "state" in resolved_q3.lower()


def test_session_registry_isolation():
    """Verifies that different sessions maintain isolated conversational states."""
    s1 = get_session_memory("session_alpha")
    s2 = get_session_memory("session_beta")

    s1.clear()
    s2.clear()

    s1.add_turn("Query Alpha", "Answer Alpha")
    s2.add_turn("Query Beta", "Answer Beta")

    assert len(s1.turns) == 1
    assert s1.turns[0].user_query == "Query Alpha"

    assert len(s2.turns) == 1
    assert s2.turns[0].user_query == "Query Beta"
