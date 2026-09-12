from __future__ import annotations

import os
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from triagem_atendimento.state import TriagemState
from triagem_atendimento.tools.atendimento import (
    consultar_status_pedido,
    escalar_para_humano,
    verificar_politica_reembolso,
)

load_dotenv()

TOOLS = [
    consultar_status_pedido,
    verificar_politica_reembolso,
    escalar_para_humano,
]


def _call_model(state: TriagemState) -> dict[str, list[BaseMessage]]:
    api_key = os.getenv("GOOGLE_API_KEY")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=api_key,
    ).bind_tools(TOOLS)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def _route_model_output(state: TriagemState) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END


def build_graph():
    workflow = StateGraph(TriagemState)

    workflow.add_node("agent", _call_model)
    workflow.add_node("tools", ToolNode(TOOLS))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        _route_model_output,
        {
            "tools": "tools",
            END: END,
        },
    )
    workflow.add_edge("tools", "agent")

    checkpointer = InMemorySaver()
    return workflow.compile(checkpointer=checkpointer)