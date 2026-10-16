"""Accounts and security (a browser-only demo: accounts live in this browser's storage).

What is protected, and how:
  * Passwords are never stored. We store a salted PBKDF2-SHA256 hash (600,000 rounds) made with the browser's WebCrypto.
  * Compare hashes in constant time, so timing cannot reveal how much of a guess was right.
  * Five wrong tries lock that account for a while (30 s, doubling up to 15 min), whether they typed the email or the username.
  * The same error message is shown for "no such account" and "wrong password", so it cannot be used to find who has an account.
  * Sessions expire (8 hours, or 14 days with "keep me logged in").
A real shop needs a server for all of this: anyone with access to this browser can still read or edit what is stored.
"""
import hmac
import json
import secrets
import time
import unicodedata

from pyscript import window
from pyodide.ffi import to_js

import cart
import orders
from data import COMMON, DEF_AV
from state import S, esc, get_users, guest_wallet, icon, load_json, q, qa, save_acct, save_json, store_get, store_set, toast
import avatars

OLD_IT, NEW_IT = 120000, 600000
DUMMY = "0" * 32                                   # used so unknown accounts take as long to check as real ones


# ---------------------------------------------------------------- hashing (WebCrypto)
async def hash_pw(password, salt, iterations=None):
    """PBKDF2-SHA256 as a hex string. Older accounts used 120,000 rounds and are upgraded when they log in."""
    iterations = iterations or OLD_IT
    try:
        enc = window.TextEncoder.new()
        key = await window.crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", False, to_js(["deriveBits"]))
        params = to_js({"name": "PBKDF2", "hash": "SHA-256", "salt": enc.encode(salt), "iterations": iterations},
                       dict_converter=window.Object.fromEntries)
        bits = await window.crypto.subtle.deriveBits(params, key, 256)
        return bytes(window.Uint8Array.new(bits).to_py()).hex()
    except AttributeError:                           # very old browser without WebCrypto: weak fallback (demo only)
        h = 5381
        for ch in salt + password:
            h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
        return "x" + str(h - (1 << 32) if h >= (1 << 31) else h)


def safe_eq(a, b):
    return hmac.compare_digest(str(a).encode(), str(b).encode())


async def check_pw(rec, password):
    return safe_eq(await hash_pw(password, rec["salt"], rec.get("it")), rec["hash"])


async def new_cred(password):
    salt = secrets.token_hex(16)
    return {"salt": salt, "hash": await hash_pw(password, salt, NEW_IT), "it": NEW_IT}


# ---------------------------------------------------------------- lockout after repeated wrong passwords
def now_ms():
    return int(time.time() * 1000)


def lock_left(key):
    f = load_json("bb_fails", {}).get(key)
    return -(-(f["until"] - now_ms()) // 1000) if f and f.get("until", 0) > now_ms() else 0


def note_fail(key):
    fails, now = load_json("bb_fails", {}), now_ms()
    f = fails.get(key) or {"n": 0, "until": 0, "t": 0}
    if now - f["t"] > 9e5:                           # forget old mistakes after 15 minutes
        f = {"n": 0, "until": 0, "t": 0}
    f["n"] += 1
    f["t"] = now
    if f["n"] >= 5:
        f["until"] = now + int(min(900, 30 * 2 ** (f["n"] - 5)) * 1000)
    fails[key] = f
    save_json("bb_fails", fails)


def clear_fails(key):
    fails = load_json("bb_fails", {})
    fails.pop(key, None)
    save_json("bb_fails", fails)


def try_msg(seconds):
    return f'Too many attempts. Try again in {seconds} second{"" if seconds == 1 else "s"}.'


# ---------------------------------------------------------------- sessions
def start_session(email, remember):
    save_json("bb_session", {"em": email, "exp": now_ms() + (12096e5 if remember else 288e5)})


def read_session():
    x = load_json("bb_session", None)
    return x["em"] if isinstance(x, dict) and x.get("exp", 0) > now_ms() else None


# ---------------------------------------------------------------- what makes a good name and password
def valid_name(name):
    """2 to 60 characters, starts with a letter, at least two letters, only letters, spaces and ' . - allowed."""
    if not 2 <= len(name) <= 60 or unicodedata.category(name[0])[0] not in "LM":
        return False
    if sum(1 for c in name if unicodedata.category(c)[0] == "L") < 2:
        return False
    return all(unicodedata.category(c)[0] in "LM" or c in "'’ .-" for c in name)


def pw_rules(p):
    return [len(p) >= 8, any(c.isalpha() for c in p) and any(c.isdigit() for c in p), bool(p) and p.lower() not in COMMON]


def pw_error(p, who):
    if len(p) < 8:
        return "Use at least 8 characters."
    if len(p) > 128:
        return "Use 128 characters or fewer."
    if not (any("a" <= c.lower() <= "z" for c in p) and any(c.isdigit() for c in p)):
        return "Include at least one letter and one number."
    if p.lower() in COMMON:
        return "That password is too common. Choose something harder to guess."
    low = p.lower()
    bits = [*(who.get("name") or "").lower().split(), (who.get("email") or "").split("@")[0].lower()]
    if any(len(b) >= 4 and b in low for b in bits):
        return "Do not include your name or email in your password."
    return ""


def strength(p):
    n = 0
    if len(p) >= 8:
        n += 1
    if any(c.islower() for c in p) and any(c.isupper() for c in p):
        n += 1
    if any(c.isdigit() for c in p):
        n += 1
    if any(not c.isalnum() for c in p) or len(p) >= 12:
        n += 1
    return max(1, n) if p else 0


# ---------------------------------------------------------------- accounts
def find_acct(identifier):
    """Look an account up by email or by username."""
    users = get_users()
    if "@" in identifier:
        return users.get(identifier)
    return next((u for u in users.values() if (u.get("username") or "").lower() == identifier), None)


def migrate(rec):
    """Fill in anything an older account record is missing."""
    changed = False
    if not rec.get("username"):
        base = "".join(c for c in rec["email"].split("@")[0] if c.isalnum() or c in "_.")[:16] or "user"
        base = base + "_bb" if len(base) < 3 else base
        taken = {(u.get("username") or "").lower() for u in get_users().values() if u["email"] != rec["email"]}
        name, n = base, 0
        while name.lower() in taken:
            n += 1
            name = base + str(n)
        rec["username"], changed = name, True
    if not rec.get("role"):
        rec["role"], changed = "student", True
    if not rec.get("avatar"):
        rec["avatar"], changed = dict(DEF_AV), True
    if rec.get("wallet") is None:
        rec["wallet"] = [{"code": "WELCOME20", "used": False}] + [{"code": cart.new_free(), "used": False} for _ in range(rec.get("vouch") or 0)]
        rec["vouch"], changed = 0, True
    if changed:
        users = get_users()
        users[rec["email"]] = rec
        save_json("bb_users", users)
    return rec


def upd_acct(change):
    users = get_users()
    rec = users[S["acct"]["email"]]
    change(rec)
    save_json("bb_users", users)
    S["acct"] = rec
    draw_account()


def prefs_of(rec):
    p = rec.get("prefs") or {}
    return {"notif": {"ready": True, "rewards": True, "promo": False, "receipts": True, **p.get("notif", {})},
            "a11y": {"large": False, "calm": False, **p.get("a11y", {})}}


def apply_prefs(rec):
    """Larger text and Reduce motion are classes on the <html> element."""
    a11y = prefs_of(rec)["a11y"] if rec else {}
    classes = window.document.documentElement.classList
    classes.toggle("big", bool(a11y.get("large")))
    classes.toggle("calm", bool(a11y.get("calm")))


def draw_account():
    """The header's account area: avatar and log-out button, or a Log in link."""
    a = S["acct"]
    if a:
        html = (f'<a class="who" href="#/settings" aria-label="Account settings for {esc(a["name"])}" title="{esc(a["name"])}">{avatars.avatar_html(a.get("avatar"))}</a>'
                f'<button id="lo" aria-label="Log out" title="Log out" data-act="logout">{icon("signout")}</button>')
    else:
        html = '<a class="loginl" href="#/login">Log in</a>'
    q("#acct").innerHTML = html


def login_as(rec, quiet=False, remember=False):
    rec = migrate(rec)
    S["acct"] = rec
    S["user"] = {"name": rec["name"], "mobile": rec["mobile"]}
    S["stamps"] = (rec.get("stamps") or 0) + S["stamps"]
    S["wallet"] = rec.get("wallet") or []
    S["hist"] = [*S["hist"], *(rec.get("hist") or [])]
    cart.add_stamps(0)                               # an old full card becomes a voucher
    if not quiet:
        start_session(rec["email"], remember)
    save_acct()
    draw_account()
    apply_prefs(S["acct"])
    if not quiet:
        toast("Welcome, " + rec["name"].strip().split(" ")[0])
        orders.claim_pending()                       # stamps from an order placed as a guest


def logout(redraw=True):
    store_set("bb_session", "")
    S.update({"acct": None, "user": {"name": "", "mobile": ""}, "stamps": 0, "wallet": guest_wallet(), "vapplied": "", "hist": []})
    apply_prefs(None)
    draw_account()
    toast("You are logged out")
    if redraw:
        cart.HOOKS["route"]()


def restore_session():
    email = read_session()
    rec = email and get_users().get(email)
    if rec:
        login_as(rec, quiet=True)
    else:
        draw_account()
