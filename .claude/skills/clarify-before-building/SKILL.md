---
name: clarify-before-building
description: Ask the user every open question before starting a milestone, feature or design change, and never fill gaps with assumptions. Use at the start of any new milestone (M6, M7...), any new feature or screen, any change of scope, and whenever a business rule, policy, provider, data shape or user-visible behaviour is not already decided in the repository.
---

# Clarify before building

The user wants to be asked, not guessed for. A wrong assumption in this project (prices, approvals,
customer acceptance, orders, ERP writes) is a business error, not just a code bug. This skill is the
procedure for turning "I think they want..." into "they decided...".

## When to use
- Before writing code for a new milestone or feature.
- When the user's request is short or general ("move to M6", "add orders", "make it better").
- When, in the middle of work, you hit a choice the documents do not settle. Stop and ask then; do
  not pick one "for now".

## Procedure
1. **Read first, so you only ask what is really open.**
   - `AGENTS.md`, `.docs/handoff.md`, `.docs/agent-context.md`, `.docs/plan/roadmap.md` (the
     milestone row and its exit gate), `.docs/plan/open-decisions.md`, and the related ADRs and
     feature documents.
   - The actual code the work will touch.
2. **List every open point**, grouped by type, and for each note why it matters:
   - business rules and policies (who may do what, limits, timings, what happens on failure);
   - scope (what is in this milestone, what is explicitly later);
   - user-visible behaviour (screens, messages, documents, customer experience);
   - integrations and providers (which system, sandbox or real, accounts, costs);
   - data (what is stored, how long, who sees it);
   - technical choices that change cost, security or effort (libraries, infrastructure).
   A point is open if no ADR, open-decisions row, roadmap line or earlier user answer settles it.
   "The obvious default" is still open when it changes behaviour the business would notice.
3. **Ask with the AskUserQuestion tool**, in rounds of up to 4 questions:
   - Most important (blocking) questions first.
   - Each question in plain words, explaining the term if it is technical.
   - 2-4 concrete options, each with its consequence (what the user/customer will see, risk,
     effort, cost). Put a recommendation first and label it "(Recommended)" only when you have a
     real reason, and say the reason.
   - Never bundle two decisions into one question.
   - If an answer is unclear, partial or "you decide", ask a short follow-up, or state your exact
     proposal and ask for a yes/no. Do not silently interpret it.
4. **Repeat** until no blocking point is open. Non-blocking points may be recorded as open
   decisions with the user's agreement, never decided silently.
5. **Play the decisions back** in a short summary (what will be built, what will not, the rules
   chosen) and get a confirmation before coding.
6. **Record the answers in the repository**, not only in chat, before or with the code:
   ADR for architecture/business-rule decisions, `open-decisions.md` (resolved or still open),
   roadmap scope changes, and the handoff ("User decisions (date)").
7. **During implementation**, if something new comes up that the answers do not cover, stop and
   ask again (steps 2-3) instead of choosing.

## Never
- Never invent business rules, prices, limits, durations, wording for customers, provider choices
  or account details.
- Never treat a plan document's proposed design as the user's decision for a detail it leaves open.
- Never ask questions the repository already answers; cite where it is answered instead.
- Never present an assumption as a fact in code comments, docs or summaries. If something had to
  stay open, label it "open decision" and say who decides.
