"""Drink detail page: photo or icon, facts, a quantity picker and an Add button. Every item is sold at its menu price."""
import re

import cart
from data import CATS
from state import esc, icon, peso, q
from views_browse import art, coming_soon

DT = {"qty": 1}                                  # quantity chosen on this page


def caffeine_info(d):
    """Caffeine facts taken from the drink's own description (never guessed)."""
    text = (d["n"] + " " + d["d"]).lower()
    if d.get("cf"):
        return "Caffeine free", "No tea or coffee"
    if re.search(r"coffee|espresso|tea|matcha|barako|robusta|arabica|liberica|sencha|jasmine|assam", text):
        return "Contains caffeine", "Tea or coffee based"
    return "Ask the counter", "Caffeine level varies"


def drink_page(drink_id):
    d = cart.find(drink_id)
    if not d:
        return coming_soon("Drink not found", "404")
    DT["qty"] = 1
    c = next(x for x in CATS if x["id"] == d["cat"])
    if d.get("nc"):
        second = "<div><b>Same pickup</b>Collected with your drinks</div>"
        first, third = "Baked fresh", ("No stamp", "Bakes do not earn stamps")
    else:
        info = caffeine_info(d)
        second = f"<div><b>{info[0]}</b>{info[1]}</div>"
        first, third = "Made to order", ("+1 stamp", "With an account")
    return f'''<div class="wrap"><nav class="crumbs" aria-label="Breadcrumb"><a href="#/menu">Menu</a> / <a href="#/menu/{d["cat"]}">{c["n"]}</a> / {d["n"]}</nav>
<div class="dt" id="dt"><div class="rise">{art(d, "big")}</div><div class="rise" style="--i:1"><p class="eyebrow"><i>{d.get("t") or c["n"]}</i></p><h1 style="font-size:clamp(38px,6vw,64px);margin:10px 0">{d["n"]}</h1>
<div class="price" style="font-size:28px">{peso(d["p"])}</div>
<p style="color:var(--mut);margin-top:10px">{d["d"]}</p>
<div class="facts"><div><b>{first}</b>At the cart</div>{second}<div><b>{third[0]}</b>{third[1]}</div></div>
<p class="fine allergy">Made in a shared kitchen. Drinks and bakes may contain milk, soy, gluten, eggs or nuts. Tell the counter about any allergy before you order.</p>
<div class="dbuy"><div class="qty"><button aria-label="Fewer" data-act="dqty" data-d="-1">{icon("minus")}</button><span id="dq">1</span><button aria-label="More" data-act="dqty" data-d="1">{icon("plus")}</button></div><button class="btn pri" id="dadd" data-act="dadd" data-id="{drink_id}">Add to bag</button></div></div></div></div>'''


def update_buy():
    """Refresh the quantity and the price on the Add button."""
    btn = q("#dadd")
    d = cart.find(btn.getAttribute("data-id"))
    q("#dq").textContent = str(DT["qty"])
    btn.textContent = "Add to bag · " + peso(d["p"] * DT["qty"])


def after_render():
    if q("#dadd"):                                  # the "drink not found" page has no Add button
        update_buy()


# ---------------------------------------------------------------- handlers (registered in main.py)
def on_qty(btn, _e=None):
    """EVENT data-act="dqty": the + and - on the drink page."""
    DT["qty"] = max(1, min(10, DT["qty"] + int(btn.getAttribute("data-d"))))
    update_buy()


def on_add(btn, _e=None):
    """EVENT data-act="dadd": add the chosen quantity, then open the bag so the customer can review it."""
    cart.add_item(btn.getAttribute("data-id"), DT["qty"])
    cart.bag()
