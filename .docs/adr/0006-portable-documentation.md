# 0006: Versioned documentation and portable agent instructions
Date: 2026-10-22
Status: accepted design; implementation pending

## Context
AI-written code must remain understandable across sessions, tools and humans.

## Decision
Keep plans, ADRs, execution flow, code map, testing/runbooks and handoff under .docs. Use AGENTS.md as shared rules and CLAUDE.md as an entry pointer. Update documentation with each relevant change.

## Alternatives considered
Chat-only memory; divergent agent-specific rule copies; document after implementation ends.

## Consequences
Documentation is part of delivery. Private skills/tools are not portable automatically. Planned and implemented behaviour must be distinguished.

## Verification
Check local links, required docs, implementation claims and handoff status at completion.
