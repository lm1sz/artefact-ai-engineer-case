# Empório da Música

A Python customer-service agent for the supplied music-store challenge. It uses seven read-only tools to answer catalog, policy, payment and authorized-order questions. The CLI is the agent interface; `ui/` is an optional scripted visual prototype.

**Validation status:** 56 deterministic tests pass. Five offline reference conversations cover 13 customer turns. These verify Python behavior and scripted orchestration; GPT-6.1 Sol end-to-end validation is still pending API access.

## Start here: review without an API key

Python 3.11+ is required. From the repository root on Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m chatbot --check
.\.venv\Scripts\python.exe -m unittest discover -s chatbot/tests -v
.\.venv\Scripts\python.exe chatbot/scripts/evaluate.py --offline
```

On macOS/Linux, create the environment with `python3 -m venv .venv` and replace `.\.venv\Scripts\python.exe` with `.venv/bin/python` in the commands. No `.env` or API key is needed for these checks. Installation downloads the declared dependencies; the checks themselves make no model/API requests.

Read the [English written case](chatbot/docs/WRITTEN_CASE.md) for the rationale and requirement mapping, then the five [reference conversations](chatbot/examples/reference/). `run.json` contains the actual tool inputs and outputs behind each reference. A successful `--check` validates source loading and local configuration, **not** API connectivity.

## Structure

```text
chatbot/
  agent.py         # Conversation loop, history and tool calls
  prompt.txt       # Persona, grounding and response instructions
  tools.py         # Seven tools, argument validation and business rules
  data.py          # CSV/PDF loading and personal-data masking
  providers.py     # GPT-6.1 Sol configuration and OpenAI Responses transport
  cli.py           # Terminal interface
  data/            # Anonymized CSVs and source policy PDF
  tests/           # Business rules, orchestration and provider tests
  scripts/         # Evaluation, anonymized data preparation and delivery packaging
  examples/        # Explicitly labeled offline reference conversations
  docs/            # English technical case summary
  private/         # Local originals, notes and past evaluations; excluded from Git
ui/
  index.html
  app.js
  style.css
```

## Technical choices

- **Function calling:** structured tool requests let Python enforce argument and ownership rules independently of the model.
- **Direct CSV queries:** the small structured dataset does not need semantic retrieval or model-written SQL.
- **PDF pages by topic:** explicit mappings keep the eight-page policy source auditable; changed pagination requires maintenance.
- **GPT-6.1 Sol:** selected based on the candidate's familiarity with the model. Its quality, latency and cost in this agent have not yet been validated end to end.
- **No extra framework:** a bounded synchronous loop is sufficient for seven tools and makes the execution path easy to review.
- **Prompt strategy:** a store persona, explicit source/tool routing, missing-information rules and refusal boundaries. Prompt instructions guide language and tool selection; Python enforces authorization and calculations.
- **Short in-memory history:** six completed text turns support follow-up questions without a database. This avoids retaining raw tool records between turns, but older customer facts can be forgotten.

## Run the chatbot

After installation, create the local configuration in PowerShell:

```powershell
if (-not (Test-Path chatbot/.env)) { Copy-Item chatbot/.env.example chatbot/.env }
```

If `chatbot/.env` already exists, edit it without replacing it. Set `OPENAI_API_KEY` locally. This chatbot exclusively uses `gpt-6.1-sol` through the OpenAI Responses API, with `medium` reasoning by default. Other model IDs are rejected. Never commit API keys.

```dotenv
OPENAI_API_KEY=your-local-key
OPENAI_MODEL=gpt-6.1-sol
OPENAI_REASONING_EFFORT=medium
```

Supported reasoning settings and function calling are documented on the [official GPT-6.1 Sol model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol). Account access and quota must be checked with your own key.

```powershell
.\.venv\Scripts\python.exe -m chatbot --check
.\.venv\Scripts\python.exe -m chatbot --trace
.\.venv\Scripts\python.exe -m chatbot --demo-customer-id 3 --trace
```

On macOS/Linux, copy `chatbot/.env.example` to `chatbot/.env` only if no configuration already exists, or export the environment variables directly. Existing environment variables take precedence over `.env`.

On Windows, `./run.ps1 --check` and `./run.ps1 --trace` are optional launchers. `/reset` clears conversation history; `/quit` exits. `--trace` prints tool names only. To test one real request before a longer evaluation:

```powershell
.\.venv\Scripts\python.exe -m chatbot --ask "What are the regular opening hours?" --trace
```

This request consumes API quota. A missing key produces a setup error; HTTP/access/quota failures produce a concise error without printing credentials. The program does not silently switch models.

`--demo-customer-id` simulates a local authenticated session. It is not a production login and must not become a user-selectable web parameter.

## Open the UI

Open [ui/index.html](ui/index.html), or run:

```powershell
py -3 -m http.server 8765 --bind 127.0.0.1 --directory ui
```

Visit `http://127.0.0.1:8765`. The UI uses scripted examples; it is not connected to the chatbot. It does not authenticate customers or call a model.

## How it works

```text
CLI -> Agent.perguntar -> model requests tool -> Tools.executar
    -> validate arguments / check ownership / read data / calculate
    -> return tool result to model -> mask final response -> CLI
```

The model interprets requests and writes replies. Python validates operations, authorizes order access and calculates prices with `Decimal`. Product and order queries use CSV data; policy retrieval selects complete pages by topic from the eight-page PDF. No vector database or agent framework is needed for this small dataset.

Each message is limited to six model rounds and ten tool calls. The first request requires a tool call. The last six completed conversation turns are retained in memory; old tool results are discarded.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s chatbot/tests -v
.\.venv\Scripts\python.exe chatbot/scripts/evaluate.py --offline
```

The suite contains 56 deterministic tests, including source validation, payment boundaries, ownership, partial return inputs, orchestration, CLI behavior and API-format mocks. Passing tests does not establish live-model answer quality. Offline examples use scripted tool choices and reference replies, not model transcripts.

To deliberately run a live evaluation, consuming configured API quota:

```powershell
.\.venv\Scripts\python.exe chatbot/scripts/evaluate.py --live --scenario 01_budget_and_payment
.\.venv\Scripts\python.exe chatbot/scripts/evaluate.py --live
```

Each live run gets its own timestamped folder under ignored `chatbot/private/live-evaluation/`. The script records customer turns, model replies, elapsed time, tool arguments/results, expected review criteria and potential call deviations. A completed run is not a quality pass: manually check factual accuracy, English, source citations, refusal behavior and partial facts. Review flags are prompts for inspection, not an LLM judge or a quality score. Do not present offline references as actual model conversations.

The five scenarios cover: budget/PIX/12-to-6 installments; store information and filtered promotions; authorized tracking; four-turn return clarification; and injection, unauthorized access and an out-of-scope request. Historical experiments with another provider are not evidence for the current model.

## Boundaries and assumptions

- Data are static snapshots, not live stock or carrier updates. Promotion flags have no validity dates.
- Order tools check session ownership and return only permitted fields. Chat claims cannot change identity.
- Returns are provisional assessments. No refunds, orders, payments or support cases are created.
- The highest active product promotion applies once; PIX does not stack. Quotes exclude shipping and provide exact installment amounts whose sum equals the total.
- The PDF contains conflicting contacts and installment summaries, and leaves shipping at exactly BRL 500 undefined. Staff must confirm ambiguities; quotes follow detailed section 3.1.
- Actual receipt dates, purchase channel and warranty certificates are absent. The assistant asks for missing facts and does not infer receipt from delivery estimates.
- Store hours use `America/Campo_Grande`; no holiday calendar is supplied.
- Demo customer data are anonymized. Pattern masking is additional protection and does not recognize every possible personal detail.
- Input files are checked for duplicate IDs, category/product/order/customer references, product prices/stock/specifications and promotion ranges. Policy retrieval expects eight readable pages; matching page count alone cannot detect a changed manual, so topic mappings still require review.
- Tool validation does not prove that model arguments came from the customer, nor that final wording accurately reflects results. The return conversation checks specifically flag invented receipt/channel/condition arguments; live answer review remains necessary.

## Delivery and next priorities

The highest-priority remaining validation is one successful API smoke test followed by the five live scenarios and manual review. After that: replace the local identity simulation with verified application sessions, keep confirmed return facts per order, and connect real store/carrier data if required. UI integration is optional for this challenge; the CLI keeps the main flow easy to review.

To rebuild a source archive from the explicit public-file allowlist:

```powershell
.\.venv\Scripts\python.exe chatbot/scripts/package_case.py
```

The ZIP and SHA-256 manifest are saved under ignored `chatbot/private/entrega-final/`. They exclude `.env`, private source originals, local notes and live logs. The archive is a convenience; the challenge still requests a public GitHub repository with genuine commit history. No public repository/submission is created by this command. Do not fabricate prior commits or change the repository after submission.

## AI assistance

I used OpenAI Codex to generate and revise substantial parts of the implementation, tests and documentation. I supplied the challenge, selected the model based on familiarity, prioritized deterministic tools and a small structure, and reviewed the agent/tool flow interactively, including argument types, extra fields, stock checks and session ownership. Codex also ran the offline checks. This assistance does not substitute for live-model evaluation; I distinguish the verified Python behavior from model behavior that remains to be measured.
