import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

type Pedido = { status: string; codigo_rastreio: string | null; previsao_entrega: string };

const PEDIDOS_MOCK: Record<string, Pedido> = {
	"PED-123": { status: "enviado", codigo_rastreio: "BR123456789", previsao_entrega: "2026-09-20" },
	"PED-456": { status: "processando", codigo_rastreio: null, previsao_entrega: "2026-09-25" },
	"PED-789": { status: "entregue", codigo_rastreio: "BR987654321", previsao_entrega: "2026-09-10" },
};

const POLITICAS_MOCK: Record<string, string> = {
	eletronicos: "Reembolso integral permitido em até 7 dias corridos após o recebimento, desde que o produto esteja na embalagem original sem avarias.",
	vestuario: "Troca ou reembolso garantidos em até 30 dias após o recebimento. Peças devem conter etiqueta intacta e sem sinais de uso.",
	alimentos: "Reembolso aplicável apenas em caso de avaria, produto vencido ou item incorreto reportado em até 24 horas após o recebimento.",
};

function createServer(env: Env) {
	const server = new McpServer({ name: "triagem-atendimento", version: "1.0.0" });

	server.registerTool(
		"consultar_status_pedido",
		{ inputSchema: z.object({ pedido_id: z.string() }) },
		async ({ pedido_id }) => {
			const pedido = PEDIDOS_MOCK[pedido_id.trim()];
			if (!pedido) {
				return {
					content: [{ type: "text", text: `Pedido '${pedido_id}' não encontrado no sistema.` }],
					isError: true,
				};
			}
			const rastreio = pedido.codigo_rastreio ? ` Código de rastreio: ${pedido.codigo_rastreio}.` : "";
			return {
				content: [{ type: "text", text: `Status: ${pedido.status}.${rastreio} Previsão de entrega: ${pedido.previsao_entrega}.` }],
			};
		},
	);

	server.registerTool(
		"verificar_politica_reembolso",
		{ inputSchema: z.object({ categoria_produto: z.string() }) },
		async ({ categoria_produto }) => {
			const politica = POLITICAS_MOCK[categoria_produto.trim().toLowerCase()];
			const texto = politica ?? `Política de reembolso não encontrada para a categoria '${categoria_produto}'. Consulte as condições gerais de suporte.`;
			return { content: [{ type: "text", text: texto }] };
		},
	);

	server.registerTool(
		"escalar_para_humano",
		{ inputSchema: z.object({ motivo: z.string() }) },
		async ({ motivo }) => {
			const ticketId = crypto.randomUUID();
			await env.TICKETS.put(ticketId, JSON.stringify({ motivo, status: "pendente", criado_em: new Date().toISOString() }));
			return {
				content: [{ type: "text", text: `Escalação registrada. ticket_id: ${ticketId}. Motivo: ${motivo}. Aguardando aprovação humana.` }],
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
