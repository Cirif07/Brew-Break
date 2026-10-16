"""Cashless payment: a QR code to scan, a "checking" step, and the successful / unsuccessful / failed screens.

DEMO MODE: no real payment provider is connected. With BIZ["demoPayments"] = True the QR is a sample and the
"Scan to pay" screen has a dropdown to choose the result. Set it to False in data.py and "I have paid" reports
"payment checking is not connected yet" until a real provider check is added in pay_verify().
"""
import asyncio
import math

from pyscript import document, window
from pyodide.ffi import create_proxy

import cart
import dialogs
import orders
from data import BIZ, SLOTS
from state import S, esc, icon, later, peso, q, qa

PAY_SECONDS = 300
STATUS = {"ok": ("st-ok", "#dfe8d3", "#36502a"), "warn": ("st-warn", "#f6e6c8", "#7a5a12"), "fail": ("st-fail", "#f6dfd3", "#8f3223")}


# ---------------------------------------------------------------- the QR code
def qr_svg(text):
    """Draw a QR code as an SVG using the qrcode-generator library loaded in index.html. Returns '' if it could not load."""
    try:
        qr = window.qrcode(0, "M")
        qr.addData(text)
        qr.make()
        n = qr.getModuleCount()
        cells = "".join(f"M{c} {r}h1v1h-1z" for r in range(n) for c in range(n) if qr.isDark(r, c))
    except Exception:
        return ""
    return (f'<svg viewBox="-4 -4 {n + 8} {n + 8}" role="img" aria-label="QR code to pay" shape-rendering="crispEdges">'
            f'<rect x="-4" y="-4" width="{n + 8}" height="{n + 8}" fill="#fff"/><path d="{cells}" fill="#2b1e17"/></svg>')


# ---------------------------------------------------------------- finishing
def finish_order():
    """Place the order, then show the success screen."""
    orders.commit_order()
    status_dialog("ok")


def choose_cart():
    """Switch to Pay at the cart and place the order."""
    S["pay"] = "cart"
    for b in qa("#pay button"):
        b.setAttribute("aria-pressed", str(b.getAttribute("data-p") == "cart").lower())
    finish_order()


def focus_confirm():
    b = q("#place")
    if b:
        b.focus()


# ---------------------------------------------------------------- "Scan to pay" screen
def open_pay_dialog(*_):
    if not S["pay_ref"]:
        S["pay_ref"] = orders.new_ref()
    ref, amount = S["pay_ref"], cart.due()
    qr = qr_svg(f"brewbreak:pay?ref={ref}&amount={amount:.2f}&cur=PHP")
    box = qr or '<p class="qrfail">The QR code could not load. You can still pay at the cart.</p>'
    demo = ""
    if BIZ["demoPayments"]:
        demo = ('<div class="demo">Demo mode: this QR is a sample and no real payment is taken.<label>What should happen when you tap I have paid?'
                '<select id="demoRes"><option value="ok">The payment goes through</option><option value="warn">The payment is not completed</option>'
                '<option value="fail">Something goes wrong</option></select></label></div>')

    def shut():
        dialogs.close_dialog()
        focus_confirm()

    def clicked(event):
        t = event.target
        if t.id == "dlg" or t.closest("[data-x]"):
            shut()
        elif t.closest("[data-cart]"):
            dialogs.close_dialog()
            choose_cart()
        elif t.closest("[data-ok]"):
            sel = q("#demoRes")
            pick = sel.value if sel else "ok"
            dialogs.close_dialog()
            asyncio.ensure_future(pay_verify(pick))

    dialogs.show_dialog(f'''<div class="dlg paydlg" role="dialog" aria-modal="true" aria-labelledby="dT"><h3 id="dT">Scan to pay {peso(amount)}</h3>
<p class="refline">Reference <b>{esc(ref)}</b> · expires in <b id="cd">5:00</b></p><div class="qrbox">{box}</div>
<ol class="howto"><li>Open GCash, Maya or your bank app.</li><li>Choose Scan QR and scan this code.</li><li>Confirm the amount, then come back and tap I have paid.</li></ol>{demo}
<div class="dact"><button class="btn ghost" type="button" data-x>Cancel</button><button class="btn pri" type="button" data-ok {"" if qr else "disabled"}>I have paid</button></div>
<button class="vlink" type="button" data-cart style="margin-top:14px">Pay at the cart instead</button></div>''',
                        clicked, on_escape=shut, focus_selector="[data-ok]:not([disabled])")
    # The countdown watches the real clock, so a sleeping phone cannot keep an expired code alive.
    end = window.Date.now() + PAY_SECONDS * 1000

    def tick():
        left = max(0, math.ceil((end - window.Date.now()) / 1000))
        cd = q("#cd")
        if cd:
            cd.textContent = f"{left // 60}:{left % 60:02d}"
        if left <= 0:
            dialogs.close_dialog()
            status_dialog("warn", reason="expired")
    dialogs.set_timer(window.setInterval(create_proxy(tick), 1000))


# ---------------------------------------------------------------- checking step + result screens
def pay_checking():
    dialogs.show_dialog('''<div class="dlg stdlg" role="alertdialog" aria-modal="true" aria-labelledby="dT" aria-busy="true" tabindex="-1">
<div class="spin" aria-hidden="true"></div><h3 id="dT">Checking your payment…</h3><p id="dB" style="margin-bottom:6px">This usually takes a few seconds. Please keep this page open.</p></div>''',
                        lambda event: None, on_escape=lambda: None, focus_selector=".dlg")


async def pay_verify(pick):
    """Wait for the payment result. In demo mode the result is the one chosen in the dropdown."""
    pay_checking()
    try:
        await asyncio.sleep(1.7)
        if not BIZ["demoPayments"]:
            raise RuntimeError("payment checking is not connected yet")
        result = pick
    except Exception as err:
        status_dialog("fail", message=str(err))
        return
    if result == "ok":
        finish_order()
    else:
        status_dialog("warn" if result == "warn" else "fail")


def status_dialog(kind, reason="", message=""):
    """Successful (green), not completed (amber) or failed (red). Same look as the logout and delete confirmations."""
    order = S["order"]
    ok = kind == "ok" and order
    ref = order["id"] if ok else (S["pay_ref"] or "BB-----")
    amount = order["total"] if ok else cart.due()
    symbol, bg, fg = STATUS[kind]

    def row(a, b):
        return f"<div><span>{a}</span><b>{b}</b></div>"
    if ok:
        cashless = order["paid"]
        slot = next((s for s in SLOTS if s["id"] == order["slot"]), None)
        demo = BIZ["demoPayments"]
        title = ("Demo payment complete" if demo else "Payment received") if cashless else "Order placed"
        body = ((f"This is a demonstration, so no real {peso(amount)} was taken. Your sample order is in the queue." if demo
                 else f"We received your {peso(amount)}. Your order is in the queue and we will call your name when it is ready.") if cashless
                else f"Pay {peso(amount)} at the cart when you collect your order, in cash or with another payment method.")
        pickup = ("Pick up now" if slot["id"] == "now" else slot["n"]) if slot else ""
        rows = (row("Amount", peso(amount)) + row("Reference", esc(ref)) + row("Pickup", esc(pickup))
                + row("Payment", ("Cashless (sample QR, demo)" if demo else "Cashless (QR code)") if cashless else "At the cart"))
        if order["vissued"]:
            body += " You also earned a free drink voucher. It is waiting in your wallet."
            actions = ('<button class="btn ghost" type="button" data-go="#/vouchers">See my voucher</button>'
                       '<button class="btn pri" type="button" data-x>View my order</button>')
        else:
            actions = ('<button class="btn ghost" type="button" data-go="#/menu">Order more</button>'
                       '<button class="btn pri" type="button" data-x>View my order</button>')
    else:
        if kind == "warn":
            title = "Payment not completed"
            body = ("The QR code expired before we received a payment. " if reason == "expired" else "We did not receive your payment. ") \
                   + "You have not been charged and your bag is still saved."
        else:
            title = "Something went wrong"
            extra = f" ({esc(message)})" if message else ""
            body = ("This is the demo's simulated failure. No money was taken and nothing has been ordered." if BIZ["demoPayments"] else
                    f"We could not check your payment{extra}. If money left your account, keep your reference and show it at the counter. "
                    "Nothing has been ordered yet.")
        rows = row("Amount", peso(amount)) + row("Reference", esc(ref))
        actions = ('<button class="btn ghost" type="button" data-cart>Pay at the cart instead</button>'
                   '<button class="btn pri" type="button" data-retry>Try again</button>')
    close_link = "" if ok else '<button class="vlink" type="button" data-x style="margin-top:14px">Close</button>'

    def shut():
        dialogs.close_dialog()
        app = q("#app")
        if app:
            app.focus()

    def clicked(event):
        t = event.target
        go = t.closest("[data-go]")
        if t.id == "dlg" or t.closest("[data-x]"):
            shut()
        elif go:
            shut()
            window.location.hash = go.getAttribute("data-go")
        elif t.closest("[data-retry]"):
            dialogs.close_dialog()
            open_pay_dialog()
        elif t.closest("[data-cart]"):
            dialogs.close_dialog()
            choose_cart()

    def refocus():                           # the page change that follows an order would otherwise steal focus
        target = q("#dlg .pri") or q("#dlg button")
        if target:
            target.focus()
    later(refocus, 100)
    dialogs.show_dialog(f'''<div class="dlg stdlg" role="alertdialog" aria-modal="true" aria-labelledby="dT" aria-describedby="dB">
<div class="stico" style="background:{bg};color:{fg}">{icon(symbol)}</div><h3 id="dT">{title}</h3><p id="dB">{body}</p><div class="sdet">{rows}</div>
<div class="dact">{actions}</div>{close_link}</div>''', clicked, on_escape=shut, focus_selector=".pri")
