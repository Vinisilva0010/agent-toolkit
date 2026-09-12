"""State definition for the customer support triage agent graph."""

from __future__ import annotations

from typing import Annotated, Literal

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class TriagemState(TypedDict):
    """Shared state that flows through every node of the graph.

    Attributes:
        messages: Full conversation history. The `add_messages` reducer
            appends new messages instead of overwriting the list.
        status: Current stage of the triage flow, used for routing and
            for observability (what LangSmith shows per run).
        pending_escalation: Set to True when the agent decides a human
            needs to take over. The graph interrupts before actually
            escalating, so a human can approve or reject it.
        escalation_reason: Free-text reason recorded when the agent
            requests escalation, so the human reviewer has context.
    """

    messages: Annotated[list, add_messages]
    status: Literal["in_progress", "awaiting_human", "resolved", "escalated"]
    pending_escalation: bool
    escalation_reason: str | None
