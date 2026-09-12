import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

const PEDIDOS_MOCK: Record<string, { status: string; previsao_entrega: string }> = {
	"123": { status: "enviado", previsao_entrega: "2026-09-15" },
	"456": { status: "em processamento", previsao_entrega: "2026-09-20" },
	"789": { status: "entregue", previsao_entrega: "2026-09-05" },
};

const POLITICAS_MOCK: Record<string, string> = {
	eletronicos: "Reembolso integral em até 7 dias corridos após a entrega, produto sem sinais de uso.",
	roupas: "Troca ou reembolso em até 30 dias corridos, com etiqueta original.",
};

function createServer(env: Env) {
	const server = new McpServer({
		name: "triagem-atendimento",
		version: "1.0.0",
	});

	server.registerTool(
		"consultar_status_pedido",
		{ inputSchema: z.object({ pedido_id: z.string() }) },
		async ({ pedido_id }) => {
			const pedido = PEDIDOS_MOCK[pedido_id];
			if (!pedido) {
				return {
					content: [{ type: "text", text: `Pedido '${pedido_id}' não encontrado.` }],
					isError: true,
				};
			}
			return {
				content: [
					{
						type: "text",
						text: `Status: ${pedido.status}. Previsão de entrega: ${pedido.previsao_entrega}.`,
					},
				],
			};
		},
	);

	server.registerTool(
		"verificar_politica_reembolso",
		{ inputSchema: z.object({ categoria_produto: z.string() }) },
		async ({ categoria_produto }) => {
			const politica = POLITICAS_MOCK[categoria_produto.toLowerCase()];
			const texto =
				politica ??
				`Política de reembolso não encontrada para a categoria '${categoria_produto}'.`;
			return { content: [{ type: "text", text: texto }] };
		},
	);

	server.registerTool(
		"escalar_para_humano",
		{ inputSchema: z.object({ motivo: z.string() }) },
		async ({ motivo }) => {
			const ticketId = crypto.randomUUID();
			await env.TICKETS.put(
				ticketId,
				JSON.stringify({
					motivo,
					status: "pendente",
					criado_em: new Date().toISOString(),
				}),
			);
			return {
				content: [
					{
						type: "text",
						text: `Escalação registrada. ticket_id: ${ticketId}. Aguardando aprovação humana.`,
					},
				],
			};
		},
	);

	return server;
}

export default {
	fetch(request: Request, env: Env, ctx: ExecutionContext) {
		return createMcpHandler(() => createServer(env))(request, env, ctx);
	},
} satisfies ExportedHandler<Env>;
