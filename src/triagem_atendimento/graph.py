from __future__ import annotations

import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from langchain_core.language_models.chat_models import BaseChatModel
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

TOOLS = [
    consultar_status_pedido,
    verificar_politica_reembolso,
    escalar_para_humano,
]


def _route_model_output(state: TriagemState) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END


def build_graph(model: BaseChatModel | None = None):
    if model is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY não foi encontrada nas variáveis de ambiente.")
        model = ChatGoogleGenerativeAI(
            model="gemini-3.6-flash",
            api_key=api_key,
        )

    model_with_tools = model.bind_tools(TOOLS)

    def _call_model(state: TriagemState) -> dict[str, list[BaseMessage]]:
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

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