from __future__ import annotations

import uuid
from typing import Any

from langchain_core.tools import tool

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
    """Aciona a escalação do atendimento para um operador humano quando o agente não consegue resolver a solicitação.

    Nota de arquitetura: esta versão local só registra o pedido de escalação
    e retorna, imitando o contrato da versão MCP (Fase 2) — ela NÃO pausa a
    execução sozinha. Quem pausa esperando aprovação humana é o nó
    `aguardar_aprovacao_humana` do grafo, depois que esta tool retorna.
    """
    ticket_id = str(uuid.uuid4())
    return f"Escalação registrada. ticket_id: {ticket_id}. Motivo: {motivo}. Aguardando aprovação humana."
