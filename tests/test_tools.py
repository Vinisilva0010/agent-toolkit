from __future__ import annotations

import pytest
from langchain_core.tools import BaseTool

from triagem_atendimento.tools.atendimento import (
    consultar_status_pedido,
    escalar_para_humano,
    verificar_politica_reembolso,
)


def test_consultar_status_pedido_sucesso():
    resultado = consultar_status_pedido.invoke({"pedido_id": "PED-123"})
    assert isinstance(resultado, dict)
    assert resultado["id"] == "PED-123"
    assert resultado["status"] == "enviado"
    assert resultado["codigo_rastreio"] == "BR123456789"


def test_consultar_status_pedido_inexistente():
    with pytest.raises(ValueError, match="Pedido 'PED-999' não encontrado"):
        consultar_status_pedido.invoke({"pedido_id": "PED-999"})


def test_verificar_politica_reembolso_sucesso():
    resultado = verificar_politica_reembolso.invoke(
        {"categoria_produto": "eletronicos"}
    )
    assert isinstance(resultado, str)
    assert "7 dias corridos" in resultado


def test_verificar_politica_reembolso_categoria_invalida():
    resultado = verificar_politica_reembolso.invoke({"categoria_produto": "automotivo"})
    assert isinstance(resultado, str)
    assert (
        "Política de reembolso não encontrada para a categoria 'automotivo'"
        in resultado
    )


def test_escalar_para_humano_declaracao():
    assert isinstance(escalar_para_humano, BaseTool)
    assert escalar_para_humano.name == "escalar_para_humano"
    assert escalar_para_humano.description is not None
    assert len(escalar_para_humano.description.strip()) > 0
