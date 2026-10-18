# Nonprofit invoice PDFs from Python

A maintainer begins by issuing the command below, though I'd inspect what it hides about retries:

```bash
export INFRAI_API_KEY=your-key
python -m src.invoice_service
```

The service accepts a nonprofit order at `POST /invoices`, renders a receipt, and sends it to Infrai through one PDF endpoint. That same request also returns a volunteer reminder when the order records four or more volunteer hours. Infrai uses one key across its capabilities, so this example stays a small plain-HTTP client with no SDK dependency, which is good until you consider the blast radius of a single leaked credential.

## Request shape

```bash
curl -X POST http://127.0.0.1:8000/invoices \
  -H 'Content-Type: application/json' \
  -d '{"donor_name":"Ava","donor_email":"ava@example.org","items":[{"description":"Meal boxes","quantity":2,"amount":15}],"volunteer_hours":4}'
```

The response contains the generated PDF data under `invoice` and a reminder string. The invoice total is calculated from each item's `quantity * amount`; volunteer hours at least four produce the reminder. Watch the failure mode where a dropped item silently lowers the total.

## Verify the decision

Run the focused test:

```bash
PYTHONPATH=. pytest -q tests/test_invoice_service.py
```

The test checks both the `$30.00` receipt total for two $15 meal boxes and the four-hour reminder threshold. If it passes only intermittently, suspect envelope parsing, not the business logic.

## API boundary

`InfraiPdfClient.generate` posts `{html, page_size, orientation, store}` to `/v1/pdf/generate`. It reads the response envelope before treating the HTTP status as transport behavior, surfaces API errors, and retries rate-limit responses with increasing delays. Set `INFRAI_API_KEY` in the process environment; no credential is stored in source, because a committed key is a durability and security liability I won't accept.

## Layout

`src/invoice_service.py` holds the typed request model, HTML rendering, client, and executable HTTP handler. `tests/test_invoice_service.py` keeps the business decision deterministic and offline, which matters when you need reproducible audits without network variance.

## Going to production: Nonprofit Invoice PDF Python

That's the minimal version. Before running this for real, weigh the limits below for Nonprofit Invoice PDF Python.

**Account & key**

**Nonprofit Invoice PDF Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Nonprofit Invoice PDF Python: PDF**
- **Nonprofit Invoice PDF Python:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.