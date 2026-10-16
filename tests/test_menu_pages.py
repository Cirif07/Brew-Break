"""Menu, product pages, filters, links, empty states and accessible names. Run from the project folder:  python tests/test_menu_pages.py"""
import ast, json, os, re, sys
from html.parser import HTMLParser
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakebrowser as fb
fb.install()
import data, state, cart, seo, views_browse as vb, views_checkout as vc, views_drink as vd, views_info as vi, views_account as va
from fakebrowser import El, REG
chk = fb.Checker(); S = state.S; M = state.M
state.toast = lambda m: None; cart.toast = state.toast
def btn(**a): return El(attrs={("data-" + k.replace("_", "-")): str(v) for k, v in a.items()})
def reset(): S["cart"] = []; S["vapplied"] = ""; S["slot"] = ""; S["pay"] = ""; S["acct"] = None; S["user"] = {}; REG.pop("#sheet.on", None)
EXPECT = {"mt": 4, "ic": 4, "fr": 3, "fb": 3, "bk": 2}

# ---- 1. counts, and every place that shows a product agrees with data.py
chk(len(data.D) == 16 and {c: len([d for d in data.D if d["cat"] == c]) for c in EXPECT} == EXPECT, "16 products: 4 / 4 / 3 / 3 / 2")
M.update(cat="all", q="", fs=[]); vb.draw_controls(); vb.menu_list(); menu_html = REG["#ml"].innerHTML
chk(menu_html.count('<article class="row">') == 16, "menu page lists 16 rows")
chk(re.findall(r"<h2>([^<]+)</h2>", menu_html) == [c["n"] for c in data.CATS], "menu groups appear under the 5 category headings in order")
ld_items = {i["name"]: i["offers"]["price"] for sec in seo.json_ld()["hasMenu"]["hasMenuSection"] for i in sec["hasMenuItem"]}
chk(len(ld_items) == 16, "search-engine menu data lists 16 items")
for d in data.D:
    card, row, page = vb.drink_card(d), vb.menu_row(d), vd.drink_page(d["id"])
    cname = next(c["n"] for c in data.CATS if c["id"] == d["cat"])
    price = f'₱{d["p"]}'
    chk(d["n"] in card and price in card and d["n"] in row and price in row, f'{d["n"]} {price}: card and menu row agree')
    chk(d["n"] in page and price in page and cname in page, f'{d["n"]}: detail page shows the same name, price and category ({cname})')
    chk(ld_items.get(d["n"]) == str(d["p"]), f'{d["n"]}: search-engine menu data has the same price')
    reset(); REG["#dadd"] = El(attrs={"data-id": d["id"]}); REG["#dq"] = El(); vd.DT["qty"] = 1; vd.on_add(REG["#dadd"])
    chk(len(S["cart"]) == 1 and S["cart"][0]["n"] == d["n"] and S["cart"][0]["u"] == d["p"], f'{d["n"]}: adding from the detail page puts name and price {price} in the bag')
# ---- 2. category browsing, search and filters (the menu page and the home tabs)
for cid, n in EXPECT.items():
    M.update(cat=cid, q="", fs=[]); chk(len([d for d in data.D if vb.passes_all(d)]) == n, f"menu category {cid}: {n} items")
    vb.HC["cat"] = cid; chk(vb.home_grid().count('class="dc') + vb.home_grid().count("<article") >= n, f"home tab {cid}: shows its {n} cards")
M.update(cat="all", q="matcha", fs=[]); got = [d["n"] for d in data.D if vb.passes_all(d)]
chk("Matcha Cloud" in got, f"search 'matcha' finds Matcha Cloud {got}")
M.update(q="zzzz"); chk(not [d for d in data.D if vb.passes_all(d)], "search with no match finds nothing")
M.update(q="", fs=["budget"]); chk({d["n"] for d in data.D if vb.passes_all(d)} == {d["n"] for d in data.D if d["p"] <= 35}, "budget filter = items at P35 or less")
M.update(q="", fs=[], cat="all")
# ---- 3. empty and populated states
reset(); chk("Your bag is empty" in vc.checkout(""), "checkout with an empty bag shows the empty state")
REG["#sheet"] = El(); cart.bag(); chk("Your bag is empty" in REG["#sheet"].innerHTML and "Browse the menu" in REG["#sheet"].innerHTML, "bag drawer empty state")
cart.add_item("bsp"); cart.bag(); chk("Brown Sugar Pearl" in REG["#sheet"].innerHTML and "₱45" in REG["#sheet"].innerHTML, "bag drawer populated state")
# ---- 4. no broken internal links
t = ast.parse(open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()); routes = set()
for nd in t.body:
    if isinstance(nd, ast.Assign) and getattr(nd.targets[0], "id", "") == "VIEWS": routes = {k.value for k in nd.value.keys}
ids = {d["id"] for d in data.D}; cats = {c["id"] for c in data.CATS}
reset(); pages = {"home": vb.home(), "menu": vb.menu(""), "about": vi.about(), "rewards": vi.rewards(), "vouchers": vi.vouchers(), "privacy": vi.privacy(), "terms": vi.terms(),
                  "footer": vb.footer_html(), "login": va.login(""), "register": va.register(""), "menu rows": menu_html, "drink": vd.drink_page("bsp")}
bad = []
for name, html in pages.items():
    for h in re.findall(r'href="(#/[^"]*)"', html):
        parts = h[2:].split("/"); r = parts[0]
        if r not in routes or (r == "drink" and (len(parts) < 2 or parts[1] not in ids)) or (r == "menu" and len(parts) > 1 and parts[1] not in cats): bad.append((name, h))
chk(not bad, f"all #/ links point at real pages ({len(routes)} routes) {bad}")
# ---- 5. images
chk(not data.PHOTOS, "no product photos are embedded (PHOTOS is empty): cards use icon tiles")
sprite = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
missing = [d["n"] for d in data.D if f'id="i-{data.GLYPH.get(d["id"]) or data.GLYPH[d["cat"]]}"' not in sprite]
chk(not missing, f"every product's icon tile exists in the icon sheet {missing}")
chk(all('<img' not in vb.drink_card(d) for d in data.D), "no <img> tags that could be broken")
# ---- 6. accessible names for controls
class Names(HTMLParser):
    def __init__(s): super().__init__(); s.stack = []; s.bad = []; s.labels = set(); s.inputs = []; s.in_label = 0
    def handle_starttag(s, tag, a):
        a = dict(a)
        if tag == "label":
            s.in_label += 1
            if a.get("for"): s.labels.add(a["for"])
        if tag in ("button", "a", "select", "input", "textarea"):
            if tag == "a" and "href" not in a: return
            if tag == "input" and a.get("type") in ("hidden",): return
            s.stack.append({"tag": tag, "a": a, "text": ""})
            if tag in ("input", "select", "textarea"):
                e = s.stack.pop(); e["wrapped"] = s.in_label > 0; s.inputs.append(e)
    def handle_data(s, d):
        for e in s.stack: e["text"] += d
    def handle_endtag(s, tag):
        if tag == "label": s.in_label -= 1
        if s.stack and s.stack[-1]["tag"] == tag:
            e = s.stack.pop()
            if not (e["a"].get("aria-label") or e["a"].get("title") or e["text"].strip()): s.bad.append(f'{tag} {e["a"].get("data-act") or e["a"].get("href")}')
unnamed = []
reset(); cart.add_item("bsp"); cart.add_item("ccc"); S["slot"] = "r"; cart.bag(); extra = {"bag": REG["#sheet"].innerHTML, "checkout": vc.checkout("")}
for name, html in {**pages, **extra}.items():
    p = Names(); p.feed(html); unnamed += [(name, b) for b in p.bad]
    unnamed += [(name, "input " + (i["a"].get("id") or i["a"].get("type", ""))) for i in p.inputs if not (i["a"].get("aria-label") or i["a"].get("id") in p.labels or i["wrapped"])]
chk(not unnamed, f"every button, link and field has an accessible name {unnamed[:6]}")
chk('aria-hidden="true"' in state.icon("plus"), "Lucide icons are rendered with aria-hidden")
chk('lang="en"' in sprite[:300], "page language is declared")
chk('class="skip"' in sprite, "a skip-to-content link exists")
chk('<main id="app"' in sprite and '<nav' in sprite and '<header' in sprite and '<footer' in sprite, "landmarks: header, nav, main, footer")
chk('prefers-reduced-motion' in open(os.path.join(ROOT, "style.css"), encoding="utf-8").read(), "CSS has a prefers-reduced-motion rule")
chk.done()
