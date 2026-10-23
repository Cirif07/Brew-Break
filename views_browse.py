"""Home and Menu pages. Each view returns an HTML string; main.py puts it on the page.

The handlers at the bottom are event-driven: a click on a filter chip, a key typed in the
search box or a tap on a pickup time each change the state in S/M and redraw only what changed.
"""
import math
import re

from pyodide.ffi import create_proxy

from data import BIZ, CATS, D, GLYPH, PHOTOS, PROMO, SLOTS
from state import M, S, esc, icon, peso, q, qa, toast
from cart import add_item, find, order_again_card, order_again_section


def pressed(flag):
    return str(bool(flag)).lower()


# ---------------------------------------------------------------- shared pieces
def photo_ok(url):
    return bool(re.fullmatch(r"data:image/(png|jpe?g|webp|avif);base64,[A-Za-z0-9+/=]+", url or ""))


def art(d, cls=""):
    """A drink's picture tile: a photo if one is embedded in data.py, otherwise an icon."""
    photo = PHOTOS.get(d["id"])
    if photo_ok(photo):
        inner = f'<img src="{photo}" alt="{esc(d["n"])}" loading="lazy" decoding="async">'
        extra = " ph"
    else:
        glyph = GLYPH.get(d["id"]) or GLYPH[d["cat"]]
        inner = f'<svg class="food" viewBox="0 0 256 256" aria-hidden="true"><use href="#i-{glyph}"/></svg>'
        extra = ""
    return f'<div class="art {cls}{extra}" style="--c:{d["c"]}">{inner}</div>'


def hero_cta():
    sl = next((x for x in SLOTS if x["id"] == S["slot"]), None)
    if not sl:
        return ""
    name = "pickup now" if sl["id"] == "now" else sl["n"]
    return f'<a class="btn pri" style="width:100%;margin-top:14px" href="#/menu">Choose drinks for {esc(name)} {icon("arrow")}</a>'


def drink_card(d):
    tag = d.get("t") or next(c["n"] for c in CATS if c["id"] == d["cat"])
    return (f'<article class="dc">{art(d)}<span class="tag">{tag}</span><h3><a href="#/drink/{d["id"]}">{d["n"]}</a></h3><p>{d["d"]}</p>'
            f'<div class="foot"><span class="price">{peso(d["p"])}</span>'
            f'<button class="add" data-act="add" data-id="{d["id"]}" aria-label="Add {d["n"]} to bag">{icon("plus")} Add</button></div></article>')


def rewards_promo():
    acct = S["acct"]
    n = min(10, S["stamps"]) if acct else 4          # guests see an example card with 4 stamps
    left = 10 - n
    dots = "".join(f'<span class="hs{" f" if i < n else ""}">{icon("check") if i < n else i + 1}</span>' for i in range(10))
    if not acct:
        lead = "Create a free account and collect a stamp with every drink you order. Reach ten and your next drink is on us."
        cta = '<a class="btn pri" href="#/register">Create an account</a><a class="lnk" href="#/login">I already have one</a>'
    elif n >= 10:
        lead = "Your card is full. Your free drink voucher is ready to claim."
        cta = '<a class="btn acc" href="#/rewards">Claim your free drink</a>'
    else:
        lead = f'You have {n} of 10 stamps. {left} more drink{"" if left == 1 else "s"} and a free drink voucher is added to your wallet.'
        cta = '<a class="btn pri" href="#/menu">Order a drink</a><a class="lnk" href="#/rewards">View my rewards</a>'
    label = f"{n} of 10" if acct else "Example card"
    return f'''<section class="sec" aria-labelledby="rwh"><div class="wrap"><div class="rwd"><div><h2 id="rwh">Every drink gets you closer to a free one.</h2><p class="lead">{lead}</p>
<ul class="hl"><li>{icon("check")}One stamp for every drink you order</li><li>{icon("check")}Stamps stay on your card until you use them</li><li>{icon("check")}Ten stamps add a free-drink voucher</li></ul><div class="cta">{cta}</div></div>
<div class="scard rise" style="--i:1"><div class="top"><b>Brew Break stamp card</b><span>{label}</span></div><div class="hgrid">{dots}</div>
<div class="hfree">{icon("gift")}<b>11th drink</b><span>On us</span></div></div></div></div></section>'''


def visit_section():
    hours = "".join(f'<div class="vrow2"><span>{esc(h[0])}</span><b>{esc(h[1])}</b></div>' for h in BIZ["hours"])
    where = (esc(BIZ["address"]) + ", " + esc(BIZ["city"])) if BIZ["address"] else esc(BIZ["city"])
    directions = ""
    if BIZ["address"]:
        query = (BIZ["address"] + ", " + BIZ["city"]).replace(" ", "+")
        directions = f'<a class="lnk" target="_blank" rel="noopener" href="https://www.google.com/maps/search/?api=1&query={esc(query)}">Get directions</a>'
    phone = " · " + esc(BIZ["phone"]) if BIZ["phone"] else ""
    area = "" if BIZ["address"] else '<div class="vrow2"><span>Pickup area</span><b>Near the College of Information Technology building, Cebu Eastern College (exact spot not set yet)</b></div>'
    return f'''<section class="sec tint" id="visit"><div class="wrap vis"><div><h2>Visit us</h2><p class="lead">Order ahead, then collect at the express counter. Show your PIN, or answer to the name you gave us, when your order is ready.</p>{directions}</div>
<div class="vlist2"><div class="vrow2"><span>Where</span><b>{where}</b></div>{area}{hours}<div class="vrow2"><span>Pay with</span><b>{"<br>".join(esc(x) for x in BIZ["pay"])}</b></div><div class="vrow2"><span>Contact</span><b><a class="lnk" href="mailto:{esc(BIZ["email"])}">{esc(BIZ["email"])}</a>{phone}</b></div></div></div></section>'''


def footer_html():
    """The site footer, built from data.py so contact details and hours can never disagree with the Visit section."""
    hours = "".join(f'<li><span>{esc(h[0])}</span> {esc(h[1])}</li>' for h in BIZ["hours"])
    where = (esc(BIZ["address"]) + ", " + esc(BIZ["city"])) if BIZ["address"] else esc(BIZ["city"])
    return f'''<div class="wrap foot"><div class="fb"><a class="logo" href="#/home" aria-label="Brew Break home"><svg class="mark" viewBox="0 0 48 48" aria-hidden="true"><use href="#bb-mark"/></svg><span class="wm"><span>Brew</span><span>Break</span></span></a>
<p>Good-tasting drinks. Student-friendly prices. Your perfect break.</p></div>
<nav aria-label="Explore"><h3>Explore</h3><a href="#/home">Home</a><a href="#/menu">Menu</a><a href="#/rewards">Rewards</a><a href="#/vouchers">Vouchers</a></nav>
<div><h3>Visit</h3><ul><li>{where}</li>{hours}</ul><a class="lnk" href="mailto:{esc(BIZ["email"])}">{esc(BIZ["email"])}</a></div>
<nav aria-label="Legal"><h3>Legal</h3><a href="#/privacy">Privacy</a><a href="#/terms">Terms</a></nav></div>
<p class="wrap fine foot-note">© 2026 Brew Break. A student project: payments and order tracking on this site are simulated.</p>'''


# ---------------------------------------------------------------- Home
HC = {"cat": "mt"}                                  # category chosen in the homepage browser (changed by on_hcat)


def home_tabs():
    return "".join(
        f'<button class="tab" data-act="hcat" data-c="{c["id"]}" aria-pressed="{pressed(HC["cat"] == c["id"])}">{c["n"]}<small>{len([d for d in D if d["cat"] == c["id"]])}</small></button>'
        for c in CATS)


def home_grid():
    c = next(x for x in CATS if x["id"] == HC["cat"])
    cards = "".join(drink_card(d) for d in D if d["cat"] == c["id"])
    return f'<p class="hsub">{c["s"]}</p><div class="fav">{cards}</div>'


def promo_section():
    """The promotional video. Without a real file it shows a clearly labelled placeholder, never a fake player."""
    src = PROMO.get("src")
    if src:
        poster = f' poster="{esc(PROMO["poster"])}"' if PROMO.get("poster") else ""
        track = f'<track kind="captions" src="{esc(PROMO["captions"])}" srclang="en" label="English" default>' if PROMO.get("captions") else ""
        media = (f'<video id="promo" controls preload="metadata" playsinline{poster} aria-label="{esc(PROMO["title"])}">'
                 f'<source src="{esc(src)}" type="{esc(PROMO.get("type", "video/mp4"))}">{track}'
                 f'<p>Your browser cannot play this video. <a href="{esc(src)}">Download it</a>.</p></video><p class="fine" id="promo-note"></p>')
    else:
        media = (f'<div class="vph" id="promo-ph" role="img" aria-label="Placeholder: the Brew Break promotional video has not been added yet">{icon("play")}'
                 '<b>Promotional video placeholder</b><p>The official 30–60 second Brew Break video has not been added yet. '
                 'Add the file to the assets folder and set PROMO in data.py.</p></div>')
    return ('<section class="sec tint" aria-labelledby="pvh"><div class="wrap vid"><div><h2 id="pvh">Meet Brew Break</h2>'
            '<p style="color:var(--mut);margin-top:14px;font-size:17px">A short look at who we are, what we serve and how pre-ordering works, without leaving this page.</p></div>'
            f'<div>{media}</div></div></section>')


def after_home():
    """Show the real video length under the player once the browser has read the file (the video's loadedmetadata event)."""
    video = q("#promo")
    if not video:
        return

    def loaded(*_):
        secs = float(video.duration)
        if not math.isfinite(secs):
            return
        m, s = divmod(int(round(secs)), 60)
        ok = 30 <= secs <= 60
        q("#promo-note").textContent = f"Video length {m}:{s:02d}" + ("" if ok else " (the assignment needs 30–60 seconds)")
    video.addEventListener("loadedmetadata", create_proxy(loaded))
    if video.readyState >= 1:
        loaded()


def home():
    slots = "".join(
        f'<button class="slot" data-act="hslot" aria-pressed="{pressed(s["id"] == S["slot"])}" data-s="{s["id"]}"><span>{s["n"]}</span><em>{s["q"]}</em><small>{s["t"]} · {s["m"]}</small></button>'
        for s in SLOTS)
    drink_min = min(d["p"] for d in D if d["cat"] != "bk")
    bake_min = min(d["p"] for d in D if d["cat"] == "bk")
    vals = "".join(f'<div>{icon(i)}<span><b>{t}</b>{x}</span></div>' for i, t, x in [
        ("coffee", "Good-tasting drinks", "Milk tea, iced coffee, fruit refreshers and frappes"),
        ("wallet", "Student-friendly prices", f"Drinks from {peso(drink_min)}, bakes from {peso(bake_min)}"),
        ("clock", "Your perfect break", "Order ahead and pick up when you are ready")])
    tiers = "".join(
        f'<a class="tier" href="#/menu/{t[3]}"><b>{t[0]}</b><div><h3>{t[1]}</h3><p>{t[2]}</p></div>{icon("arrow")}</a>'
        for t in [("₱30–35", "Pocket friendly", "Barako iced brew, calamansi tea, vanilla americano and mango passion cooler.", "ic"),
                  ("₱38–50", "Signature break", "Milk teas, Spanish iced coffee, caramel macchiato and strawberry lychee fizz, with a stamp on every drink when you have an account.", "mt"),
                  ("₱58–62", "Treat yourself", "Cookies and cream, java chip blended and matcha cloud frappes.", "fb")])
    steps = "".join(
        f'<div class="step"><h3>{t[0]}</h3><p>{t[1]}</p></div>'
        for t in [("Pick a drink", "Milk tea, coffee, fruit refreshers, frappes or a bake."), ("Review your bag", "Check quantities and totals before you continue."),
                  ("Choose your time", "Tell us when you will arrive so the ice stays solid."), ("Show your PIN", "Walk to the express window and grab your order.")])
    return f'''<div class="wrap"><section class="hero"><div><p class="brandline rise"><svg class="mark" viewBox="0 0 48 48" aria-hidden="true"><use href="#bb-mark"/></svg>Brew Break · for Cebu Eastern College students</p>
<h1 class="rise" style="--i:1;margin-top:14px">Good drinks. <em>Better breaks.</em></h1>
<p class="rise" style="--i:2">Good-tasting drinks. Student-friendly prices. Your perfect break.</p>
<div class="cta rise" style="--i:3"><a class="btn pri" href="#/menu">See the menu {icon("arrow")}</a><a class="lnk" href="#/rewards">How rewards work</a></div>
<div class="vals rise" style="--i:4">{vals}</div></div>
<aside class="bell rise" style="--i:3" aria-labelledby="bt"><h3 id="bt">When do you want it?</h3><div class="slots" id="hs">{slots}</div><div id="hcta">{hero_cta()}</div></aside></section></div>
{order_again_section()}
<section class="sec" aria-labelledby="bch"><div class="wrap"><div class="head"><h2 id="bch">Browse the menu</h2><a class="lnk" href="#/menu">See all {len(D)} items</a></div>
<div class="tabs" id="hcats" role="group" aria-label="Menu categories">{home_tabs()}</div><div id="hgrid" aria-live="polite" style="margin-top:22px">{home_grid()}</div></div></section>
{promo_section()}
{rewards_promo()}
<section class="sec"><div class="wrap"><div class="head"><h2>Three ways to price your break</h2></div><div class="tiers">{tiers}</div></div></section>
<section class="sec tint"><div class="wrap"><div class="head"><h2>Four taps, no queue</h2></div><div class="steps">{steps}</div></div></section>{visit_section()}'''


# ---------------------------------------------------------------- Menu
FILTERS = [("budget", "₱35 and under"), ("cf", "Caffeine free")]


def passes_filter(d, key):
    if key == "budget":
        return d["p"] <= 35
    return bool(d.get("cf") or d.get("nc"))


def passes_all(d, skip_category=False):
    if not (skip_category or M["cat"] == "all" or d["cat"] == M["cat"]):
        return False
    if M["q"] and M["q"].lower() not in (d["n"] + d["d"]).lower():
        return False
    return all(passes_filter(d, k) for k in M["fs"])


def draw_controls():
    """Redraw the filter chips and category tabs (their counts change as you filter)."""
    chips = "".join(f'<button class="chip" data-act="mf" data-f="{k}" aria-pressed="{pressed(k in M["fs"])}">{icon("check")}{label}</button>' for k, label in FILTERS)
    if M["fs"] or M["q"] or M["cat"] != "all":
        chips += '<button class="clr" data-act="clr">Clear all</button>'
    q("#cf").innerHTML = chips
    tabs = ""
    for c in [{"id": "all", "n": "All"}, *CATS]:
        n = len([d for d in D if passes_all(d, True) and (c["id"] == "all" or d["cat"] == c["id"])])
        tabs += f'<button class="tab" data-act="mc" data-c="{c["id"]}" aria-pressed="{pressed(M["cat"] == c["id"])}">{c["n"]}<small>{n}</small></button>'
    q("#cc").innerHTML = tabs


def menu(arg=""):
    if arg and any(c["id"] == arg for c in CATS):
        M["cat"] = arg
    return f'''<div class="wrap mh"><h1 style="font-size:clamp(40px,7vw,76px);margin-top:10px">The menu</h1><p>Drinks from ₱30. Pay by QR code, or at the cart in cash or another method.</p></div>
<div class="wrap">{order_again_card()}</div>
<div class="tools"><div class="wrap"><div class="tbar"><label class="search">{icon("search")}<input id="q" type="search" placeholder="Search drinks" aria-label="Search drinks" value="{esc(M["q"])}"></label><div class="filters" id="cf"></div></div>
<div class="tabs" id="cc" aria-label="Categories"></div></div></div>
<div class="wrap" id="ml" style="min-height:60vh"></div>'''


def menu_row(d):
    tag = f'<span class="tag" style="margin:6px 0 0;display:block">{d["t"]}</span>' if d.get("t") else ""
    return (f'<article class="row">{art(d)}<div><h3><a href="#/drink/{d["id"]}">{d["n"]}</a></h3><p>{d["d"]}</p>{tag}</div>'
            f'<div class="r"><span class="price">{peso(d["p"])}</span>'
            f'<button class="add" data-act="add" data-id="{d["id"]}" aria-label="Add {d["n"]} to bag">{icon("plus")} Add</button></div></article>')


def menu_list():
    """Redraw only the drink list when a filter or the search box changes."""
    found = [d for d in D if passes_all(d)]
    if not found:
        html = '''<div class="empty"><h2>No drinks match</h2><p>Try a different word or clear the filters to see everything that's brewing.</p>
<button class="btn pri" data-act="mreset">Reset filters</button></div>'''
    else:
        html = ""
        for c in CATS:
            rows = "".join(menu_row(d) for d in found if d["cat"] == c["id"])
            if rows:
                html += f'<section class="grp"><h2>{c["n"]}</h2><p>{c["s"]}</p><div class="list">{rows}</div></section>'
    q("#ml").innerHTML = html


def coming_soon(title, eyebrow="Coming next"):
    return (f'<div class="wrap"><div class="empty" style="padding:120px 0"><p class="eyebrow"><i>{eyebrow}</i></p>'
            f'<h2 style="margin-top:10px">{title}</h2><p>That page wandered off, but the cart is still open and the drinks are cold.</p>'
            f'<a class="btn pri" href="#/menu">Back to the menu</a></div></div>')


# ---------------------------------------------------------------- handlers (registered in main.py)
def on_add(btn, _e=None):
    """EVENT data-act="add": the Add button on every product card."""
    add_item(btn.getAttribute("data-id"))


def on_hslot(btn, _e=None):
    s = btn.getAttribute("data-s")
    S["slot"] = "" if S["slot"] == s else s
    for b in qa("#hs .slot"):
        b.setAttribute("aria-pressed", pressed(b.getAttribute("data-s") == S["slot"]))
    name = next((x["n"] for x in SLOTS if x["id"] == S["slot"]), "")
    toast("Pickup set to " + name if S["slot"] else "Pickup choice cleared")
    q("#hcta").innerHTML = hero_cta()


def on_filter(btn, _e=None):
    key = btn.getAttribute("data-f")
    M["fs"] = [k for k in M["fs"] if k != key] if key in M["fs"] else M["fs"] + [key]
    draw_controls()
    menu_list()


def on_category(btn, _e=None):
    M["cat"] = btn.getAttribute("data-c")
    draw_controls()
    menu_list()


def on_clear(*_):
    M.update({"cat": "all", "q": "", "fs": []})
    q("#q").value = ""
    draw_controls()
    menu_list()


def on_menu_input(value):
    M["q"] = value
    draw_controls()
    menu_list()


def on_hcat(btn, _e=None):
    """Homepage category tabs: remember the choice, update the pressed state, redraw only the product grid."""
    HC["cat"] = btn.getAttribute("data-c")
    for b in qa("#hcats .tab"):
        b.setAttribute("aria-pressed", pressed(b.getAttribute("data-c") == HC["cat"]))
    q("#hgrid").innerHTML = home_grid()
