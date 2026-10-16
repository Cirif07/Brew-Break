"""Shared app state, tiny DOM helpers and browser storage.

Every other module imports from here. Keeping the state in one dictionary (S) means
any event handler can read or change it, and then redraw the part of the page it affects.
"""
import html
import json

from pyscript import document, window
from pyodide.ffi import create_proxy

from data import VCAT

# ---------------------------------------------------------------- state
S = {
    "cart": [],          # items in the bag
    "slot": "",          # chosen pickup time id ("" = nothing chosen yet)
    "pay": "",           # chosen payment method id
    "stamps": 0,
    "wallet": [],        # vouchers (accounts only)
    "vapplied": "",      # voucher code applied to the bag
    "hist": [],          # stamp history (accounts only)
    "acct": None,        # the logged-in account record, or None for a guest
    "user": {"name": "", "mobile": ""},
    "order": None,       # the order being tracked
    "pending": None,     # stamps a guest can still claim after signing up
    "pay_ref": "",       # reference number of the payment in progress
    "last": "#/home",    # page to return to after logging in
}
M = {"cat": "all", "q": "", "fs": []}      # menu filters: category, search text, filter chips
CUS = {"id": None, "o": {}}                # drink currently being customized in the sheet


# ---------------------------------------------------------------- DOM helpers
def q(selector):
    """First element matching a CSS selector (or None)."""
    return document.querySelector(selector)


def qa(selector):
    """List of all elements matching a CSS selector."""
    return list(document.querySelectorAll(selector))


def esc(text):
    """Escape text before putting it in HTML (stops typed text from becoming code)."""
    return html.escape(str(text), quote=True)


def peso(n):
    s = f"{n:.2f}"
    return "₱" + (s[:-3] if s.endswith(".00") else s)


# Interface controls use Lucide (loaded in index.html). Names not listed here keep their Phosphor symbol
# (avatars, status badges, role badges and product glyphs).
LUCIDE = {"home": "house", "menu": "utensils", "live": "clock", "gift": "gift", "ticket": "ticket", "bag": "shopping-bag",
          "search": "search", "plus": "plus", "minus": "minus", "x": "x", "arrow": "arrow-right", "check": "check",
          "user": "user", "caret": "chevron-down", "signout": "log-out", "eye": "eye", "eyeoff": "eye-off",
          "timer": "history", "coffee": "coffee", "wallet": "wallet", "clock": "clock", "play": "play", "trash": "trash-2", "info": "info", "stamp": "stamp", "pencil": "pencil", "leaf": "leaf"}


def icon(name):
    """A Lucide icon (an <i> that lucide.createIcons() turns into an SVG), or a Phosphor symbol for names not in LUCIDE."""
    if name in LUCIDE:
        return f'<i data-lucide="{LUCIDE[name]}" class="ic" aria-hidden="true"></i>'
    return f'<svg class="ic"><use href="#i-{name}"/></svg>'


_toast_timer = None


def toast(message):
    """Show a short message at the bottom of the screen."""
    global _toast_timer
    el = q("#toast")
    el.textContent = message
    el.classList.add("on")
    if _toast_timer:
        window.clearTimeout(_toast_timer)
    _toast_timer = window.setTimeout(create_proxy(lambda: el.classList.remove("on")), 2200)


def later(fn, ms=20):
    """Run fn after a short delay (used so CSS transitions can start)."""
    return window.setTimeout(create_proxy(fn), ms)


# ---------------------------------------------------------------- storage
# localStorage can be blocked (private mode, sandboxes). We fall back to memory so nothing crashes.
_mem = {}
STORE_OK = True
try:
    window.localStorage.setItem("bb_t", "1")
    window.localStorage.removeItem("bb_t")
except Exception:
    STORE_OK = False


def store_get(key):
    try:
        v = window.localStorage.getItem(key)
        return v if v is not None else _mem.get(key)
    except Exception:
        return _mem.get(key)


def store_set(key, value):
    try:
        window.localStorage.setItem(key, value)
    except Exception:
        _mem[key] = value


def load_json(key, default):
    try:
        v = json.loads(store_get(key) or "null")
        return default if v is None else v
    except Exception:
        return default


def save_json(key, value):
    try:
        store_set(key, json.dumps(value))
    except Exception:
        pass


# ---------------------------------------------------------------- accounts (stored in this browser only)
def get_users():
    return load_json("bb_users", {})


def save_acct():
    """Write stamps, vouchers and history back to the logged-in account's record."""
    if not S["acct"]:
        return
    users = get_users()
    rec = users.get(S["acct"]["email"])
    if not rec:
        return
    rec["stamps"] = S["stamps"]
    rec["wallet"] = S["wallet"]
    rec["hist"] = S["hist"]
    save_json("bb_users", users)
    S["acct"] = rec


# ---------------------------------------------------------------- wallet (vouchers)
def guest_wallet():
    """Guests keep only reusable codes (like BREAK10), saved on this device."""
    saved = load_json("bb_gwallet", [])
    if not isinstance(saved, list):
        return []
    return [{"code": x["code"], "used": False} for x in saved
            if isinstance(x, dict) and VCAT.get(x.get("code"), {}).get("reuse")]


def save_wallet():
    """Accounts save the wallet with the account; guests save it on this device."""
    if S["acct"]:
        save_acct()
    else:
        save_json("bb_gwallet", S["wallet"])
