from __future__ import annotations

import asyncio
import logging
import sys
import warnings

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from triagem_atendimento.graph import build_graph

logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")


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


async def main() -> None:
    graph = await build_graph()
    config = {"configurable": {"thread_id": "cli-session"}}

    print("Agente de triagem de atendimento. Digite sua mensagem (Ctrl+C para sair).\n")

    try:
        while True:
            user_input = input("Você: ").strip()
            if not user_input:
                continue

            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=user_input)]}, config
            )

            while "__interrupt__" in result:
                interrupt_info = result["__interrupt__"][0].value
                ticket_id = interrupt_info.get("ticket_id", "desconhecido")
                detalhes = _extract_text(interrupt_info.get("detalhes", "Sem detalhes."))

                print("\n[APROVAÇÃO HUMANA NECESSÁRIA]")
                print(f"Ticket: {ticket_id}")
                print(f"Detalhes: {detalhes}")
                resposta = input("Aprovar escalação? (s/n): ").strip().lower()
                observacao = input("Observação (opcional): ").strip() or None

                result = await graph.ainvoke(
                    Command(
                        resume={"aprovado": resposta == "s", "observacao": observacao}
                    ),
                    config,
                )

            resposta_final = _extract_text(result["messages"][-1].content)
            print(f"\nAgente: {resposta_final}\n")

    except KeyboardInterrupt:
        print("\nAtendimento encerrado.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
