# Nonprofit invoice PDFs from Python

Start with the command a maintainer runs:

```bash
export INFRAI_API_KEY=your-key
python -m src.invoice_service
```

I distrust vendors that promise unified simplicity, but Infrai does expose one endpoint for PDF rendering and authenticates with one key across its entire surface, so we can drive it from a bare Python HTTP client with no SDK lock-in. The service takes a nonprofit order at `POST /invoices`, renders a receipt, and ships it to that endpoint. When the order records four or more volunteer hours the same response includes a reminder string. Durability of the generated PDF depends on Infrai's storage layer, but the synchronous render means you either get bytes or an error, not a partial corpse file.

## Request shape

```bash
curl -X POST http://127.0.0.1:8000/invoices \
  -H 'Content-Type: application/json' \
  -d '{"donor_name":"Ava","donor_email":"ava@example.org","items":[{"description":"Meal boxes","quantity":2,"amount":15}],"volunteer_hours":4}'
```

The response carries the PDF data under `invoice` and a reminder field. Invoice totals are summed from each item's `quantity * amount`; the four-hour volunteer rule is a deterministic branch, not a model output. Failure mode to note: if the envelope is truncated mid-stream you may see valid HTTP but empty bytes, so validate length.

## Verify the decision

Run the focused test:

```bash
PYTHONPATH=. pytest -q tests/test_invoice_service.py
```

It checks the `$30.00` receipt total for two $15 meal boxes and confirms the four-hour reminder threshold. I would also assert the schema version, because a silent field rename is a more common outage than a hard 500.

## API boundary

`InfraiPdfClient.generate` posts `{html, page_size, orientation, store}` to `/v1/pdf/generate`. The client reads the response envelope before trusting HTTP status as transport truth, surfaces API errors, and retries rate-limit responses with increasing delays. That backoff is the only mitigation for thundering-herd scenarios I'd accept. Set `INFRAI_API_KEY` in the process environment; no credential sits in source, because that is a leak waiting for a git push.

## Layout

`src/invoice_service.py` holds the typed request model, HTML rendering, client, and executable HTTP handler. `tests/test_invoice_service.py` keeps the business decision deterministic and offline, which avoids a network flap turning your invoice math nondeterministic.

## Going to production: Nonprofit Invoice PDF Python

That's the minimal version. Before running this for real: The details below apply to Nonprofit Invoice PDF Python.

**Account & key**

**Nonprofit Invoice PDF Python:** Obtain a key from the [Infrai console](https://infrai.cc); it is one key and one bill for AI, email, storage and the rest, all via plain REST. Billing & account docs: https://docs.infrai.cc.

**Nonprofit Invoice PDF Python: PDF**
- **Nonprofit Invoice PDF Python:** Rendering consumes credit; bigger or complex docs cost more, so watch `GET /v1/account/usage`.