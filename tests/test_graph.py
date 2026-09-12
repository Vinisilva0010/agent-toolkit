from __future__ import annotations

from typing import Any, Sequence
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool

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


def test_roteamento_direto_para_end_sem_tool_calls():
    fake_model = FakeToolCallingModel(
        messages=iter([AIMessage(content="Atendimento concluído com sucesso.")])
    )
    graph = build_graph(model=fake_model)
    config = {"configurable": {"thread_id": "test-route-end"}}

    resultado = graph.invoke(
        {"messages": [HumanMessage(content="Olá, obrigado.")]},
        config=config,
    )

    mensagens = resultado["messages"]
    assert len(mensagens) == 2
    assert isinstance(mensagens[-1], AIMessage)
    assert mensagens[-1].content == "Atendimento concluído com sucesso."
    assert not getattr(mensagens[-1], "tool_calls", None)


def test_roteamento_para_tools_e_retorno_ao_agente():
    chamada_tool = {
        "name": "consultar_status_pedido",
        "args": {"pedido_id": "PED-123"},
        "id": "call_mock_123",
        "type": "tool_call",
    }
    msg_com_tool = AIMessage(content="", tool_calls=[chamada_tool])
    msg_final = AIMessage(content="Seu pedido foi enviado com sucesso.")

    fake_model = FakeToolCallingModel(messages=iter([msg_com_tool, msg_final]))
    graph = build_graph(model=fake_model)
    config = {"configurable": {"thread_id": "test-route-tools"}}

    resultado = graph.invoke(
        {"messages": [HumanMessage(content="Qual o status do meu pedido PED-123?")]},
        config=config,
    )

    mensagens = resultado["messages"]
    assert len(mensagens) == 4
    assert mensagens[1].tool_calls[0]["name"] == "consultar_status_pedido"
    assert mensagens[2].type == "tool"
    assert mensagens[3].content == "Seu pedido foi enviado com sucesso."