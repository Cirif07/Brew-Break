"""Checkout page: pickup time, who is picking up, payment method, and the order summary.

Event flow: every button here carries a data-act name (cslot, cpay, qty, place ...). main.py's single click
listener calls the matching function below, which updates S and redraws the summary.
"""
import re

import cart
import payments
from data import NORM_PAY, PAY, SLOTS
from state import S, esc, icon, peso, q, qa, toast
from views_browse import coming_soon

PH_MOBILE = re.compile(r"(\+?63|0)9\d{9}")


def pressed(flag):
    return str(bool(flag)).lower()


# ---------------------------------------------------------------- "same as last time" offers (never preselected)
def sug_slot():
    sl = next((x for x in SLOTS if x["id"] == cart.load_prefs().get("slot")), None)
    if sl and not S["slot"]:
        return f'<button type="button" class="sugg" data-act="sslot" data-id="{sl["id"]}">{icon("timer")}Same as last time: {esc(sl["n"])}</button>'
    return ""


def sug_pay():
    saved = cart.load_prefs().get("pay")
    p = next((x for x in PAY if x[0] == NORM_PAY.get(saved, saved)), None)
    if p and not S["pay"]:
        return f'<button type="button" class="sugg" data-act="spay" data-id="{p[0]}">{icon("check")}Same as last time: {esc(p[1])}</button>'
    return ""


# ---------------------------------------------------------------- summary (right column, and the sticky bar on phones)
def summary_html():
    total = cart.due()
    sl = next((s for s in SLOTS if s["id"] == S["slot"]), None)
    when = ("Pick up now" if sl["id"] == "now" else "Pickup " + sl["t"]) if sl else "Choose a pickup window to continue"
    rows = "".join(cart.line_html(x, i) for x, i in enumerate(S["cart"]))
    voucher = f'<div class="ln"><span>Voucher</span><span>−{peso(cart.disc())}</span></div>' if cart.disc() else ""
    n = cart.stamp_qty(S["cart"])
    if S["acct"]:
        stamps = f'This order adds {n} stamp{"" if n == 1 else "s"} to your card{" (bakes earn no stamps)" if n < cart.count() else ""}.'
    else:
        stamps = ('Stamps are for account holders. <a class="lnk" href="#/login">Log in</a> or <a class="lnk" href="#/register">create an account</a> '
                  'to earn stamps. If you sign up right after ordering, we will add the stamps from this order too.')
    return f'''<h3>Your bag</h3><p style="color:var(--mut);font-size:14px">{when}</p>{rows}
{cart.voucher_block()}<div style="margin-top:14px"><div class="ln"><span>Subtotal · {cart.count()} item{"" if cart.count() == 1 else "s"}</span><span>{peso(cart.sub())}</span></div>{voucher}<div class="ln t"><span>Total</span><span>{peso(total)}</span></div></div>
<button class="btn acc" id="place" data-act="place">Confirm pre-order · {peso(total)}</button><p class="fine">{stamps}</p>
<p class="fine demo-note"><b>Demo checkout.</b> No real payment is taken and nothing is sent to a shop. Your bag, order and account are saved only in this browser.</p>'''


def wire_summary():
    """Redraw the summary and the sticky bar. Other modules call this through cart.HOOKS['sum']."""
    q("#sum").innerHTML = summary_html()
    bar = q("#sbar")
    if bar:
        bar.innerHTML = (f'<div><small>Total</small><b>{peso(cart.due())}</b></div>'
                         '<button class="btn acc" id="place2" type="button" data-act="place">Confirm pre-order</button>')


# ---------------------------------------------------------------- the page
def checkout(arg=""):
    if not S["cart"]:
        return ('<div class="wrap"><div class="empty" style="padding:120px 0"><h2>Your bag is empty</h2><p>Add a drink first, then come back to choose your pickup time and pay.</p>'
                '<a class="btn pri" href="#/menu">Browse the menu</a></div></div>')
    if not S["acct"] and not S["user"].get("nick"):
        saved = cart.load_prefs().get("nick")
        if saved:
            S["user"]["nick"] = saved
    u = S["user"]
    slots = "".join(
        f'<button class="slot" data-act="cslot" aria-pressed="{pressed(s["id"] == S["slot"])}" data-s="{s["id"]}"><span>{s["n"]}</span><em>{s["q"]}</em><small>{s["t"]} · {s["m"]}</small></button>'
        for s in SLOTS)
    if S["acct"]:
        who = f'''<section><h3><i>02</i>Who is picking up</h3><div class="field"><label for="f-name">Full name</label><input id="f-name" name="name" value="{esc(u.get("name", ""))}" autocomplete="name"><span class="err" id="e-name" role="alert"></span></div>
<div class="field"><label for="f-mobile">Mobile number</label><input id="f-mobile" name="mobile" inputmode="tel" value="{esc(u.get("mobile", ""))}" autocomplete="tel"><span class="err" id="e-mobile" role="alert"></span></div></section>'''
    else:
        who = f'''<section><h3><i>02</i>Name for your order</h3><div class="field"><label for="f-nick">First name or nickname<span class="req">Required</span></label><input id="f-nick" name="nick" value="{esc(u.get("nick", ""))}" maxlength="20" autocomplete="nickname" aria-required="true" aria-describedby="h-nick"><span class="hint" id="h-nick">Guest orders need a name. The counter will call it out when your order is ready, so choose one you will answer to. No account needed.</span><span class="err" id="e-nick" role="alert"></span></div></section>'''
    pays = "".join(f'<button data-act="cpay" data-p="{p[0]}" aria-pressed="{pressed(p[0] == S["pay"])}"><b>{p[1]}</b><small>{p[2]}</small></button>' for p in PAY)
    return f'''<div class="wrap"><nav class="crumbs" aria-label="Breadcrumb"><a href="#/menu">Menu</a> / Checkout</nav><h1 style="font-size:clamp(38px,6vw,64px);margin:6px 0 12px">Pickup and payment</h1>
<div class="co" id="co"><div>
<section><h3><i>01</i>Choose your pickup time</h3><span class="err" id="e-slot" role="alert" style="display:block;margin-bottom:8px"></span>{sug_slot()}<div class="slots" id="cs">{slots}</div>
<p class="fine">Pickup at the express counter. Show your PIN.</p></section>
{who}
<section><h3><i>03</i>Payment</h3><span class="err" id="e-pay" role="alert" style="display:block;margin-bottom:8px"></span>{sug_pay()}<div class="pay" id="pay">{pays}</div></section></div>
<aside class="sum" id="sum" aria-label="Order summary"></aside></div><div class="sbar" id="sbar"></div></div>'''


def after_render():
    wire_summary()


# ---------------------------------------------------------------- confirm
def place(*_):
    """Check the form, then either show the QR (cashless) or place the order (pay at the cart)."""
    if not S["cart"]:
        toast("Your bag is empty")
        return
    if not S["slot"] or not S["pay"]:
        q("#e-slot").textContent = "" if S["slot"] else "Choose a pickup window, or pick up now."
        q("#e-pay").textContent = "" if S["pay"] else "Choose a payment method."
        (q("#pay button") if S["slot"] else q("#cs .slot")).focus()
        return
    u, errors = S["user"], {}
    if S["acct"]:
        if len((u.get("name") or "").strip()) < 2:
            errors["name"] = "Enter your full name."
        if not PH_MOBILE.fullmatch((u.get("mobile") or "").replace(" ", "").replace("-", "")):
            errors["mobile"] = "Enter a Philippine mobile number, like 0917 555 0192."
    elif len((u.get("nick") or "").strip()) < 2:
        errors["nick"] = "Please enter a name (2 to 20 characters) so the counter knows who to call."
    for el in qa(".err"):
        el.textContent = ""
    for el in qa("#co input"):
        el.removeAttribute("aria-invalid")
    for key, message in errors.items():
        q("#e-" + key).textContent = message
        q("#f-" + key).setAttribute("aria-invalid", "true")
    if errors:
        q("#f-" + next(iter(errors))).focus()
        return
    if S["pay"] == "cashless":
        payments.open_pay_dialog()                   # the order is placed only after the payment succeeds
    else:
        payments.finish_order()


# ---------------------------------------------------------------- handlers (registered in main.py)
def on_slot(btn, _e=None):
    s = btn.getAttribute("data-s")
    S["slot"] = "" if S["slot"] == s else s
    q("#e-slot").textContent = ""
    for chip in qa("[data-act=sslot]"):
        chip.remove()
    for b in qa("#cs .slot"):
        b.setAttribute("aria-pressed", pressed(b.getAttribute("data-s") == S["slot"]))
    wire_summary()


def on_pay(btn, _e=None):
    p = btn.getAttribute("data-p")
    S["pay"] = "" if S["pay"] == p else p
    q("#e-pay").textContent = ""
    for chip in qa("[data-act=spay]"):
        chip.remove()
    for b in qa("#pay button"):
        b.setAttribute("aria-pressed", pressed(b.getAttribute("data-p") == S["pay"]))


def on_suggest_slot(btn, _e=None):
    S["slot"] = btn.getAttribute("data-id")
    for b in qa("#cs .slot"):
        b.setAttribute("aria-pressed", pressed(b.getAttribute("data-s") == S["slot"]))
    q("#e-slot").textContent = ""
    btn.remove()
    wire_summary()


def on_suggest_pay(btn, _e=None):
    S["pay"] = btn.getAttribute("data-id")
    for b in qa("#pay button"):
        b.setAttribute("aria-pressed", pressed(b.getAttribute("data-p") == S["pay"]))
    q("#e-pay").textContent = ""
    btn.remove()


def on_field_input(el):
    """Keep what the person types in S so it survives redraws of the summary."""
    S["user"][el.getAttribute("name")] = el.value
