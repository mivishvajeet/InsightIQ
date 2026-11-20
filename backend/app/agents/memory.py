"""
Multi-Turn Conversational Memory & Context State Manager for InsightIQ.

Maintains sliding-window conversation history, tracked entities,
and prior SQL/RAG state to enable seamless context-dependent queries
(e.g., "Filter that down to São Paulo", "What about health and beauty?").
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ConversationTurn:
    """Represents a single turn in a multi-turn analytical conversation."""
    turn_id: int
    user_query: str
    rewritten_query: Optional[str] = None
    intent: str = "auto"
    tools_used: List[str] = field(default_factory=list)
    sql_query: Optional[str] = None
    final_answer: str = ""
    timestamp: float = field(default_factory=time.time)
    entities: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConversationalMemoryManager:
    """
    Manages session-scoped conversational history and contextual memory.
    Enables coreference resolution, entity continuity, and conversational query rewriting.
    """

    def __init__(self, session_id: str = "default_session", max_turns: int = 10):
        self.session_id = session_id
        self.max_turns = max_turns
        self.turns: List[ConversationTurn] = []

    def add_turn(
        self,
        user_query: str,
        final_answer: str,
        intent: str = "auto",
        tools_used: Optional[List[str]] = None,
        sql_query: Optional[str] = None,
        rewritten_query: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> ConversationTurn:
        """Appends a new completed interaction turn to the memory window."""
        turn_id = len(self.turns) + 1
        turn = ConversationTurn(
            turn_id=turn_id,
            user_query=user_query,
            rewritten_query=rewritten_query,
            intent=intent,
            tools_used=tools_used or [],
            sql_query=sql_query,
            final_answer=final_answer,
            entities=entities or {},
        )
        self.turns.append(turn)

        # Enforce sliding window capacity
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

        return turn

    def get_recent_turns(self, limit: int = 5) -> List[ConversationTurn]:
        """Returns the most recent N turns in chronological order."""
        return self.turns[-limit:] if self.turns else []

    def get_last_turn(self) -> Optional[ConversationTurn]:
        """Returns the immediately preceding conversation turn, if any."""
        return self.turns[-1] if self.turns else None

    def get_last_sql(self) -> Optional[str]:
        """Retrieves the most recent SQL query executed in the conversation."""
        for turn in reversed(self.turns):
            if turn.sql_query:
                return turn.sql_query
        return None

    def get_context_summary(self, max_turns: int = 3) -> str:
        """Produces a concise text summary of recent context for prompt augmentation."""
        recent = self.get_recent_turns(limit=max_turns)
        if not recent:
            return "No prior conversational context."

        lines = []
        for t in recent:
            lines.append(f"User: {t.user_query}")
            if t.sql_query:
                lines.append(f"Executed SQL: {t.sql_query}")
            # Snippet of assistant response
            ans_snippet = (t.final_answer[:120] + "...") if len(t.final_answer) > 120 else t.final_answer
            lines.append(f"Assistant: {ans_snippet}")

        return "\n".join(lines)

    def extract_contextual_entities(self) -> Dict[str, Any]:
        """Aggregates all persistent business entities mentioned across recent turns."""
        merged: Dict[str, Any] = {}
        for t in self.turns:
            merged.update(t.entities)
        return merged

    def clear(self) -> None:
        """Flushes the active conversation memory."""
        self.turns.clear()


# Global in-memory session registry for multi-session support
session_memory_registry: Dict[str, ConversationalMemoryManager] = {}


def get_session_memory(session_id: str = "default_session") -> ConversationalMemoryManager:
    """Retrieves or creates a session-scoped ConversationalMemoryManager."""
    if session_id not in session_memory_registry:
        session_memory_registry[session_id] = ConversationalMemoryManager(session_id=session_id)
    return session_memory_registry[session_id]
