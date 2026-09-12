from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from langgraph.types import interrupt

MOCK_PEDIDOS: dict[str, dict[str, Any]] = {
    "PED-123": {
        "id": "PED-123",
        "status": "enviado",
        "codigo_rastreio": "BR123456789",
        "previsao_entrega": "2026-09-20",
    },
    "PED-456": {
        "id": "PED-456",
        "status": "processando",
        "codigo_rastreio": None,
        "previsao_entrega": "2026-09-25",
    },
    "PED-789": {
        "id": "PED-789",
        "status": "entregue",
        "codigo_rastreio": "BR987654321",
        "previsao_entrega": "2026-09-10",
    },
}

MOCK_POLITICAS: dict[str, str] = {
    "eletronicos": "Reembolso integral permitido em até 7 dias corridos após o recebimento, desde que o produto esteja na embalagem original sem avarias.",
    "vestuario": "Troca ou reembolso garantidos em até 30 dias após o recebimento. Peças devem conter etiqueta intacta e sem sinais de uso.",
    "alimentos": "Reembolso aplicável apenas em caso de avaria, produto vencido ou item incorreto reportado em até 24 horas após o recebimento.",
}


@tool
def consultar_status_pedido(pedido_id: str) -> dict[str, Any]:
    """Consulta o status e detalhes de entrega de um pedido com base no seu identificador."""
    pedido = MOCK_PEDIDOS.get(pedido_id.strip())
    if not pedido:
        raise ValueError(f"Pedido '{pedido_id}' não encontrado no sistema.")
    return pedido


@tool
def verificar_politica_reembolso(categoria_produto: str) -> str:
    """Verifica as regras de reembolso aplicáveis para uma categoria de produto."""
    categoria = categoria_produto.strip().lower()
    return MOCK_POLITICAS.get(
        categoria,
        f"Política de reembolso não encontrada para a categoria '{categoria_produto}'. Consulte as condições gerais de suporte.",
    )


@tool
def escalar_para_humano(motivo: str) -> str:
    """Aciona a escalação do atendimento para um operador humano quando o agente não consegue resolver a solicitação."""
    resposta_humano = interrupt(
        {
            "acao": "escalar_para_humano",
            "motivo": motivo,
        }
    )

    if not isinstance(resposta_humano, dict):
        raise TypeError("A resposta da intervenção humana deve ser um dicionário.")

    aprovado = resposta_humano.get("aprovado", False)
    observacao = resposta_humano.get("observacao")

    if aprovado:
        msg = f"Escalação aprovada pelo operador. Motivo: {motivo}."
        if observacao:
            msg += f" Observação: {observacao}"
        return msg

    msg = f"Escalação recusada pelo operador. Motivo informado: {motivo}."
    if observacao:
        msg += f" Instrução do operador: {observacao}."
    msg += " Continue o atendimento tentando resolver o problema diretamente com o cliente."
    return msg
