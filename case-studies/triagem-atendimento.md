# Building a Production-Ready Support Triage Agent: Architecture, Not Magic

Most "AI agent" demos are a chatbot wrapped around a single LLM call. They
work fine until a tool call fails, someone tries something adversarial, or
the business needs a human to sign off before anything happens. This project
is what it looks like to build for that reality instead of around it.

## The problem

A customer support flow with three real needs: check an order's status,
check a refund policy, and — when the agent genuinely can't help — get a
human involved. Simple on paper. Most of the engineering work is in what
happens when things don't go as planned.

## A state graph instead of a single prompt

The agent is built as an explicit state graph (LangGraph), not one large
prompt trying to do everything. Every turn is a node: the model decides,
tools execute, control returns to the model. State and conversation history
are checkpointed at every step, so a session can pause and resume exactly
where it left off — which matters a lot for the next point.

## Human approval as a hard pause, not a suggestion

When the agent decides a case needs a human, execution actually stops and
waits for a real decision — approve or reject, with a note — before
continuing. This isn't a prompt asking the model to "be careful." It's a
pause enforced by the graph itself, at the exact point where an irreversible
action would otherwise happen.

## Tools as a separate, swappable service (MCP)

The three tools live behind a Model Context Protocol server, deployed
independently on Cloudflare Workers. The agent doesn't call Python functions
directly — it calls a service over HTTP, the same way it would call any
other API. That means the tool layer can be redeployed, reused across
different clients or even different agent frameworks, without touching the
orchestration logic at all.

## Security treated as a constraint, not an afterthought

Every tool went through a least-privilege review before being considered
done, and the agent is tested against an automated red-team suite —
role-override attempts, secret exfiltration, escalation abuse, requests to
generate destructive code — run against the real model, not a mock. All of
it runs on free-tier infrastructure, so testing thoroughly never became a
reason to cut corners.

## What this actually means for a client

There's a real difference between "we added AI to our product" and
"we built something that survives real usage, real users, and real attempts
to break it." This project is the second kind: not flashier, just built to
still be working the way it's supposed to after the demo is over.

Source code, tests, and deployment docs are public on GitHub.
