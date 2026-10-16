"""Cart: the bag, its maths, vouchers, the saved bag, "Order again", and the slide-over bag drawer.

HOW THIS FILE WORKS (instructor map). Nothing here runs on its own. Each function marked EVENT is a PyScript
event handler: main.py's single click listener (@when("click", "body")) reads the clicked button's data-act
name and calls the matching function through the ACTIONS table. The handler changes the data in S["cart"]
and then redraws what is on screen (refresh_views).

  data-act="add"       vb.on_add        -> add_item()        Add a menu item to the bag
  data-act="qty"       on_qty           (+ / - buttons)      Change one line's quantity
  data-act="rm"        on_remove        (Remove button)      Take one line out of the bag
  data-act="bagclear"  on_clear_bag     (Clear bag)          Empty the bag (asks for a second tap)

CALCULATIONS (all in Philippine pesos, whole numbers, official menu prices only, no fees):
  line total = unit price x quantity        sub() = sum of every line total
  disc()     = voucher discount (0 if none) due() = max(0, sub() - disc())
"""
import random
import re
import string
import time

from pyscript import document

from data import D, SLOTS, VCAT, PAY
from state import (S, q, qa, esc, peso, icon, toast, later, load_json, save_json, save_acct, save_wallet)

MAX_QTY = 20          # most of one item per order
CLR = {"arm": False}  # True after the first tap on "Clear bag" (the second tap really clears)
HOOKS = {}            # later modules register redraw functions here (checkout summary, voucher list)
CART_KEY = "bb_cart"


# ---------------------------------------------------------------- cart maths
def find(drink_id):
    return next((d for d in D if d["id"] == drink_id), None)


def is_food(drink_id):
    d = find(drink_id)
    return bool(d and d.get("nc"))


def sub():
    return sum(i["u"] * i["q"] for i in S["cart"])


def count():
    return sum(i["q"] for i in S["cart"])


def stamp_qty(items):
    """Only drinks earn stamps, bakes do not."""
    return sum(0 if is_food(i["id"]) else i["q"] for i in items)


def make_item(d, qty):
    """One bag line. The price is always the official menu price: there are no sizes, add-ons or fees."""
    return {"k": d["id"], "id": d["id"], "n": d["n"], "u": d["p"], "q": qty}


def line_note(i):
    return f'{peso(i["u"])} each'


def add_item(drink_id, qty=1):
    """EVENT (via vb.on_add / views_drink.on_add): put a menu item in the bag. Same item again = quantity goes up."""
    d = find(drink_id)
    if not d:
        return
    line = next((i for i in S["cart"] if i["id"] == drink_id), None)
    if line:
        room = MAX_QTY - line["q"]
        if room <= 0:
            toast(f"You can order up to {MAX_QTY} of each item")
            return
        line["q"] += min(qty, room)
    else:
        S["cart"].append(make_item(d, min(qty, MAX_QTY)))
    refresh_views()
    toast(f'{d["n"]} added to your bag')
    btn = q("#bagBtn")
    btn.classList.remove("bump")
    _ = btn.offsetWidth          # reading this forces the browser to restart the animation
    btn.classList.add("bump")


def line_html(x, i):
    """One bag line, shared by the bag drawer and the checkout summary."""
    n = esc(i["n"])
    minus_off = " disabled" if i["q"] <= 1 else ""
    plus_off = " disabled" if i["q"] >= MAX_QTY else ""
    return (f'<div class="ci"><b>{n}</b><span class="p">{peso(i["u"] * i["q"])}</span><small>{line_note(i)}</small>'
            f'<div class="qty"><button type="button" aria-label="Fewer {n}" data-act="qty" data-i="{x}" data-d="-1"{minus_off}>{icon("minus")}</button>'
            f'<span aria-live="polite">{i["q"]}</span>'
            f'<button type="button" aria-label="More {n}" data-act="qty" data-i="{x}" data-d="1"{plus_off}>{icon("plus")}</button></div>'
            f'<button type="button" class="rmv" data-act="rm" data-i="{x}" aria-label="Remove {n} from your bag">{icon("trash")} Remove</button></div>')


def refresh_views(keep_arm=False):
    """Redraw every place that shows the bag: the header total, the open drawer, and the checkout summary."""
    if not keep_arm:
        CLR["arm"] = False
    render_bag()
    if q("#sheet.on"):
        bag()
    if q("#sum"):
        if S["cart"]:
            HOOKS["sum"]()
        else:
            HOOKS["route"]()                 # the bag is empty now: show the "bag is empty" page


def render_bag():
    c = count()
    q("#bagTxt").innerHTML = f"{c} · <b>{peso(sub())}</b>" if c else "Bag"
    persist()


# ---------------------------------------------------------------- vouchers
def vdef(code):
    if code in VCAT:
        return VCAT[code]
    if re.fullmatch(r"FREE-[A-Z0-9]{4,}", code or ""):
        return {"title": "Free drink", "desc": "One drink on us, up to ₱62. Covers one drink only.", "type": "free", "cap": 62}
    return None


def vcalc(code):
    """Return (discount, message, note). The message says why a voucher gives nothing yet; the note says what it covers."""
    v = vdef(code)
    if not v:
        return 0, "This voucher is not valid.", ""
    subtotal = sub()
    if not S["cart"]:
        return 0, "Add items to your bag to use this voucher.", ""
    if v.get("min") and subtotal < v["min"]:
        return 0, f'Spend {peso(v["min"] - subtotal)} more to use this voucher.', ""
    note = ""
    if v["type"] == "amt":
        amount = v["value"]
    elif v["type"] == "pct":
        amount = min(v.get("cap", 10 ** 9), int(subtotal * v["value"] / 100 + 0.5))
    else:                                    # free drink: ONE unit of the most expensive drink, never a bake
        drinks = [i for i in S["cart"] if not is_food(i["id"])]
        if not drinks:
            return 0, "Add a drink to use this voucher.", ""
        best = drinks[0]
        for i in drinks:
            if i["u"] > best["u"]:
                best = i
        amount = min(v.get("cap", 10 ** 9), best["u"])
        of = f' (1 of {best["q"]})' if best["q"] > 1 else ""
        note = f'Covers one drink only: {best["n"]}{of}. Everything else is charged normally.'
    return min(amount, subtotal), "", note


def disc():
    return vcalc(S["vapplied"])[0] if S["vapplied"] else 0


def due():
    return max(0, sub() - disc())


def wallet_avail():
    return len([w for w in S["wallet"] if not w["used"]])


def apply_code(raw):
    """Try to apply a typed code. Returns an error message, or '' when it worked."""
    code = "".join(str(raw).upper().split())
    if not code:
        return "Enter a voucher code."
    v = vdef(code)
    if not v:
        return "That code is not valid."
    w = next((x for x in S["wallet"] if x["code"] == code), None)
    if code.startswith("FREE-"):
        if not w or w["used"]:
            return "That voucher is not in your wallet."
    elif not v.get("reuse"):
        if not S["acct"]:
            return "Log in to use this voucher."
        if w and w["used"]:
            return "You have already used this voucher."
        if not w:
            S["wallet"].append({"code": code, "used": False})
            save_wallet()
    elif not w:                              # reusable codes are saved too, so they show up everywhere
        S["wallet"].append({"code": code, "used": False})
        save_wallet()
    S["vapplied"] = code
    return ""


def voucher_block():
    """The voucher button in the bag and at checkout. It opens a small screen (see dialogs.py)."""
    code = S["vapplied"]
    avail = [w for w in S["wallet"] if not w["used"] and vdef(w["code"])]
    if code:
        v = vdef(code)
        amt, msg, note = vcalc(code)
        head = (f'<span class="vt"><b>{esc(v["title"] if v else "Voucher")}</b>'
                f'<small>{esc(code)}{" · −" + peso(amt) if amt else ""}</small></span>')
        text = " ".join(x for x in (note, msg) if x)
        extra = f'<p class="vmsg" style="padding:0 16px 8px">{esc(text)}</p>' if text else ""
        extra += '<div class="vact" style="padding:0 16px 12px"><button type="button" class="vlink" data-act="vremove">Remove voucher</button></div>'
    else:
        small = f"{len(avail)} available in your wallet" if avail else "No vouchers in your wallet yet"
        head = f'<span class="vt"><b>Use a voucher</b><small>{small}</small></span>'
        extra = ""
    return (f'<div class="vbox vacc"><button type="button" class="vhead" data-act="vopen" aria-haspopup="dialog">'
            f'{icon("ticket")}{head}{icon("arrow")}</button>{extra}</div>')


def vrefresh():
    """After a voucher changes, redraw everything that shows totals."""
    render_bag()
    if q("#sum") and "sum" in HOOKS:
        HOOKS["sum"]()
    if q("#sheet.on"):
        bag()
    if q("#vlist") and "vlist" in HOOKS:
        HOOKS["vlist"]()


# ---------------------------------------------------------------- stamps become vouchers
def new_free():
    return "FREE-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def add_stamps(n):
    """Add stamps. Every full card of 10 becomes a free-drink voucher; extra stamps carry over."""
    S["stamps"] += n
    issued = 0
    while S["stamps"] >= 10:
        S["stamps"] -= 10
        S["wallet"].append({"code": new_free(), "used": False, "src": "stamps"})
        issued += 1
    return issued


# ---------------------------------------------------------------- saved bag (survives a refresh)
def persist():
    save_json(CART_KEY, {"t": int(time.time() * 1000), "cart": S["cart"], "vapplied": S["vapplied"], "slot": S["slot"]})


def restore_cart():
    """Load the saved bag, rebuilding every item from the real menu so edited data cannot change prices."""
    x = load_json(CART_KEY, None)
    if not isinstance(x, dict) or not isinstance(x.get("cart"), list):
        return False
    if time.time() * 1000 - x.get("t", 0) > 864e5:
        return False
    lines = {}
    for i in x["cart"]:
        if not isinstance(i, dict):
            continue
        d = find(i.get("id"))
        qty = i.get("q")
        if not d or not isinstance(qty, int) or isinstance(qty, bool) or qty < 1 or qty > MAX_QTY:
            continue
        if d["id"] in lines:                 # older saves could hold the same item twice
            lines[d["id"]]["q"] = min(MAX_QTY, lines[d["id"]]["q"] + qty)
        else:
            lines[d["id"]] = make_item(d, qty)
    S["cart"] = list(lines.values())
    S["vapplied"] = x.get("vapplied") if vdef(x.get("vapplied") or "") else ""
    S["slot"] = x.get("slot") if x.get("slot") in [s["id"] for s in SLOTS] else ""
    return bool(S["cart"])


# ---------------------------------------------------------------- remembered choices
def acct_key():
    return S["acct"]["email"] if S["acct"] else "guest"


def load_prefs():
    return load_json("bb_prefs_" + acct_key(), {})


def save_prefs(p):
    save_json("bb_prefs_" + acct_key(), p)


def sug_slot_bag():
    sl = next((x for x in SLOTS if x["id"] == load_prefs().get("slot")), None)
    if sl and not S["slot"]:
        return f'<button type="button" class="sugg" data-act="bsugg" data-id="{sl["id"]}" style="margin:2px 0 10px">{icon("timer")}Same as last time: {esc(sl["n"])}</button>'
    return ""


# ---------------------------------------------------------------- order again
def last_key():
    return "bb_last_" + acct_key()


def save_last(items):
    save_json(last_key(), {"t": int(time.time() * 1000), "items": [
        {"id": i["id"], "n": i["n"], "u": i["u"], "q": i["q"]} for i in items]})


def load_last():
    x = load_json(last_key(), None)
    if not isinstance(x, dict) or not isinstance(x.get("items"), list):
        return None
    items = [i for i in x["items"] if isinstance(i, dict) and find(i.get("id")) and isinstance(i.get("q"), int) and 0 < i["q"] <= 20]
    return {"items": items} if items else None


def order_again_card():
    last = load_last()
    if not last:
        return ""
    n = sum(i["q"] for i in last["items"])
    names = ", ".join(f'{i["q"]}× {i["n"]}' for i in last["items"])
    return (f'<div class="again"><div><b>Order again</b><p>{esc(names)}</p></div>'
            f'<button class="btn pri" type="button" data-act="again">{icon("plus")} Add {n} item{"s" if n > 1 else ""} to bag</button></div>')


def order_again_section():
    card = order_again_card()
    return f'<section class="sec" style="padding-bottom:0"><div class="wrap">{card}</div></section>' if card else ""


# ---------------------------------------------------------------- slide-over sheets
_last_focus = None


def open_sheet(content):
    global _last_focus
    sheet = q("#sheet")
    was_open = sheet.classList.contains("on")      # redrawing an open drawer must not steal focus
    if not was_open:
        _last_focus = document.activeElement
    sheet.innerHTML = content
    sheet.removeAttribute("inert")

    def show():
        sheet.classList.add("on")
        q("#scrim").classList.add("on")
        el = sheet.querySelector("[data-first]") or sheet.querySelector("button")
        if el and not was_open:
            el.focus()
    later(show)


def close_sheet(*_):
    sheet = q("#sheet")
    sheet.classList.remove("on")
    q("#scrim").classList.remove("on")
    sheet.setAttribute("inert", "")
    if _last_focus:
        _last_focus.focus()


def pickup_block():
    """The pickup-time buttons shown in the bag."""
    buttons = "".join(
        f'<button data-act="bslot" aria-pressed="{str(s["id"] == S["slot"]).lower()}" data-s="{s["id"]}">{s["n"]}'
        + ("" if s["id"] == "now" else f'<small>{s["s"]}</small>') + "</button>" for s in SLOTS)
    req = "" if S["slot"] else '<span class="req">Required</span>'
    return f'<div class="opt" style="margin-top:6px"><b>Pickup window{req}</b>{sug_slot_bag()}<div class="seg" id="bslots">{buttons}</div></div>'


def stamp_box():
    n = stamp_qty(S["cart"])
    if S["acct"]:
        total, left = S["stamps"] + n, 10 - S["stamps"]
        msg = "This order earns you a free drink voucher." if total >= 10 else f'{left} more cup{"s" if left > 1 else ""} until your 11th is free.'
        bars = "".join(f'<i class="{"f" if i < total else ""}"></i>' for i in range(10))
        note = " Bakes earn no stamps." if n < count() else ""
        return (f'<div class="box"><b>{msg}</b><div class="stamps">{bars}</div>'
                f'<span style="color:var(--mut)">{S["stamps"]} stamps now, +{n} with this order.{note}</span></div>')
    return ('<div class="box"><b>Earn stamps with an account</b><br><span style="color:var(--mut)">Stamps are for account holders. '
            '<a class="lnk" href="#/login" data-act="close">Log in</a> or <a class="lnk" href="#/register" data-act="close">create an account</a> to start your card.</span></div>')


def bag(*_):
    """Open or redraw the bag drawer from S["cart"]. Shows the empty state or the populated state."""
    head = f'<div class="sh"><h3 id="shT">Your bag</h3><button class="x" aria-label="Close" data-act="close">{icon("x")}</button></div>'
    if not S["cart"]:
        CLR["arm"] = False
        open_sheet(head + '''<div class="sb"><div class="cempty"><h3>Your bag is empty</h3><p>Pick a drink or a bake and it will wait here while you choose a pickup time.</p>
<a class="btn pri" style="margin-top:18px" href="#/menu" data-act="close">Browse the menu</a></div></div>''')
        return
    rows = "".join(line_html(x, i) for x, i in enumerate(S["cart"]))
    n = count()
    clear = f'<button type="button" class="clrb" data-act="bagclear">{"Tap again to clear your bag" if CLR["arm"] else "Clear bag"}</button>'
    voucher_line = f'<div class="ln"><span>Voucher</span><span>−{peso(disc())}</span></div>' if disc() else ""
    if S["slot"]:
        go = f'<a class="btn pri" style="width:100%;margin-top:14px" href="#/checkout" data-act="close" data-first>Continue to checkout {icon("arrow")}</a>'
    else:
        go = '<button class="btn pri" style="width:100%;margin-top:14px" disabled>Choose a pickup time to continue</button>'
    open_sheet(head + f'''<div class="sb">{pickup_block()}{rows}{clear}{voucher_block()}{stamp_box()}</div>
<div class="sf"><div class="ln"><span>Subtotal · {n} item{"" if n == 1 else "s"}</span><span>{peso(sub())}</span></div>{voucher_line}
<div class="ln t"><span>Total</span><span>{peso(due())}</span></div>{go}</div>''')


# ---------------------------------------------------------------- click handlers (registered in main.py)
def _refocus(selector):
    """After a redraw the clicked button is a new element: put keyboard focus back on its replacement."""
    el = q(selector)
    if el and not el.disabled:
        el.focus()


def on_qty(btn, _e=None):
    """EVENT data-act="qty": the + and - buttons (bag drawer and checkout summary). Changes one line, then redraws."""
    i, step = int(btn.getAttribute("data-i")), int(btn.getAttribute("data-d"))
    if not 0 <= i < len(S["cart"]):
        return
    line = S["cart"][i]
    new = line["q"] + step
    if new > MAX_QTY:
        toast(f"You can order up to {MAX_QTY} of each item")
        return
    if new < 1:                              # the minus button is disabled at 1; this only guards bad data
        return
    line["q"] = new
    refresh_views()
    _refocus(f'[data-act="qty"][data-i="{i}"][data-d="{step}"]')


def on_remove(btn, _e=None):
    """EVENT data-act="rm": remove one line from the bag."""
    i = int(btn.getAttribute("data-i"))
    if not 0 <= i < len(S["cart"]):
        return
    gone = S["cart"].pop(i)
    refresh_views()
    toast(f'{gone["n"]} removed from your bag')
    if S["cart"]:
        _refocus(f'[data-act="rm"][data-i="{min(i, len(S["cart"]) - 1)}"]')


def on_clear_bag(*_):
    """EVENT data-act="bagclear": empty the bag. The first tap asks to confirm, the second tap clears."""
    if not S["cart"]:
        return
    if not CLR["arm"]:
        CLR["arm"] = True
        refresh_views(keep_arm=True)
        return
    S["cart"], S["vapplied"] = [], ""
    refresh_views()
    toast("Your bag is empty")


def on_bslot(btn, _e=None):
    s = btn.getAttribute("data-s")
    S["slot"] = "" if S["slot"] == s else s
    persist()
    bag()


def on_bsugg(btn, _e=None):
    S["slot"] = btn.getAttribute("data-id")
    persist()
    bag()


def on_again(*_):
    last = load_last()
    if not last:
        return
    for i in last["items"]:
        add_item(i["id"], i["q"])
    toast("Your last order is in the bag")
    bag()


def on_vremove(*_):
    S["vapplied"] = ""
    vrefresh()
    toast("Voucher removed")


def on_vuse(btn, _e=None):
    S["vapplied"] = btn.getAttribute("data-code")
    vrefresh()
    toast("Voucher applied to your bag")


def on_vapply(btn, _e=None):
    """Redeem a typed code (the box lives on the Vouchers page)."""
    box = btn.closest("[data-vbox]")
    inp, msg = box.querySelector(".vin"), box.querySelector(".vmsg")
    err = apply_code(inp.value)
    if err:
        msg.textContent = err
        msg.classList.add("err")
        inp.setAttribute("aria-invalid", "true")
        inp.focus()
        return
    vrefresh()
    if msg.isConnected:
        msg.textContent = "Redeemed. It will apply to your bag."
        msg.classList.remove("err")
        inp.removeAttribute("aria-invalid")
        inp.value = ""
    toast("Voucher redeemed")
