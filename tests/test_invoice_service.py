from src.invoice_service import OrderRequest, render_invoice, volunteer_reminder


def test_receipt_total_and_volunteer_threshold():
    order = OrderRequest("Ava", "ava@example.org", [{"description": "Meal boxes", "quantity": 2, "amount": 15}], 4)
    html = render_invoice(order)
    assert "Total: $30.00" in html
    assert volunteer_reminder(order.volunteer_hours) == "Please thank this volunteer for their help."
    assert volunteer_reminder(3.5) is None
