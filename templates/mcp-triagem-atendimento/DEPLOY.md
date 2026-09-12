# Deploy — mcp-triagem-atendimento

Servidor MCP (TypeScript, Cloudflare Workers) com as ferramentas de
atendimento/triagem. Free tier da Cloudflare (100 mil requisições/dia).

## Pré-requisitos

- Node.js e npm instalados.
- Conta Cloudflare (grátis).

## Deploy do zero (novo cliente/ambiente)

```bash
npm create cloudflare@latest -- <nome-do-projeto> --template=cloudflare/ai/demos/remote-mcp-authless
cd <nome-do-projeto>
npm install
```

Copiar o conteúdo de `src/index.ts` deste projeto e ajustar os dados mockados
(`PEDIDOS_MOCK`, `POLITICAS_MOCK`) para o caso de uso do cliente.

Criar o namespace de KV (usado pela tool `escalar_para_humano` pra registrar
tickets de escalação):

```bash
npx wrangler kv namespace create TICKETS
```

Colar o bloco `id` retornado dentro de `wrangler.jsonc`, no formato:


"kv_namespaces": [
{ "binding": "TICKETS", "id": "<id-retornado>" }
]



Gerar os tipos TypeScript pro novo binding:

```bash
npm run cf-typegen
```

## Testar local antes de publicar

```bash
npm run dev
```

Validar com o MCP Inspector (`npx @modelcontextprotocol/inspector`),
conectando via "Streamable HTTP" em `http://localhost:8787/mcp`.

## Publicar

```bash
npx wrangler login
npm run deploy
```

Na primeira publicação de uma conta nova, a Cloudflare pede pra escolher um
subdomínio `workers.dev` — esse subdomínio é único por conta e serve pra
todos os Workers futuros dela, não só este projeto.

**Atenção:** depois do primeiro deploy de um subdomínio novo, o certificado
TLS pode levar alguns minutos pra propagar. Um `curl` retornando erro de
handshake TLS logo depois do deploy é esperado — esperar cerca de 5 minutos
e testar de novo antes de investigar como bug.

## Validar em produção

```bash
curl -X POST https://SEU-PROJETO.SEU-SUBDOMINIO.workers.dev/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}"
```

Deve retornar a lista das ferramentas expostas pelo servidor.

## Conectar ao agente LangGraph (Python)

No projeto Python, configurar a variável de ambiente `MCP_SERVER_URL` com a
URL pública do deploy (`https://SEU-PROJETO.SEU-SUBDOMINIO.workers.dev/mcp`).

O `graph.py` já busca as tools automaticamente dessa URL via
`langchain-mcp-adapters` quando `build_graph()` é chamado sem o parâmetro
`tools=` explícito.