"""Promptfoo custom provider that exercises the real triagem-atendimento
LangGraph agent (Gemini + local tools) for adversarial red-teaming."""

import asyncio
import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from triagem_atendimento.graph import build_graph
from triagem_atendimento.tools.atendimento import (
    consultar_status_pedido,
    escalar_para_humano,
    verificar_politica_reembolso,
)

TOOLS = [consultar_status_pedido, verificar_politica_reembolso, escalar_para_humano]


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def _find_escalation_reason(messages) -> str | None:
    for message in messages:
        if isinstance(message, AIMessage):
            for call in getattr(message, "tool_calls", None) or []:
                if call.get("name") == "escalar_para_humano":
                    return call.get("args", {}).get("motivo")
    return None


async def _run(prompt: str) -> str:
    graph = await build_graph(tools=TOOLS)
    config = {"configurable": {"thread_id": f"redteam-{uuid.uuid4()}"}}

    result = await graph.ainvoke({"messages": [HumanMessage(content=prompt)]}, config)

    escalation_triggered = "__interrupt__" in result
    if escalation_triggered:
        # Auto-resolve as a rejection so red-team runs don't need a human,
        # and so we can still evaluate the final agent response.
        result = await graph.ainvoke(
            Command(resume={"aprovado": False, "observacao": "red-team auto-decline"}),
            config,
        )

    escalation_reason = _find_escalation_reason(result["messages"])
    final_text = _extract_text(result["messages"][-1].content)

    return (
        f"ESCALATION_TRIGGERED: {escalation_triggered}\n"
        f"ESCALATION_REASON: {escalation_reason}\n"
        f"RESPONSE: {final_text}"
    )


def call_api(prompt, options, context):
    output = asyncio.run(_run(prompt))
    return {"output": output}
