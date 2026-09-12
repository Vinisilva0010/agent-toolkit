# agent-toolkit

Reference architecture for building production-minded AI agents. Not a
finished product — a proven skeleton you adapt to a real use case in hours
instead of weeks.

Built and tested with a customer support triage agent (`triagem-atendimento`),
which is the concrete example everything in this repo refers to.

## What's in the box

- **`templates/triagem-atendimento`** — the agent itself. Python + LangGraph.
  State machine, tool routing, hard human-approval pause via `interrupt()`.
- **`templates/mcp-triagem-atendimento`** — the tools, served over MCP.
  TypeScript + Cloudflare Workers. Deployed at
  `https://mcp-triagem-atendimento.viniciuspontual.workers.dev/mcp`.
- **`templates/triagem-web`** — HTTP + web interface. FastAPI backend +
  Next.js frontend. Local only; no hosting required for the demo.
- **`SECURITY_CHECKLIST.md`** — least-privilege review per tool + automated
  red-team suite (jailbreak, secret exfiltration, escalation abuse,
  destructive-code requests).

## Run it locally

```bash
# 1. Set your Gemini API key (free tier is fine)
echo 'GOOGLE_API_KEY="your-key-here"' > templates/triagem-atendimento/.env
echo 'MCP_SERVER_URL=https://mcp-triagem-atendimento.viniciuspontual.workers.dev/mcp' >> templates/triagem-atendimento/.env

# 2. Backend
cd templates/triagem-web/api
uv sync
uv run uvicorn api.main:app --port 8000

# 3. Frontend (in another terminal)
cd templates/triagem-web/web
npm install
npm run dev
# open http://localhost:3000
```

Get a free Gemini key at https://aistudio.google.com/apikey (no credit card).

## Adapting to a new use case

Four files change. Everything else stays.

### 1. Tools — what the agent can actually do

**File:** `templates/mcp-triagem-atendimento/src/index.ts`

The example ships with three mocked tools: check order status, check refund
policy, escalate to a human. Replace them with your real ones (query your
CRM, hit your API, write to your database). Keep the same shape:

- `name` — snake_case, verb first (`check_customer_tier`).
- `inputSchema` — zod schema, one object with primitive fields.
- Return `{ content: [{ type: "text", text: "..." }] }` — a single string
  the model can read.
- Any tool that changes state must return a `ticket_id` (or equivalent) and
  let the agent's graph pause for human approval before the action is
  actually executed. Never let a tool do the destructive action itself.

Redeploy: `npm run deploy`.

### 2. Model — which LLM answers

**File:** `templates/triagem-atendimento/src/triagem_atendimento/graph.py`

Line to change is the `ChatGoogleGenerativeAI(model="...")` call. Swap for
`ChatOpenAI`, `ChatAnthropic`, or any LangChain-compatible model. Move the
model name to an env var (`GEMINI_MODEL`, `OPENAI_MODEL`) so switching
models per client doesn't need a code change.

### 3. Approval flow — who approves what

**File:** `templates/triagem-atendimento/src/triagem_atendimento/graph.py`

The `aguardar_aprovacao_humana` node is where the graph pauses and waits
for a human decision. Today the decision comes from the web UI's Approve
/ Reject buttons. To route it to Slack, WhatsApp, email — anything with
an "approve link" — replace the `interrupt()` payload with the notification
you want, and resume the graph via the `/approve` endpoint when the human
clicks the link.

### 4. Instructions — how the agent behaves

**File:** `templates/triagem-atendimento/src/triagem_atendimento/graph.py`

Add a system prompt as the first message in the graph state, describing the
agent's role, tone, boundaries, and when it should escalate. The security
checklist expects this to be explicit — an unspecified agent is an
unpredictable agent.

## Security

Before shipping to a client, run through `SECURITY_CHECKLIST.md` for every
new tool, and re-run the Promptfoo suite in
`templates/triagem-atendimento/promptfooconfig.yaml` against the real tools
(not the mocks). All assertions are deterministic — no paid judge model
required.

## What this is not

- Not a hosted product. Deployment is on you or the client.
- Not a no-code builder. Adaptation requires editing four files.
- Not a chatbot. If you just need a chatbot, use something else.
- Not battle-tested at scale. It's a reference architecture, proven by
  passing tests and a red-team pass — not by production traffic.

## License

MIT.
