"""Pure-data check of the official menu. Needs only Python 3: run `python tests/check_menu.py` from the project folder."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import data

OFFICIAL = [
    ("mt", "Milk Tea", [("Brown Sugar Pearl", 45), ("Wintermelon Cream Cheese", 48), ("Okinawa Grass Jelly", 40), ("Taro Velvet Pearl", 45)]),
    ("ic", "Iced Coffee", [("Creamy Spanish Iced Coffee", 45), ("Creamy Barako Iced Brew", 30), ("Iced Vanilla Americano", 35), ("Caramel Macchiato", 50)]),
    ("fr", "Fruit Refreshers", [("Strawberry Lychee Fizz", 38), ("Mango Passion Cooler", 35), ("Honey Calamansi Tea", 32)]),
    ("fb", "Frappes", [("Cookies and Cream", 58), ("Java Chip Blended", 62), ("Matcha Cloud", 60)]),
    ("bk", "Bakes", [("Choco Chip Chunk", 25), ("Cheesy Ensaymada Mini", 28)]),
]
ok = True
def check(c, m):
    global ok; ok &= bool(c); print(("PASS " if c else "FAIL ") + m)

check(len(data.D) == 16, f"exactly 16 products ({len(data.D)})")
check(len({d["id"] for d in data.D}) == 16, "product ids are unique")
check([c["id"] for c in data.CATS] == [o[0] for o in OFFICIAL], "5 categories in the official order")
for cid, cname, items in OFFICIAL:
    check([c["n"] for c in data.CATS if c["id"] == cid] == [cname], f"category name {cname}")
    got = [(d["n"], d["p"]) for d in data.D if d["cat"] == cid]
    check(got == items, f"{cname}: {len(got)} items, names and prices match the official list")
html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
nos = re.findall(r"<li>([^<]+?), ₱(\d+)</li>", html)
check(nos == [(n, str(p)) for _, _, it in OFFICIAL for n, p in it], "no-JavaScript menu list in index.html matches")
print("ALL OK" if ok else "FAILURES"); sys.exit(0 if ok else 1)
