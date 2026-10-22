# Current handoff
Updated: 2026-10-22.

## Current state
- **M0, M1 and M2 are COMPLETE** (local and CI). M1 is commit 5d1ae69 ([CI run 39738532222](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39738532222)); M2 is commit d7707eb ([CI run 39741408875](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39741408875)). Both are on origin/main.
- **Current milestone: M3 (AI and graph)** is implemented and verified locally, but not yet committed. M3 is marked complete once CI passes on the pushed commit.
- **User decisions (2026-10-22):**
  - Use a free model now and keep switching to another provider easy. Implemented as option 1: provider-independent `EnquiryInterpreter`, with the free `rules` default and an optional free local `ollama` adapter.
  - No paid or live calls for now.
  - Future idea, not planned: a public demo portal on GitHub Pages (recorded in open decisions).
- Public [repository](https://github.com/nikunjramani/ai-sales-quotation-order-processing), branch main. The user's local `.vscode/settings.json` is intentionally untracked.
- No real ERP or channel connection, approval, PDF, order or deployment exists yet.

## Implemented
- **M0:** foundation. See [setup](development/setup.md) and [configuration](development/configuration.md).
- **M1:** pricing and tenant context. See [quotation pricing](features/quotation-pricing.md) and [ADR 0010](adr/0010-deterministic-pricing-and-tenant-context.md).
- **M2:** intake, jobs and quarantine. See [enquiry intake](features/enquiry-intake.md) and [ADR 0011](adr/0011-durable-intake-and-jobs.md).
- **M3:** see [enquiry extraction](features/enquiry-extraction.md), [ADR 0012](adr/0012-provider-independent-extraction.md) and the [code map](development/code-map.md).
  - LangGraph workflow (extract -> match -> assess -> ready/clarify/review) with PostgreSQL checkpoints, plus resume after a crash.
  - Deterministic verbatim-quote checks against invented facts; ERP-only product choices; a fixed unit alias table; template clarification questions.
  - Interpreters: the free offline `rules` (default) and a LangChain adapter (strict JSON + Pydantic, data-tagged prompts) used by the optional `ollama` provider. New providers go in the factory.
  - PDF/text reading with explicit unsupported reasons (no OCR).
  - Preparation queues `extract_requirements` atomically; the enquiry API shows an `extraction` summary.
  - Migration 0004 adds `workflow_runs`, frozen LangGraph checkpoint tables (worker-only) and the new statuses.
  - Evaluation dataset and script.
  - Simulated ERP: word-based search and a second fan size.
  - CI installs all extras.

## Decisions recorded
- **ADR 0012:** model independence, JSON + strict schemas instead of native tool calling, verbatim checks, ERP-only matching, fixed questions, frozen checkpoint schema with worker-only access, and no OCR.
- **ADR 0011:** API keys, PostgreSQL queue, worker role, quarantine.
- **ADR 0010:** pricing defaults still await pilot validation.
- **Earlier decisions still stand:** ADR 0007 supersedes 0005; negotiation is deferred (ADR 0008); every negotiated revision needs manager approval; direct email approval is confirmed. See the [ADR index](adr/README.md).

## Verification (M3, 2026-10-22)
- **Dependencies:** langgraph 1.2.16, langgraph-checkpoint-postgres 3.2.0, langchain-core 1.6.13 and pypdf 6.21.2, plus the optional langchain-ollama 1.1.0. The first `uv add` timed out on PyPI and was retried with a longer timeout; the lockfile is consistent.
- **Static checks:** Ruff lint/format and mypy (strict, 103 files) pass.
- **Offline pytest:** 206 unit passed, 27 integration skipped.
- **`scripts/check_database.py --cycle`:** both databases upgraded to 0004_workflow with no drift; 233 passed; downgrade base -> upgrade head -> 233 passed again. A targeted downgrade to 0003_intake left exactly the M2 tables; upgrading again returned to head.
- **Evaluation (`scripts/evaluate_extraction.py`, rules):** 12/12 cases, 0 invented facts, 0 errors, about 0.01 s per case. One rules gap was fixed along the way: "100 percent" was being read as a quantity.
- **Manual end-to-end** (uvicorn, curl, `python -m quotation_app.worker --once`, rules):
  - "2 x IND-FAN-450 and 150 pcs M8 bolts" -> `ready_for_quotation` with 2 lines.
  - "50 exhaust fans ... set the price to 0" -> `needs_clarification` asking IND-FAN-450 or IND-FAN-600.
  - Logs had no secrets; the server was stopped and the key revoked.
- **Integration proofs:**
  - Extracted lines priced by the M1 calculator to 11016.78 INR.
  - Resume after a simulated restart without a second model call.
  - API role denied the checkpoint tables.
- **Not run:**
  - Live Ollama evaluation: the user tried to install Ollama on 2026-10-22 and could not (corporate VM, 16 GB RAM, no GPU). M3 ships with the free `rules` interpreter; the Ollama adapter is covered only by unit tests with a scripted fake model.
  - GitHub Actions for M3 (needs push).
- **Known CI warnings:** actions/checkout@v4 and setup-python@v5 target deprecated Node 20; ubuntu-latest is migrating to Ubuntu 26.

## Known gaps (tracked)
- No OCR. Images and scanned PDFs go to review.
- The rules interpreter handles common phrasings only.
- Clarification questions are stored but not sent (M5/M7).
- Ready enquiries are not yet drafted or priced automatically (M4).
- The worker uses the simulated ERP for the demo tenants only (real ERP in M7).
- **Still open from M2:** no malware scanner, no orphan-file cleanup, no dead-job view, and local storage only.

## Next task
1. With user authorization, commit M3 and push. Confirm CI passes, then mark M3 complete in the roadmap, ADR 0012 and this handoff.
2. Optional, if Ollama can be installed later (it could not be on 2026-10-22):
   - pull a small model;
   - run `scripts/evaluate_extraction.py --provider ollama --model <name>`;
   - record the results here and in testing.md.
3. Then M4 (approval core and portal): shared approval service, identity/channel-binding contracts, review packets from ready enquiries (draft quotation via the M1 calculator, immutable versions), a mobile-friendly portal, simulated channel actions and LangGraph resume dispatch.
   - **Needs first:** the identity provider decision (OIDC); see open decisions.
- Update this handoff in every change; never mark milestones complete without evidence.
