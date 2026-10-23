# Plan: Gemini enquiry reader and category-based "not found" replies
**Status:** planned, not started (user decisions 2026-10-23). The user asked for this plan to be stored here, not in chat history. Start on a new branch `feat/gemini-and-categories` from `main`; ask again before changing any decision below.

## Context
In the demo, "can you get price for tata cars" got the same fixed reply twice ("Which products and
quantities…?"). Causes:
- **No AI runs today.** The free `rules` reader only spots "number + product" phrases. The Ollama
  slot exists but can't be installed on this VM.
- **Unhelpful replies.** When nothing is recognised or matched, the reply doesn't say the product
  isn't sold, or what the business does sell.

**User decisions (2026-10-23):**
- **Provider:** Google Gemini free tier, small model (Flash-Lite class). API reachable from this VM
  (checked).
- **If AI is down or rate-limited:** wait and retry (current job retry behaviour). No fallback to
  rules.
- **Not found:** say the product was not found and list the business's **categories**, not
  individual products. If the customer asks about a category, reply with that category's products.
- **Reply wording:** customer replies stay fixed templates; AI only reads the enquiry (option 3,
  "AI writes replies", was not chosen). Templates are generic and driven by ERP data, with no
  per-product logic.

## Part A: Gemini provider (an adapter only; the workflow is unchanged)
- `pyproject.toml`
  - Add an optional extra `gemini = ["langchain-google-genai>=X,<Y"]`, pinned to a release at least
    14 days old (check PyPI first).
  - `uv lock`; CI already syncs `--all-extras`.
- [config.py](../../src/quotation_app/config.py)
  - `model_provider: Literal["rules","ollama","gemini"]`.
  - New `gemini_api_key: SecretStr | None` (env `QUOTATION_GEMINI_API_KEY`).
  - Validation: provider `gemini` requires the key and `model_name`.
- [factory.py](../../src/quotation_app/adapters/interpreters/factory.py)
  - New `gemini` branch with a lazy import of `ChatGoogleGenerativeAI`: model, `api_key`,
    `temperature=0`, JSON output if supported, timeout and limited internal retries.
  - It returns the existing `LangChainInterpreter`, so the prompt-injection containment, strict
    schemas and verbatim-quote checks are all reused.
- **Wait and retry:** confirm that Gemini connection, 429 and 5xx errors propagate as non-permanent
  errors, so the durable job retries with backoff (as for Ollama today). Only schema failures become
  `InterpretationRejected`, which leads to `needs_review`. Wire the factory call sites (worker) to
  pass the key.
- [.env.example](../../.env.example): commented `QUOTATION_MODEL_PROVIDER=gemini`, `QUOTATION_MODEL_NAME`
  and `QUOTATION_GEMINI_API_KEY`. Look up the current Flash-Lite model ID at implementation.
- [evaluate_extraction.py](../../scripts/evaluate_extraction.py): add `gemini` to the providers, reading
  the key from settings.

## Part B: Product categories, data-driven
- [domain/catalogue.py](../../src/quotation_app/domain/catalogue.py)
  - `Product` gains `category: str | None = None`.
  - Update the workflow-state (de)serialisers `_product_to_state` / `_product_from_state` in
    [workflows/enquiry.py](../../src/quotation_app/workflows/enquiry.py). Old checkpoints have no category,
    so default to None.
- [ports/erp.py](../../src/quotation_app/ports/erp.py)
  - `ErpReader.list_categories(context) -> Sequence[str]`: distinct category names, sorted.
  - Real ERP adapters map it to their product groups later.
- [adapters/erp/simulated.py](../../src/quotation_app/adapters/erp/simulated.py)
  - Synthetic categories:
    - industrial: Exhaust fans, Fasteners, Cables, Pumps;
    - office: matching groups.
  - `list_categories` returns these.
  - `search_products` also matches category words, so "which pumps / fasteners do you have"
    finds that category's products.
- **Replies** in [domain/requirements.py](../../src/quotation_app/domain/requirements.py) `assess(...)`
  gains `categories: Sequence[str]`. These remain fixed templates:
  - **No items understood:** "Which products and quantities would you like a quotation for? We
    supply: Exhaust fans, Fasteners, Cables, Pumps. Ask about a category to see its products."
  - **Item not found:** "We could not find 'Tata Sierra car' in our catalogue. We supply: …
    Ask about a category to see its products, or share a product code."
  - **Category follow-ups use the existing paths:**
    - several matches give the existing "which product did you mean: SKU (description), …" (up to
      5);
    - one match with no quantity gives the existing "How many … do you need?".
    - No prices are shown in replies (unchanged).
- The `assess_step` node in [workflows/enquiry.py](../../src/quotation_app/workflows/enquiry.py) calls
  `deps.erp.list_categories(...)` only when a not-found or no-items question is needed. It uses the
  same read-only system context, and ERP errors follow the existing retry rules.

## Tests (mirrored `tests/` folders)
- **Unit, domain:** `assess` messages for no items, not found (category list), an empty category
  list (graceful wording), and category-only follow-ups.
- **Unit, ERP:** simulated `list_categories`; search by category word; tenant isolation.
- **Unit, factory and config:** `gemini` builds a `LangChainInterpreter` with no network call (patch
  the import). A missing key or model gives a clear error.
- **Unit, workflow:** a not-found item yields the category reply; a fake interpreter returns
  "tata sierra car" with no quantity.
- **Evaluation dataset:** add synthetic cases for an unsold product and a category question.
  Rules must still pass 100%.
- **Gemini sandbox run:** opt-in only (needs your key), with
  `uv run python scripts/evaluate_extraction.py --provider gemini --model <id>`. It runs on
  synthetic data only, because the free tier may use prompts to improve Google products.

## Docs
- **ADR 0017:** Gemini free tier as the first hosted reader, the wait-and-retry rule, category
  replies, and "replies stay templates".
- **Updates:**
  - open-decisions: the model provider row;
  - [configuration.md](../development/configuration.md);
  - the extraction feature doc;
  - handoff "User decisions (2026-10-23)";
  - demo README (how to switch to Gemini).
- **Free-tier warning:** synthetic data only; move to a paid tier or another provider before real
  customer data.

## Workflow
- Branch `feat/gemini-and-categories` from up-to-date `main`. Do not merge PR #2 myself.
- Commit, push and open a PR to main. Never push to main.

## Verification
1. `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`.
2. `scripts/check_database.py --cycle` for integration tests. There is no migration, because
   categories come from the ERP, not the DB.
3. `uv run python scripts/evaluate_extraction.py` passes (rules).
4. **With your Gemini key in `.env`** (I will ask for it to be set; I never see or commit it):
   - Run the Gemini evaluation.
   - Run the live demo (`demo/run_demo.py` with `QUOTATION_MODEL_PROVIDER=gemini`):
     - "i need a price for tata sierra car" gives "not found + We supply: Exhaust fans,
       Fasteners, Cables, Pumps";
     - "which pumps do you have?" gives a pump question;
     - "2 x IND-FAN-450 and 150 M8 bolts" still reaches approval and the PDF.
   - Stopping the network or using a bad key makes the job retry; the customer sees
     "processing…".
5. Push the branch; CI green; report the CI run.
