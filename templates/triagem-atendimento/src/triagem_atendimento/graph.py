from __future__ import annotations

import os
import re

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from triagem_atendimento.state import TriagemState

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8787/mcp")


async def load_mcp_tools() -> list[BaseTool]:
    """Busca as tools de atendimento no servidor MCP (Fase 2)."""
    client = MultiServerMCPClient(
        {
            "triagem_atendimento": {
                "url": MCP_SERVER_URL,
                "transport": "http",
            }
        }
    )
    return await client.get_tools()


def _route_model_output(state: TriagemState) -> str:
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END


def _route_after_tools(state: TriagemState) -> str:
    """MCP é síncrono: escalar_para_humano só registra o ticket, não pausa
    sozinha. É aqui, no grafo, que decidimos pausar de verdade."""
    last_message = state["messages"][-1]
    if isinstance(last_message, ToolMessage) and last_message.name == "escalar_para_humano":
        return "aguardar_aprovacao_humana"
    return "agent"


async def build_graph(
    model: BaseChatModel | None = None,
    tools: list[BaseTool] | None = None,
):
    if model is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY não foi encontrada nas variáveis de ambiente."
            )
        model = ChatGoogleGenerativeAI(model="gemini-3.6-flash", api_key=api_key)

    if tools is None:
        tools = await load_mcp_tools()

    model_with_tools = model.bind_tools(tools)

    def _call_model(state: TriagemState) -> dict[str, list[BaseMessage]]:
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def _aguardar_aprovacao_humana(state: TriagemState) -> dict[str, list[BaseMessage]]:
        last_message = state["messages"][-1]
        ticket_match = re.search(r"ticket_id:\s*([\w-]+)", str(last_message.content))
        ticket_id = ticket_match.group(1) if ticket_match else None

        decisao = interrupt(
            {
                "acao": "aprovar_escalacao",
                "ticket_id": ticket_id,
                "detalhes": last_message.content,
            }
        )
        if not isinstance(decisao, dict):
            raise TypeError("A decisão humana deve ser um dicionário.")

        aprovado = decisao.get("aprovado", False)
        observacao = decisao.get("observacao")
        texto = (
            "Escalação aprovada pelo operador."
            if aprovado
            else "Escalação recusada pelo operador; continue tentando resolver diretamente."
        )
        if observacao:
            texto += f" Observação do operador: {observacao}."
        return {"messages": [HumanMessage(content=texto)]}

    workflow = StateGraph(TriagemState)
    workflow.add_node("agent", _call_model)
    workflow.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    workflow.add_node("aguardar_aprovacao_humana", _aguardar_aprovacao_humana)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent", _route_model_output, {"tools": "tools", END: END}
    )
    workflow.add_conditional_edges(
        "tools",
        _route_after_tools,
        {"aguardar_aprovacao_humana": "aguardar_aprovacao_humana", "agent": "agent"},
    )
    workflow.add_edge("aguardar_aprovacao_humana", "agent")

    checkpointer = InMemorySaver()
    return workflow.compile(checkpointer=checkpointer)
