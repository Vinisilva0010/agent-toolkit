from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from triagem_atendimento.graph import build_graph


class FakeToolCallingModel(GenericFakeChatModel):
    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Any | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ):
        return self


def test_fluxo_feliz_consulta_pedido():
    tool_call = {
        "name": "consultar_status_pedido",
        "args": {"pedido_id": "PED-123"},
        "id": "call_happy_path",
        "type": "tool_call",
    }
    msg_tool = AIMessage(content="", tool_calls=[tool_call])
    msg_final = AIMessage(content="O status do pedido PED-123 é enviado.")

    fake_model = FakeToolCallingModel(messages=iter([msg_tool, msg_final]))
    graph = build_graph(model=fake_model)
    config = {"configurable": {"thread_id": "it-happy-path"}}

    resultado = graph.invoke(
        {"messages": [HumanMessage(content="Qual o status do pedido PED-123?")]},
        config=config,
    )

    mensagens = resultado["messages"]
    assert len(mensagens) == 4
    assert isinstance(mensagens[2], ToolMessage)
    assert "BR123456789" in mensagens[2].content
    assert mensagens[3].content == "O status do pedido PED-123 é enviado."


def test_ferramenta_erro_recuperavel():
    # Ao falhar com ValueError na tool, o ToolNode devolve mensagem de erro sem abortar o grafo
    tool_call = {
        "name": "consultar_status_pedido",
        "args": {"pedido_id": "PED-INEXISTENTE"},
        "id": "call_err_path",
        "type": "tool_call",
    }
    msg_tool = AIMessage(content="", tool_calls=[tool_call])
    msg_final = AIMessage(
        content="Não localizei o pedido informado. Por favor, verifique o código."
    )

    fake_model = FakeToolCallingModel(messages=iter([msg_tool, msg_final]))
    graph = build_graph(model=fake_model)
    config = {"configurable": {"thread_id": "it-tool-error"}}

    resultado = graph.invoke(
        {"messages": [HumanMessage(content="Status do pedido PED-INEXISTENTE?")]},
        config=config,
    )

    mensagens = resultado["messages"]
    assert len(mensagens) == 4
    assert isinstance(mensagens[2], ToolMessage)
    assert (
        "ValueError" in mensagens[2].content or "não encontrado" in mensagens[2].content
    )
    assert (
        mensagens[3].content
        == "Não localizei o pedido informado. Por favor, verifique o código."
    )


def test_resposta_ambigua_modelo():
    # Modelo retorna mensagem vazia e sem chamadas de ferramenta
    fake_model = FakeToolCallingModel(messages=iter([AIMessage(content="")]))
    graph = build_graph(model=fake_model)
    config = {"configurable": {"thread_id": "it-ambiguous-response"}}

    resultado = graph.invoke(
        {"messages": [HumanMessage(content="Oi")]},
        config=config,
    )

    mensagens = resultado["messages"]
    assert len(mensagens) == 2
    assert mensagens[-1].content == ""


def test_escalacao_aprovada():
    tool_call = {
        "name": "escalar_para_humano",
        "args": {"motivo": "Cliente agressivo"},
        "id": "call_escalate_approved",
        "type": "tool_call",
    }
    msg_tool = AIMessage(content="", tool_calls=[tool_call])
    msg_final = AIMessage(content="Transferência para atendente humano realizada.")

    fake_model = FakeToolCallingModel(messages=iter([msg_tool, msg_final]))
    graph = build_graph(model=fake_model)
    config = {"configurable": {"thread_id": "it-escalate-approved"}}

    # Inicia execução até pausar no interrupt()
    resultado_pausa = graph.invoke(
        {"messages": [HumanMessage(content="Quero falar com um humano agora!")]},
        config=config,
    )

    assert "__interrupt__" in resultado_pausa
    interrupt_info = resultado_pausa["__interrupt__"][0].value
    assert interrupt_info["acao"] == "escalar_para_humano"
    assert interrupt_info["motivo"] == "Cliente agressivo"

    # Retoma com aprovação humana
    resultado_final = graph.invoke(
        Command(resume={"aprovado": True, "observacao": "Operador assumindo"}),
        config=config,
    )

    mensagens = resultado_final["messages"]
    tool_msg = next(m for m in mensagens if isinstance(m, ToolMessage))
    assert "Escalação aprovada pelo operador" in tool_msg.content
    assert "Operador assumindo" in tool_msg.content
    assert mensagens[-1].content == "Transferência para atendente humano realizada."


def test_escalacao_recusada():
    tool_call = {
        "name": "escalar_para_humano",
        "args": {"motivo": "Dúvida simples de política"},
        "id": "call_escalate_rejected",
        "type": "tool_call",
    }
    msg_tool = AIMessage(content="", tool_calls=[tool_call])
    msg_final = AIMessage(content="Entendido, vou continuar tentando tirar sua dúvida.")

    fake_model = FakeToolCallingModel(messages=iter([msg_tool, msg_final]))
    graph = build_graph(model=fake_model)
    config = {"configurable": {"thread_id": "it-escalate-rejected"}}

    # Pausa no interrupt
    resultado_pausa = graph.invoke(
        {"messages": [HumanMessage(content="Me passa alguém")]},
        config=config,
    )
    assert "__interrupt__" in resultado_pausa

    # Retoma com recusa humana
    resultado_final = graph.invoke(
        Command(
            resume={
                "aprovado": False,
                "observacao": "Tente responder sobre reembolso primeiro",
            }
        ),
        config=config,
    )

    mensagens = resultado_final["messages"]
    tool_msg = next(m for m in mensagens if isinstance(m, ToolMessage))
    assert "Escalação recusada pelo operador" in tool_msg.content
    assert "Tente responder sobre reembolso primeiro" in tool_msg.content
    assert resultado_final.get("status") != "escalated"
    assert (
        mensagens[-1].content == "Entendido, vou continuar tentando tirar sua dúvida."
    )


def test_timeout_recursion_limit():
    # Modelo insiste em chamar a mesma tool indefinidamente simulando loop
    def gerar_loop_infinito():
        while True:
            yield AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "verificar_politica_reembolso",
                        "args": {"categoria_produto": "eletronicos"},
                        "id": "call_infinite_loop",
                        "type": "tool_call",
                    }
                ],
            )

    fake_model = FakeToolCallingModel(messages=gerar_loop_infinito())
    graph = build_graph(model=fake_model)
    config = {"configurable": {"thread_id": "it-timeout-loop"}, "recursion_limit": 4}

    with pytest.raises(GraphRecursionError):
        graph.invoke(
            {"messages": [HumanMessage(content="Loop infinito")]},
            config=config,
        )
