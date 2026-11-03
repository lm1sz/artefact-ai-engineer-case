# Empório da Música

A Python customer-service agent for Artefact's AI Engineer challenge. It helps customers find instruments, consult store policies, calculate payment quotes and check authorized orders using the supplied CSV files and policy PDF.

## Run the project

Python 3.11+ is required. From the repository root on Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements.lock -e .
Copy-Item chatbot/.env.example chatbot/.env
```

Copy the example only when no local `.env` exists. Set your own key in `chatbot/.env` or in the environment:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your-local-openai-key
OPENAI_MODEL=gpt-6.1-sol
OPENAI_REASONING_EFFORT=medium
```

The default is OpenAI `gpt-6.1-sol` through the Responses API. Environment variables take precedence over `.env`; credentials stay on the Python side and must not be committed. Access and quota depend on the evaluator's account.

```powershell
.\.venv\Scripts\python.exe -m chatbot --check
.\.venv\Scripts\python.exe -m chatbot --trace
.\.venv\Scripts\python.exe -m ui.server --port 8765
```

For the UI, open http://127.0.0.1:8765. `/reset` clears CLI history and `/quit` exits. The UI's “Nova conversa” button resets browser-session history. `--trace` prints tool names only. On macOS/Linux, use `python3 -m venv .venv` and `.venv/bin/python` instead of the Windows Python path. Installation needs package-index access; source checks and tests need no API key.

Sessions are guests by default. Add `--demo-customer-id 3` to the CLI or UI command to simulate the authorized customer for order 1. This is a developer-selected demonstration identity, not a production login. Chat messages and browser parameters cannot change it.

## Organization

```text
chatbot/                 Agent, providers, source queries and business rules
  data/                  Anonymized CSVs and the source policy PDF
  examples/demonstrations Three reviewed English conversations and tool evidence
  scripts/               Evaluation, demonstration capture and packaging
  tests/                 Chatbot and provider tests
ui/                      Local server and browser interface
  tests/                 HTTP, session and access-control tests
```

The CLI runs the chatbot directly. The UI is a separate package that imports the same Agent and Tools; it adds no alternative business logic. See [UI instructions](ui/README.md).

## Why this approach

The model interprets the customer's message and proposes a tool call. Python validates the tool name, argument fields, types and ranges before querying data or applying a rule. A small function-calling loop is enough for seven tools, without an agent framework or database.

CSV filtering handles the structured dataset directly, including promotions across the complete catalog before applying a display limit. Policy topics map to complete pages of the eight-page PDF. This makes sources easy to inspect; page mappings need review if the manual changes.

The prompt defines the store's tone, when to consult each source, language preferences, scope and missing-information rules. Source text is treated as data, never as permission to bypass checks. The last six completed conversation turns stay in memory; failed replies are not added. Reset preserves identity and access-denial state. Each turn is bounded to six model rounds and ten tool calls.

Catalog replies present structured specifications directly. A wood species does not imply solid construction, tone or durability. Marketing descriptions remain searchable locally but are omitted from model payloads. Payment replies use Python's exact cent amounts. This standardized presentation can require a follow-up for mixed requests.


## Rules and limitations

Availability requires active status and positive stock. The highest active promotion applies once; PIX does not stack. Quotes exclude shipping and require staff confirmation. For BRL 599.90 in six installments, the exact schedule is two payments of BRL 99.99 and four of BRL 99.98. Twelve payments fail the applicable minimum; the customer chooses another count.

Order access requires a matching application-session identity. A claim of administrator status grants nothing. Return assessment keeps receipt date, purchase channel and complete condition unknown until confirmed. Having the box alone is insufficient; estimated delivery is not receipt. The agent does not issue payments, refunds, orders or support tickets.

The manual has conflicting contact details and installment summaries, and leaves shipping at exactly BRL 500 undefined. Those ambiguities require staff clarification; payment quotes use detailed section 3.1. Data are static snapshots, not live stock/carrier information. Hours use Campo Grande local time, without a holiday calendar.

The model still selects tools and interprets customer facts. Type validation does not prove that a proposed fact follows the customer's words. Portuguese/English hints and the specific recipe-offer guard are heuristic. Production authentication, persistent confirmed return facts and broader free-form conversation evaluation are future work.

## Reviewed conversations

- [Catalog and installments](chatbot/examples/demonstrations/01_catalog_and_installments.md)
- [Return clarification](chatbot/examples/demonstrations/02_return_clarification.md)
- [Privacy and store information](chatbot/examples/demonstrations/03_privacy_and_store.md)

Execution method: ChatGPT-mediated model turns with local Python tools. Eight completed customer turns execute nine real tool calls through the same Agent, schemas, ownership checks, history and checked presentation. Final outputs are preserved verbatim; [evidence.json](chatbot/examples/demonstrations/evidence.json) contains exact arguments/results, source hashes and session context. The return example uses simulated customer 3; the others use guests. The capture method and OpenAI deployment target are recorded separately.

To repeat the capture workflow, run `python chatbot/scripts/interactive_demo.py --output chatbot/private/new-demo`. For each request-NNN.json, the interactive model receives its instructions, items and tool schemas; the operator saves response-NNN.json in the Agent provider protocol. Python then executes requested tools and continues. Normal CLI/UI execution uses the configured API provider.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s chatbot/tests -v
.\.venv\Scripts\python.exe -m unittest discover -s ui/tests -v
.\.venv\Scripts\python.exe chatbot/scripts/evaluate.py --offline
# Uses the configured API and its quota:
.\.venv\Scripts\python.exe chatbot/scripts/evaluate.py --live
```

The local suite covers data validation, payment/promotion boundaries, grounding, returns, privacy, history, provider protocol and HTTP sessions. Provider tests use simulated responses. The OpenAI adapter's continuation/tool protocol is tested; evaluator-specific access is checked with their key. Source checks do not establish API connectivity or conversational quality.

Offline evaluation uses scripted calls and reference wording, explicitly labeled and saved under ignored `chatbot/private/offline-evaluation/`. API evaluations save separate timestamped traces and input hashes under `chatbot/private/live-evaluation/`. Review wording and exact arguments; automatic call flags are inspection prompts, not quality scores.

`python chatbot/scripts/package_case.py` creates an allowlisted source ZIP and SHA-256 manifest under ignored `chatbot/private/entrega-final/`. It excludes keys, original customer files, private traces and temporary environments. Credential-pattern checks add protection but are not a universal secret detector.

## AI assistance and submission

I used OpenAI Codex to help implement and revise code, investigate failures, write tests and prepare documentation and demonstrations. My inputs included the challenge requirements, provider choice, operational rules and interactive review of the tool flow. The repository distinguishes completed tool execution, protocol tests and the demonstration capture method.
