# Security Checklist — agent-toolkit

Security checklist applied to every tool in every template of this toolkit.
First filled out for triagem-atendimento (Python + MCP).

## consultar_status_pedido (check order status)

- Data read today: in-memory mock dictionary, no real database access.
- Data read in real production: only the specific order queried, never the
  full orders table. The credential/token used by the tool should be scoped
  per order_id or, at minimum, per authenticated customer session — never a
  full-access key to the entire orders database.
- Writes: none. Read-only tool.
- Known and handled failure: nonexistent order raises a structured error
  (does not leak internal database details, does not crash the agent).

## verificar_politica_reembolso (check refund policy)

- Data read today: mock dictionary of policies per category.
- Data read in real production: public content (refund policy is not
  sensitive data), so this tool can keep broad access without real risk —
  the safest of the three by nature.
- Writes: none.

## escalar_para_humano (escalate to human)

- Data written today: ticket record in Cloudflare KV (reason, status,
  timestamp) — no personal customer data yet, since the template is mocked.
- Data written in real production: if the ticket starts including customer
  identification (name, order, contact info), the KV entry stops being
  "arbitrary data" and becomes personal data — at that point, evaluate
  whether Cloudflare KV is adequate (no field-level encryption by default)
  or whether it should move to storage with stronger access control,
  depending on the client's data policy.
- Main risk: this is the only tool with a real side effect (it writes data).
  It's the highest-attention point in the whole template — never let this
  tool gain permission to do more than register a ticket. It must never, in
  any future version, gain the ability to execute the escalated action by
  itself (e.g. sending an email, notifying Slack) without additional review
  — that would widen the attack surface via prompt injection.
- Human approval: mandatory before any subsequent action based on the
  escalation — this is why the graph pauses with interrupt() instead of
  trusting the tool alone.

## General rules applied to every new tool in this toolkit

- Never hardcode credentials in source code — always use environment
  variables or the provider's secret manager (Wrangler secrets, local .env
  that is never committed).
- Every tool with a side effect (writes, sends, transacts) requires human
  confirmation before any irreversible consequence.
- Tool errors must never expose internal stack traces or infrastructure
  details to the model — only the business-level message that is needed.
- Least privilege per tool: each tool only accesses the minimum scope of
  data required for its specific function, never a generic "account-wide"
  access.
