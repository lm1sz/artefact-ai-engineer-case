# Empório da Música — Technical Case Summary

## Problem and scope

The prototype helps customers choose musical instruments within a budget, consult store policies, calculate payment quotes and check authorized orders. It also provides provisional return guidance when the supplied data are incomplete.

The implementation uses Python and the challenge's anonymized CSV files and policy PDF. The configured model is exclusively GPT-6.1 Sol, selected based on my familiarity with its everyday use rather than a project-specific benchmark. The agent interface is a CLI; the separate web UI is a scripted visual prototype. The intended business benefit is to answer repetitive questions and prepare grounded guidance for staff; no support-time reduction has been measured.

## Alignment with the challenge

| Requirement | Implementation and evidence | Status |
| --- | --- | --- |
| Python text agent | CLI, bounded agent loop, seven tools; mocked provider round-trip tests | Implemented; live validation pending |
| Store persona and grounded answers | Prompt routes operational facts to CSV tools and policies to PDF pages | Implemented; final wording needs live review |
| Out-of-scope handling | Prompt redirects; scenario 5 combines an unrelated request and forged access | Backend denial tested; language behavior pending |
| Explain technical decisions | Root README and this document | Included |
| Three to five conversations, including policy application | Five reference conversations, 13 turns; matching live evaluation runner | References included; actual GPT conversations pending |
| Public repository with genuine progress | Source package and reproducible commands prepared | GitHub publication/history pending |

The reference conversations are review aids, not a claim that the actual-model conversation deliverable is complete.

## Design

```text
Customer -> CLI -> Agent -> model requests a tool
                       -> Python validates and executes the request
                       -> model receives source results and writes the reply
```

The model interprets language, selects tools and composes answers. Python enforces allowed operations, argument validation, order ownership and monetary calculations. This separation keeps the implementation small and makes operational rules independently testable.

Seven tools cover product search, promotions, product details, policy retrieval, order lookup, return assessment and payment quotes. Structured records are queried directly. The eight-page policy PDF is retrieved through explicit topic-to-page mappings. This dataset does not require a vector database or an agent framework.

## Business rules and data boundaries

- Product availability requires active status and positive stock. Promotion discovery checks the complete catalog before filtering and limiting results.
- The highest active product promotion applies once. PIX does not stack with promotions. Active flags are snapshot facts, not proof of current campaign validity.
- Prices use `Decimal`. Payment quotes validate stock and installment rules and exclude shipping.
- Exact installments are computed in integer cents: divide the total by the number of payments and distribute remaining cents. Their sum equals the quote total, and amounts differ by at most one cent.
- When a requested credit installment count fails the minimum, Python returns the maximum supported count. It does not change the customer's payment choice or charge anything. For BRL 599.90, twelve installments fail and six are supported.
- Order tools require a matching application-session identity and expose only permitted fields. A chat claim cannot change identity. The CLI identity flag is a local simulation, not production authentication.
- Return assessments ask for missing receipt date, purchase channel and condition. An estimated delivery date is not actual receipt. Assessments require staff confirmation and never issue refunds.

For example, BRL 599.90 in six installments becomes two payments of BRL 99.99 and four of BRL 99.98. The Python calculation supplies these exact amounts to the model.

## Handling partial return information

Unknown facts remain `null`. The existing condition field combines unused/original condition, packaging and included items. Having the box alone does not confirm that field: the assistant should ask about the remaining conditions without repeating confirmed information.

This approach deliberately preserves the current small interface. Facts are still interpreted by the model from recent conversation text; Python validates their types and date consistency, not the truth of arbitrary customer statements or model-supplied arguments. Structured, confirmed facts linked to a session and order are a future improvement.

## Validation and evidence

The current suite contains 56 passing deterministic tests covering source validation, business rules, exact installment totals and minimums, partial return arguments, authorization, privacy, agent orchestration, CLI behavior, evaluation exports and the OpenAI request/continuation format. The five offline reference scenarios cover 13 customer turns and run without an API key or valid model configuration.

Reference conversations use scripted tool choices and reference wording. Chat-assisted simulations use actual tools but manual interpretation and response writing. Neither is an end-to-end GPT-6.1 evaluation.

Historical live Gemini conversations are retained separately and explicitly identified. GPT-6.1 live validation remains pending because no local OpenAI API key is available. No GPT-6.1 quality, latency or cost claim is made.

## Deliberately deferred

Production authentication, persistent structured return state, separate condition subfields, UI/backend integration and live store/carrier adapters are outside this prototype's current scope. No payment, order mutation, refund or support-ticket creation is implemented.

The policy source contains conflicting contact details and installment summaries. Quotes follow detailed section 3.1 and remain subject to staff confirmation. The implementation does not make legal determinations.

## Reproduction and review

Install and run using the root README. No API is needed for source checks or tests:

```powershell
python -m chatbot --check
python -m unittest discover -s chatbot/tests -v
python chatbot/scripts/evaluate.py --offline --output chatbot/private/case-review
```

Read the core modules in this order: `cli.py`, `agent.py`, `tools.py`, `data.py`, `providers.py`, then `prompt.txt`. For a demonstration, show a product/payment quote, an unauthorized order denial and a return request with missing facts.

Before claiming the current model meets the challenge's conversational requirements, run and review actual GPT-6.1 conversations. Offline references should remain explicitly labeled if included in a submission.

For live evaluation, set the API key locally and run `python chatbot/scripts/evaluate.py --live`. Each run preserves separate evidence with timings and tool arguments/results. The payment scenario checks whether "Six, then" retains the selected product; the return scenario checks whether "I still have the box" leaves incomplete condition facts unknown. Call deviations are review flags; final answer accuracy and language are reviewed manually.

Release criteria: the offline suite passes; all five live scenarios complete; prices and installment totals match tools; no unauthorized order details appear; unknown return facts remain unknown; policy answers cite the relevant source and acknowledge ambiguities; replies use the requested language. Fix issues and rerun affected scenarios before treating the live transcripts as submission evidence. Current live-model status remains pending.

## AI assistance

I used OpenAI Codex for substantial implementation, test generation, documentation and offline verification. My inputs included the model choice, tool-based operational rules, a simplified chatbot/UI structure and interactive review of the core execution flow. I distinguish AI-generated reference wording, deterministic test results and actual live-model evidence. The last category is still pending for GPT-6.1 Sol.
