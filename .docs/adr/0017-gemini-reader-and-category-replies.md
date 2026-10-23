# 0017: Gemini as the first hosted enquiry reader, and category-based "not found" replies
Date: 2026-10-23
Status: accepted; implemented on branch `feat/gemini-and-categories` (verified locally; the live Gemini evaluation waits for the user's API key)
Builds on [0012](0012-provider-independent-extraction.md); plan: [gemini-and-categories](../plan/gemini-and-categories.md)

## Context
In the demo, "can you get price for tata cars" got the same fixed reply twice ("Which products and quantities…?"). There were two reasons:
- **No AI was running.** The free `rules` reader only recognises "number + product", and Ollama could not be installed on this VM.
- **The reply was unhelpful.** It said neither that the product isn't sold nor what is sold.

The user answered each open point on 2026-10-23 ([clarify-before-building](../../.claude/skills/clarify-before-building/SKILL.md)).

## Decision
| Topic | Decision (user, 2026-10-23) |
|---|---|
| Hosted reader | Google Gemini **free tier**, small model: `gemini-3.5-flash-lite`, listed as stable on Google's models page (checked 2026-10-23). Provider `gemini` through the existing LangChain adapter |
| Data | Free-tier prompts **are used to improve Google's products** (Google pricing page): synthetic/demo data only. Move to a paid tier or another provider before real customer data |
| AI unavailable, rate-limited or bad key | **Wait and retry:** the durable job retries with backoff and resumes from its checkpoint. There is no fallback to `rules` |
| Product not in the catalogue | Say so and name the business's **categories** (from the ERP), e.g. "We could not find 'tata sierra car' in our catalogue. We supply: Cables, Exhaust fans, Fasteners, Pumps. Ask about a category to see its products, or share a product code." The same list is added when nothing was understood |
| Asking about a category | Uses the existing questions: several products give "which product did you mean: …" (up to 5); one product gives "How many … do you need?". No prices in replies |
| Reply wording | Customer replies stay **fixed templates**; the AI only reads the enquiry. AI-written replies were offered and not chosen |

## Implementation
- `Settings.model_provider` gains `gemini`, plus `QUOTATION_GEMINI_API_KEY` (a secret). Settings refuse `gemini` without a model name and key.
- The factory builds `ChatGoogleGenerativeAI` with JSON output, temperature 0, a timeout and 2 client retries. It runs inside `LangChainInterpreter`, so prompt-injection containment, strict schemas and the verbatim-quote checks are unchanged.
- **Dependencies:**
  - optional extra `gemini`, with `langchain-google-genai` 4.4.0;
  - transitive pins `google-genai<=2.29.0`, `google-auth<=2.61.0` and `pycparser<=3.1`, which keep every new package at least 14 days old.
- `Product.category` holds the ERP product group. `ErpReader.list_categories()` returns the tenant's sorted groups. ERP search also matches category words, so "fasteners" finds M8 bolts.
- The workflow asks the ERP for categories only when the reply needs them. ERP errors there are retried like any other ERP read. Checkpoints from before categories still load, with the category treated as none.

## Alternatives offered and not chosen
- Claude API (paid).
- Waiting for local Ollama.
- Groq free tier.
- Falling back to rules when AI is down.
- Listing individual products instead of categories.
- AI-written customer replies.

## Consequences
- A missing or wrong Gemini key does not stop the worker from starting, as long as both values are set; each extraction job retries and, after 5 attempts, becomes dead. This is "wait and retry"; there is no dead-job view yet.
- Real ERPs must map their product groups to `list_categories` (adapter work in M7).

## Verification (2026-10-23)
- **Unit:** 339 tests, including templates, `needs_categories`, simulated ERP categories and search, tenant isolation (another business's categories are never named), category lookup failure retried, Gemini factory without network, settings validation, and evaluation question checks.
- **PostgreSQL:** the full suite (383) after the downgrade/upgrade cycle.
- **Evaluation (rules):** 14/14 cases, including the new "unsold product" cases.
- **Live (API and worker):**
  - "can you get price for tata cars" and "…2 tata sierra car" gave the category replies;
  - "2 x IND-FAN-450" was still ready for quotation;
  - a Gemini worker with an invalid key logged `retry … (GoogleInvalidRequestError)`, with no key in the logs.
- **Still to do:** a live Gemini evaluation with the user's key.
