from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from worker.tasks.tickets import _build_email_html, _make_ticket_token


def _fake_order():
    order = SimpleNamespace(id=42, idempotency_key=uuid4(), total_price="375.00")
    show = SimpleNamespace(
        movie=SimpleNamespace(title="Dune: Part Two"),
        hall=SimpleNamespace(name="IMAX Hall"),
        start_time=datetime(2026, 7, 9, 20, 52),
    )
    order.tickets = [
        SimpleNamespace(
            id=1,
            price="150.00",
            show=show,
            seat=SimpleNamespace(row_number=3, seat_number=6),
        ),
        SimpleNamespace(
            id=2,
            price="225.00",
            show=show,
            seat=SimpleNamespace(row_number=4, seat_number=5),
        ),
    ]
    return order


def test_ticket_token_is_deterministic():
    order = _fake_order()
    ticket = order.tickets[0]
    assert _make_ticket_token(ticket, order) == _make_ticket_token(ticket, order)


def test_different_tickets_produce_different_tokens():
    order = _fake_order()
    t1 = _make_ticket_token(order.tickets[0], order)
    t2 = _make_ticket_token(order.tickets[1], order)
    assert t1 != t2


def test_token_is_hex_sha256():
    order = _fake_order()
    token = _make_ticket_token(order.tickets[0], order)
    assert len(token) == 64
    int(token, 16)  # raises if not hex


def test_email_html_contains_order_details():
    html = _build_email_html(_fake_order())
    assert "Dune: Part Two" in html
    assert "Order #42" in html or "order #42" in html
    assert "375.00 UAH" in html
    # inline QR images referenced by cid
    assert "cid:qr1" in html and "cid:qr2" in html


def test_email_html_escapes_titles():
    order = _fake_order()
    order.tickets[0].show.movie.title = "<script>x</script>"
    html = _build_email_html(order)
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html
