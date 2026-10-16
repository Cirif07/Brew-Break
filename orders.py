"""Orders: placing an order, remembering it, the tracker page, and claiming stamps after signing up.

commit_order() is the single place where an order becomes real. It is only called after payment succeeded
(QR payments) or straight away for "Pay at the cart". Stamps, vouchers and "Order again" all change here, nowhere else.
"""
import random
import time

from pyscript import window
from pyodide.ffi import create_proxy

import cart
from data import BIZ, NORM_PAY, PAY, SLOTS, STEP_NAMES, STEP_TXT
from state import S, esc, icon, load_json, peso, q, save_acct, save_json, store_set, toast

ORDER_KEY = "bb_order"
_tracker = None                                   # id of the timer that moves the order along


def new_ref():
    return "BB-" + str(4082 + random.randrange(40))


# ---------------------------------------------------------------- placing an order
def commit_order():
    """Create the order from the bag. Called only after a successful payment, or for Pay at the cart."""
    user = S["user"]
    order_id = S["pay_ref"] or new_ref()
    S["pay_ref"] = ""
    nick = S["acct"]["name"].strip().split(" ")[0] if S["acct"] else (user.get("nick") or "").strip()
    items = [dict(i) for i in S["cart"]]
    drinks = cart.stamp_qty(S["cart"])
    S["order"] = {"id": order_id, "items": items, "total": cart.due(), "vcode": S["vapplied"], "vamt": cart.disc(),
                  "slot": S["slot"], "pay": S["pay"], "paid": S["pay"] == "cashless", "acct": bool(S["acct"]),
                  "earned": drinks if S["acct"] else 0, "nick": nick, "stage": 0, "vissued": 0}
    cart.save_last(items)                                            # for "Order again"
    cart.save_prefs({"slot": S["slot"], "pay": S["pay"], "nick": "" if S["acct"] else nick})   # for "Same as last time"
    if not S["acct"] and drinks > 0:                                 # a guest can still claim these stamps after signing up
        S["pending"] = {"id": order_id, "n": drinks}
        save_json("bb_pending", {"t": int(time.time() * 1000), "id": order_id, "n": drinks})
    if S["acct"]:
        names = ", ".join(f'{i["q"]}× {i["n"]}' for i in S["cart"])
        S["hist"].insert(0, ["Today", f"{order_id} · {names}", f"+{drinks}"])
        issued = cart.add_stamps(drinks)                             # a full card becomes a free-drink voucher
        S["order"]["vissued"] = issued
        if issued:
            S["hist"].insert(0, ["Today", "Free drink voucher added to your wallet", "Voucher"])
    if S["vapplied"] and S["order"]["vamt"]:                         # one-time vouchers are used up
        w = next((x for x in S["wallet"] if x["code"] == S["vapplied"]), None)
        if w and not (cart.vdef(S["vapplied"]) or {}).get("reuse"):
            w["used"] = True
            w["usedAt"] = int(time.time() * 1000)
    S["vapplied"] = ""
    S["cart"], S["slot"], S["pay"] = [], "", ""
    save_acct()
    cart.render_bag()
    window.location.hash = "#/live"


# ---------------------------------------------------------------- saved order (the Orders page survives a refresh)
def persist_order():
    if S["order"]:
        save_json(ORDER_KEY, {"t": int(time.time() * 1000), "o": S["order"]})


def restore_order():
    """Rebuild the saved order from the real menu so edited data cannot change what is shown."""
    x = load_json(ORDER_KEY, None)
    if not isinstance(x, dict) or not isinstance(x.get("o"), dict):
        return
    o = x["o"]
    oid = str(o.get("id", ""))
    if time.time() * 1000 - x.get("t", 0) > 432e5 or not oid.startswith("BB-") or not oid[3:].isdigit() or not isinstance(o.get("items"), list):
        return
    items = []
    for i in o["items"]:
        d = cart.find(i.get("id")) if isinstance(i, dict) else None
        qty = i.get("q") if d else None
        if not d or not isinstance(qty, int) or isinstance(qty, bool) or qty < 1 or qty > 20:
            continue
        items.append(cart.make_item(d, qty))
    if not items:
        return
    pay = NORM_PAY.get(o.get("pay"), o.get("pay"))
    num = lambda v: v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0
    S["order"] = {"id": oid, "items": items, "total": max(0, num(o.get("total"))), "vcode": str(o.get("vcode") or "")[:24],
                  "vamt": max(0, num(o.get("vamt"))), "slot": o.get("slot") if o.get("slot") in [s["id"] for s in SLOTS] else "now",
                  "pay": pay if pay in [p[0] for p in PAY] else PAY[0][0], "paid": bool(o.get("paid")), "acct": bool(o.get("acct")),
                  "earned": max(0, int(num(o.get("earned")))), "nick": str(o.get("nick") or "")[:20],
                  "stage": min(3, max(0, int(num(o.get("stage"))))), "vissued": 0}


# ---------------------------------------------------------------- stamps a guest can claim after signing up
def restore_pending():
    x = load_json("bb_pending", None)
    if isinstance(x, dict) and time.time() * 1000 - x.get("t", 0) < 864e5:
        oid, n = str(x.get("id", "")), x.get("n")
        if oid.startswith("BB-") and oid[3:].isdigit() and isinstance(n, int) and 0 < n <= 20:
            S["pending"] = {"id": oid, "n": n}


def claim_pending():
    """After a guest logs in or registers, give them the stamps from the order they just placed."""
    p = S["pending"]
    if not p or not S["acct"]:
        return
    issued = cart.add_stamps(p["n"])
    S["hist"].insert(0, ["Today", f'{p["id"]} · added after sign-up', f'+{p["n"]}'])
    S["pending"] = None
    store_set("bb_pending", "")
    save_acct()
    toast(f'We added {p["n"]} stamp{"s" if p["n"] > 1 else ""} from order {p["id"]}{" and a free drink voucher" if issued else ""}')


def claim_box(o):
    p = S["pending"]
    if o["acct"] or not p or p["id"] != o["id"]:
        return ""
    n = p["n"]
    return (f'<div class="box claim"><b>You earned {n} stamp{"s" if n > 1 else ""} on this order</b>'
            f'<p style="margin-top:4px">Create a free account to claim {"them" if n > 1 else "it"}. Stamps add up to a free drink.</p>'
            f'<div class="vact"><a class="btn pri" href="#/register">Create an account</a><a class="vlink" href="#/login">Log in</a></div></div>')


# ---------------------------------------------------------------- the Orders (tracker) page
def steps_for(items):
    foods = any(cart.is_food(i["id"]) for i in items)
    drinks = any(not cart.is_food(i["id"]) for i in items)
    text = STEP_TXT["both" if foods and drinks else "food" if foods else "drink"]
    return list(zip(STEP_NAMES, text))


def live_html(o):
    st = o["stage"]
    sl = next((s for s in SLOTS if s["id"] == o["slot"]), SLOTS[0])
    steps = steps_for(o["items"])
    rows = "".join(
        f'<li class="{"done" if i < st or st == 3 else "now" if i == st else ""}"><span class="d">{icon("check") if i < st or st == 3 else i + 1}</span>'
        f'<div><b>{n}</b><p style="font-size:14px">{t}</p></div></li>' for i, (n, t) in enumerate(steps))
    if st == 2:
        action = '<button class="btn pri" data-act="pickedup">I picked it up</button>'
    elif st == 3:
        action = '<button class="btn pri" data-act="reorder">Order these again</button>'
    else:
        action = ""
    items = "".join(f'<div class="ci"><b>{i["q"]}× {i["n"]}</b><span class="p">{peso(i["u"] * i["q"])}</span><small>{cart.line_note(i)}</small></div>' for i in o["items"])
    voucher = f'<div class="ln"><span>Voucher {esc(o["vcode"])}</span><span>−{peso(o["vamt"])}</span></div>' if o["vamt"] else ""
    pay_line = ("Demo payment: no real money was taken" if BIZ["demoPayments"] else "Paid by QR code") if o["pay"] == "cashless" else "To pay at the cart: " + peso(o["total"])
    return f'''<div><span class="pill">{"Demo status" if st < 3 else "Complete (demo)"}</span><h1 style="font-size:clamp(40px,7vw,76px);margin:16px 0 10px">{steps[st][0]}</h1>
<p style="color:var(--mut)">Ticket {o["id"]} · for {esc(o["nick"] or "you")} · pickup {sl["t"]}</p><ol class="tl">{rows}</ol>
<div class="cta">{action}<a class="lnk" href="#/menu">Back to the menu</a></div></div>
<aside><div class="pass"><p class="eyebrow"><i>Handover PIN</i></p><div class="pin">{o["id"][-4:]}</div>
<p style="font-size:14px;color:var(--mut)">Show this PIN at the express counter. We will call out <b>{esc(o["nick"] or "your name")}</b> when your order is ready.</p></div>
<p class="fine demo-note"><b>Demo only.</b> This status moves on a timer in your browser. It is not connected to a real shop, and nothing was sent to one.</p>
{claim_box(o)}<div class="sum" style="position:static;margin-top:18px"><h3>Order summary</h3>{items}{voucher}<div class="ln t"><span>Total</span><span>{peso(o["total"])}</span></div><p class="fine">{pay_line}</p></div></aside>'''


def live():
    if not S["order"]:
        return ('<div class="wrap"><div class="empty" style="padding:120px 0"><h2>No active order</h2>'
                '<p>When you place a pre-order, its progress and handover PIN appear here.</p><a class="btn pri" href="#/menu">Browse the menu</a></div></div>')
    return '<div class="wrap lv" id="lv"></div>'


def draw():
    el = q("#lv")
    if el and S["order"]:
        persist_order()
        el.innerHTML = live_html(S["order"])


def start_tracker():
    """Draw the tracker and move the order along every 7 seconds (a demo of what the cart's system would send)."""
    global _tracker
    stop_tracker()
    if not S["order"]:
        return
    draw()

    def tick():
        o = S["order"]
        if o and o["stage"] < 2:
            o["stage"] += 1
            draw()
    _tracker = window.setInterval(create_proxy(tick), 7000)


def stop_tracker():
    global _tracker
    if _tracker is not None:
        window.clearInterval(_tracker)
        _tracker = None


def on_pickedup(*_):
    S["order"]["stage"] = 3
    draw()


def on_reorder(*_):
    for item in S["order"]["items"]:
        existing = next((c for c in S["cart"] if c["k"] == item["k"]), None)
        if existing:
            existing["q"] += item["q"]
        else:
            S["cart"].append(dict(item))
    cart.render_bag()
    cart.bag()
