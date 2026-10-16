"""About, Rewards, Vouchers, Privacy and Terms pages.

The Vouchers page is where codes are typed and redeemed. The wallet list there and the voucher screen in the bag
both read the same S["wallet"], so a redeemed code shows up in both.
"""
import cart
from data import D, PERKS
from state import S, esc, icon, peso, q
from views_browse import visit_section


# ---------------------------------------------------------------- Rewards
def perks_html():
    items = "".join(f'<div class="perk"><b>{title}</b><p>{text}</p></div>' for title, text in PERKS["everyone"])
    return f'<section><h2 style="font-size:34px">How rewards work</h2><div style="margin-top:14px">{items}</div></section>'


def rewards(arg=""):
    n = S["stamps"]
    left = 10 - n
    free_n = len([w for w in S["wallet"] if w["code"].startswith("FREE-") and not w["used"]])
    hist = S["hist"]
    login_note = "" if S["acct"] else ('<p style="margin-top:16px;color:var(--mut)">Log in to keep your stamps and vouchers between visits. '
                                       '<a class="lnk" href="#/login">Log in</a> or <a class="lnk" href="#/register">create an account</a>.</p>')
    passport = "".join(f'<div class="stc"><div class="st {"f" if i < n else ""}">{icon("check") if i < n else i + 1}</div>{"Today" if i < n else ""}</div>' for i in range(10))
    if S["acct"]:
        if free_n:
            note = f'You have {free_n} free drink voucher{"s" if free_n > 1 else ""} in your wallet. <a class="lnk" href="#/vouchers">Use {"one" if free_n > 1 else "it"}</a>.'
        else:
            note = "When your card fills up, a free drink voucher is added to your wallet automatically."
    else:
        note = "Order while logged in so your stamps are saved."
    history = ("".join(f'<div class="hist"><span>{h[0]}</span><span>{h[1]}</span><b>{h[2]}</b></div>' for h in hist)
               or '<p style="color:var(--mut)">No stamps yet. Your first order starts your card.</p>')
    return f'''<div class="wrap"><div style="padding:clamp(36px,6vw,64px) 0 0"><h1 style="font-size:clamp(40px,7vw,76px);margin-top:10px">Rewards</h1>{login_note}
<div class="stats"><div><b>{n}/10</b><span>stamps collected</span></div><div><b>{cart.wallet_avail()}</b><span>active vouchers</span></div><div><b>{peso(0)}</b><span>cart credit</span></div></div></div>
<div class="rw"><section><h2 style="font-size:34px">Buy 10, the 11th is free</h2><p style="color:var(--mut);margin-top:8px">Every drink you order with an account earns one stamp. Stamps stay on your card until you use them.</p>
<div class="pp">{passport}</div>
<div class="box" style="display:flex;gap:14px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin:0"><b>{left} more drink{"s" if left > 1 else ""} until your next free drink voucher.</b><a class="btn pri" href="#/menu">Order to earn stamps</a></div>
<p class="fine">{note} Each voucher covers one drink only.</p></section>
{perks_html()}</div>
<section style="padding-bottom:20px"><h2 style="font-size:30px;margin-bottom:14px">Recent stamps</h2>{history}</section></div>'''


# ---------------------------------------------------------------- Vouchers
def voucher_card(item):
    v = cart.vdef(item["code"])
    if not v:
        return ""
    stub = peso(v["value"]) if v["type"] == "amt" else f'{v["value"]}%' if v["type"] == "pct" else "FREE"
    applied = S["vapplied"] == item["code"]
    reuse = ' <span class="vtag">Reusable</span>' if v.get("reuse") else ""
    if item["used"]:
        action = '<span class="vtag">Used</span>'
    elif applied:
        action = '<span class="vtag on">Applied</span><button class="vlink" type="button" data-act="vremove">Remove</button>'
    else:
        action = f'<button class="btn pri vuse" type="button" data-act="vuse" data-code="{esc(item["code"])}">Use in my bag</button>'
    return (f'<article class="vc{" used" if item["used"] else ""}"><div class="stub">{stub}</div><div class="bd"><h3>{esc(v["title"])}</h3><p>{esc(v["desc"])}</p>'
            f'<p><code>{esc(item["code"])}</code>{reuse}</p><div class="vact">{action}</div></div></article>')


def voucher_cards():
    if not S["acct"]:                                  # guests see the reusable codes they redeemed on this device
        cards = f'<div class="vgrid">{"".join(voucher_card(w) for w in S["wallet"])}</div>' if S["wallet"] else ""
        saved = "Codes you redeem are saved on this device. " if S["wallet"] else ""
        return (f'{cards}<div class="vempty" style="margin-top:{20 if S["wallet"] else 0}px"><p>{saved}Log in to keep welcome and reward vouchers in your wallet too.</p>'
                '<a class="btn pri" href="#/login">Log in</a></div>')
    if not S["wallet"]:
        return '<p class="vmsg">No vouchers yet. Complete a stamp card on the Rewards page to earn a free drink voucher.</p>'
    ordered = sorted(S["wallet"], key=lambda w: 1 if w["used"] else 0)          # unused first
    return f'<div class="vgrid">{"".join(voucher_card(w) for w in ordered)}</div>'


def refresh_voucher_list():
    q("#vlist").innerHTML = voucher_cards()


def vouchers(arg=""):
    back = '<a class="btn pri" style="margin-bottom:30px" href="#/checkout">Back to checkout</a>' if S["cart"] else ""
    applied = f'In your bag: {esc(S["vapplied"])}.' if S["vapplied"] else ""
    return f'''<div class="wrap vp"><h1>Vouchers</h1><p class="sub">Redeem a code or pick a voucher from your wallet, then check out.</p>{back}
<section class="vcode" data-vbox><h2>Redeem a code</h2><div class="vrow"><input class="vin" maxlength="24" autocomplete="off" autocapitalize="characters" spellcheck="false" aria-label="Voucher code" placeholder="Enter your code"><button class="btn pri vbtn" type="button" data-act="vapply">Redeem</button></div><p class="vmsg" role="alert">{applied}</p></section>
<section class="vsec"><h2>Your vouchers</h2><div id="vlist">{voucher_cards()}</div></section></div>'''


# ---------------------------------------------------------------- About and contact
def about(arg=""):
    """About page. Everything here comes from the business description and from data.py; nothing is invented."""
    prices = [d["p"] for d in D]
    cards = "".join(f'<div class="step"><h3>{t}</h3><p>{x}</p></div>' for t, x in [
        ("Good-tasting drinks and food", f"{len(D)} items across milk tea, iced coffee, fruit refreshers, frappes and bakes."),
        ("Student-friendly prices", f"Everything on the menu costs between {peso(min(prices))} and {peso(max(prices))}."),
        ("Convenient ordering", "Browse the menu, build a bag and choose a pickup window before you walk over.")])
    flow = "".join(f'<div class="step"><h3>{t}</h3><p>{x}</p></div>' for t, x in [
        ("Browse", "Search the menu or filter by category."),
        ("Add to bag", "Change quantities and see the total update."),
        ("Choose a time", "Pick a pickup window and enter a name for the order."),
        ("Collect", "Show the handover PIN at the express counter.")])
    return f'''<div class="wrap"><div style="padding:clamp(36px,6vw,64px) 0 0"><p class="eyebrow"><i>About</i></p><h1 style="font-size:clamp(40px,7vw,76px);margin:10px 0 18px">About Brew Break</h1>
<p class="lead" style="color:var(--mut);max-width:60ch;font-size:18px">Brew Break is a proposed mobile coffee and beverage cart for students at Cebu Eastern College, especially around the College of Information Technology building and nearby walkways.</p></div></div>
<section class="sec" aria-labelledby="ab1"><div class="wrap"><div class="head"><h2 id="ab1">What we care about</h2></div><div class="steps">{cards}</div></div></section>
<section class="sec tint" aria-labelledby="ab2"><div class="wrap"><div class="head"><h2 id="ab2">How this website supports the business</h2></div><div class="steps">{flow}</div>
<p class="fine demo-note" style="margin-top:22px"><b>Student project.</b> This site is a demonstration. No real payment is taken, nothing is sent to a shop, and the order tracker is a simulation.</p></div></section>{visit_section()}'''


# ---------------------------------------------------------------- Privacy and Terms
def privacy(arg=""):
    return '''<div class="wrap"><article class="prose"><p class="eyebrow"><i>Last updated October 2026</i></p><h1>Privacy</h1><p>This website is a student project demonstration of a pre-order service for Brew Break, a proposed cart at Cebu Eastern College. It has no server: what you enter stays in your own browser.</p>
<h2>What is stored, and where</h2><ul><li>Your bag, pickup choice and last order, saved in this browser's storage so a refresh does not lose them.</li><li>If you create an account: your name, username, optional mobile number, a salted password hash, stamps and vouchers, saved in this browser only.</li><li>Payment: no real payment is taken, and no card or wallet details are asked for or stored.</li></ul>
<h2>What is not done</h2><p>This site's own code sends nothing to a server, a shop or anyone else. The page does load fonts, icons, the PyScript runtime and a QR library from public content-delivery networks, which can see your IP address when they load.</p>
<h2>Clearing it</h2><p>You can delete your account in Settings, or clear this site's storage in your browser settings. Questions: hello@brewbreak.ph.</p></article></div>'''


def terms(arg=""):
    return '''<div class="wrap"><article class="prose"><p class="eyebrow"><i>Last updated October 2026</i></p><h1>Terms</h1><p>This is a student project demonstration. The terms below describe how the demo behaves. They are not an agreement with a real business.</p>
<h2>Pickup</h2><p>Choose a pickup window when you order. The order page shows a handover PIN.</p>
<h2>Payment</h2><p>No real payment is taken. Cashless shows a sample QR code, and Pay at the cart means paying when you collect, in cash or another method.</p>
<h2>Vouchers and stamps</h2><p>Each drink ordered with an account earns one stamp; bakes earn none. Ten stamps add a free-drink voucher that covers one drink, up to ₱62. BREAK10 takes ₱10 off an order. Vouchers have no cash value.</p>
<h2>Allergens</h2><p>Drinks and bakes may contain milk, soy, nuts, gluten or caffeine. Ask the counter about any allergy before you order.</p></article></div>'''
