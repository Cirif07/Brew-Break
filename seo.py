"""Search and sharing information: one title and description per page, and machine-readable data about the cafe and its menu.

JSON-LD is a block of structured data that search engines read to understand the business (opening hours, menu, prices).
"""
import json

import cart
from data import BIZ, CATS, D
from state import q

META = {
    "home": ("Brew Break — drinks ready when you are", "Order Brew Break drinks and bakes ahead and choose a pickup time. Student-friendly prices at Cebu Eastern College."),
    "menu": ("Menu — Brew Break", f"All {len(D)} drinks and bakes, from ₱{min(d['p'] for d in D)}. Search and filter by category."),
    "vouchers": ("Vouchers — Brew Break", "Redeem a voucher code or use one from your wallet."),
    "rewards": ("Rewards — Brew Break", "Collect a stamp with every drink. Ten stamps add a free-drink voucher."),
    "live": ("Your order — Brew Break", "Follow your order and show your PIN at the express counter."),
    "checkout": ("Checkout — Brew Break", "Choose your pickup time and place a demo pre-order."),
    "login": ("Log in — Brew Break", "Log in to see your stamps, vouchers and past orders."),
    "register": ("Create an account — Brew Break", "Save your details, collect stamps and skip the typing at checkout."),
    "settings": ("Settings — Brew Break", "Manage your profile, password, notifications and display options."),
    "privacy": ("Privacy — Brew Break", "What this demo website stores in your browser."),
    "about": ("About — Brew Break", "Brew Break is a proposed student-friendly drink cart for Cebu Eastern College. Find out what we serve and where."),
    "terms": ("Terms — Brew Break", "How the demo handles pickup, payment, vouchers and allergy information."),
}


def set_page_meta(route_name, arg):
    """Update the tab title and the description tags, and announce the new page to screen readers."""
    m = META.get(route_name)
    if route_name == "drink":
        d = cart.find(arg)
        m = (f"{d['n']} — Brew Break", f"{d['d']} From ₱{d['p']}.") if d else META["home"]
    m = m or ("Page not found — Brew Break", "This page could not be found.")
    q("title").textContent = m[0]
    for selector, value in (("meta[name=description]", m[1]), ('meta[property="og:title"]', m[0]), ('meta[property="og:description"]', m[1]),
                            ('meta[name="twitter:title"]', m[0]), ('meta[name="twitter:description"]', m[1])):
        el = q(selector)
        if el:
            el.setAttribute("content", value)
    live = q("#live")
    if live:
        live.textContent = m[0]


def json_ld():
    """The cafe, its opening hours and its whole menu as schema.org data."""
    sections = [{"@type": "MenuSection", "name": c["n"], "description": c["s"],
                 "hasMenuItem": [{"@type": "MenuItem", "name": d["n"], "description": d["d"],
                                  "offers": {"@type": "Offer", "price": str(d["p"]), "priceCurrency": "PHP"}}
                                 for d in D if d["cat"] == c["id"]]} for c in CATS if any(d["cat"] == c["id"] for d in D)]
    prices = [d["p"] for d in D]
    address = {"@type": "PostalAddress", "addressLocality": BIZ["city"].split(",")[0].strip(), "addressCountry": "PH"}
    if BIZ["address"]:
        address["streetAddress"] = BIZ["address"]
    data = {"@context": "https://schema.org", "@type": "CafeOrCoffeeShop", "name": "Brew Break", "description": META["home"][1],
            "email": BIZ["email"], "address": address, "priceRange": f"₱{min(prices)}–₱{max(prices)}", "paymentAccepted": ", ".join(BIZ["pay"]),
            "openingHoursSpecification": [{"@type": "OpeningHoursSpecification", "dayOfWeek": BIZ["schedule"]["days"],
                                           "opens": BIZ["schedule"]["opens"], "closes": BIZ["schedule"]["closes"]}],
            "hasMenu": {"@type": "Menu", "name": "Brew Break menu", "hasMenuSection": sections}}
    if BIZ["phone"]:
        data["telephone"] = BIZ["phone"]
    return data


def inject_json_ld():
    from pyscript import document
    tag = document.createElement("script")
    tag.type = "application/ld+json"
    tag.textContent = json.dumps(json_ld(), ensure_ascii=False)
    document.head.appendChild(tag)
