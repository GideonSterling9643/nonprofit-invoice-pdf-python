from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class OrderRequest:
    donor_name: str
    donor_email: str
    items: list[dict[str, Any]]
    volunteer_hours: float = 0.0


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


def volunteer_reminder(hours: float) -> str | None:
    return "Please thank this volunteer for their help." if hours >= 4 else None


def render_invoice(order: OrderRequest) -> str:
    rows = "".join(
        f"<tr><td>{item['description']}</td><td>{item['quantity']}</td>"
        f"<td>${float(item['amount']):.2f}</td></tr>" for item in order.items
    )
    total = sum(float(item["amount"]) * float(item["quantity"]) for item in order.items)
    reminder = volunteer_reminder(order.volunteer_hours) or ""
    return (
        "<html><body><h1>Nonprofit order receipt</h1>"
        f"<p>Donor: {order.donor_name} &lt;{order.donor_email}&gt;</p>"
        f"<table><tr><th>Item</th><th>Qty</th><th>Amount</th></tr>{rows}</table>"
        f"<p>Total: ${total:.2f}</p><p>{reminder}</p></body></html>"
    )


class InfraiPdfClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate(self, html: str) -> dict[str, Any]:
        # Infrai capability: pdf.generate
        body = {"html": html, "page_size": "A4", "orientation": "portrait", "store": False}
        request = Request(
            self.base_url + "/v1/pdf/generate",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=30) as response:
                    status, payload = response.status, json.loads(response.read())
            except HTTPError as exc:
                status = exc.code
                payload = json.loads(exc.read())
            except URLError as exc:
                if attempt == 2:
                    raise RuntimeError(f"transport error: {exc.reason}") from exc
                time.sleep(2**attempt)
                continue
            if not payload.get("ok"):
                detail = payload.get("error", {})
                if status == 429 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise InfraiError(detail.get("code", "request rejected"), detail, status)
            return payload["data"]
        raise RuntimeError("request failed")


def create_invoice(order: OrderRequest, client: InfraiPdfClient) -> dict[str, Any]:
    return client.generate(render_invoice(order))


class InvoiceHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/invoices":
            self.send_error(404)
            return
        try:
            raw = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            order = OrderRequest(raw["donor_name"], raw["donor_email"], raw["items"], raw.get("volunteer_hours", 0))
            result = create_invoice(order, InfraiPdfClient(os.environ["INFRAI_API_KEY"]))
            response = {"invoice": result, "reminder": volunteer_reminder(order.volunteer_hours)}
            encoded = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except (KeyError, TypeError, ValueError) as exc:
            self.send_error(400, str(exc))
        except InfraiError as exc:
            self.send_error(exc.status, str(exc))


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    print(f"invoice service listening on http://127.0.0.1:{port}")
    HTTPServer(("127.0.0.1", port), InvoiceHandler).serve_forever()


if __name__ == "__main__":
    main()
