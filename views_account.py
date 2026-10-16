"""Login, register and settings pages.

Async handlers: hashing a password takes a moment, so these handlers use `await`. main.py starts them with
asyncio.ensure_future(), and the page keeps working (the button just says "Logging in...") while the browser computes the hash.
"""
import re

import auth
import avatars
import cart
import dialogs
from data import AVC
from state import STORE_OK, S, esc, get_users, icon, later, q, qa, save_json, toast
from views_checkout import PH_MOBILE

from pyscript import window

EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]{2,}")
USERNAME = re.compile(r"[a-z0-9_.]{3,20}", re.I)
SWGRP = {"ready": "notif", "rewards": "notif", "promo": "notif", "receipts": "notif", "large": "a11y", "calm": "a11y"}
CURRENT = {"page": ""}                                    # "login" or "register", so Enter submits the right form


def goto(address):
    window.location.hash = address


# ---------------------------------------------------------------- small form helpers
def val(field):
    el = q("#f-" + field)
    return el.value if el else ""


def bad(field, message):
    q("#e-" + field).textContent = message
    el = q("#f-" + field)
    if el:
        el.setAttribute("aria-invalid", "true")


def clean(root="#af"):
    for el in qa(root + " .err"):
        el.textContent = ""
    for el in qa(root + " [aria-invalid]"):
        el.removeAttribute("aria-invalid")


def first_bad(root="#af"):
    el = q(root + " [aria-invalid=true]")
    if el:
        el.focus()
    return bool(el)


def busy(on, label):
    b = q("#sub")
    b.disabled = on
    b.textContent = label


def pw_field(field, label, auto, extra=""):
    return (f'<div class="field"><label for="f-{field}">{label}</label><div class="pw"><input id="f-{field}" type="password" autocomplete="{auto}">'
            f'<button type="button" class="eye" aria-label="Show password" data-act="eye">{icon("eye")}</button></div>{extra}<span class="err" id="e-{field}" role="alert"></span></div>')


def txt_field(field, label, kind, auto, mode=""):
    inputmode = f' inputmode="{mode}"' if mode else ""
    return f'<div class="field"><label for="f-{field}">{label}</label><input id="f-{field}" type="{kind}" autocomplete="{auto}"{inputmode}><span class="err" id="e-{field}" role="alert"></span></div>'


def auth_shell(heading, sub, form, alt):
    warn = "" if STORE_OK else '<p class="warn" role="status">This browser is blocking saved accounts, so an account you create here will be lost when you refresh the page.</p>'
    return f'''<div class="wrap"><div class="auth"><div class="rise"><h1>{heading}</h1><p class="sub">{sub}</p>{warn}{form}<p class="alt">{alt}</p></div>
<aside class="aside rise" style="--i:1"><div class="art" style="--c:#e3c8a6;height:190px;margin:0"><svg class="food" viewBox="0 0 256 256" aria-hidden="true"><use href="#i-tea-bag"/></svg></div><h2>Your break, remembered.</h2>
<div class="pk2">{icon("stamp")}<div><b>Stamps that stay</b><p>Every drink adds one, saved to your account.</p></div></div>
<div class="pk2">{icon("user")}<div><b>Checkout in a tap</b><p>Your name and number fill in for you.</p></div></div>
<div class="pk2">{icon("gift")}<div><b>Rewards that follow you</b><p>Vouchers and free drinks stay on your card.</p></div></div></aside></div></div>'''


def after_render():
    """Limit how long each box can be, so nobody pastes huge text into the page."""
    for selector, size in (("#f-name,#f-sname", 60), ("#f-email", 254), ("#f-mobile,#f-smobile", 20), ("#f-suser", 20), ("[type=password]", 128)):
        for el in qa(selector):
            el.maxLength = size


def guarded(job):
    """Run an async form handler; if anything unexpected fails, show a friendly message instead of nothing."""
    async def run():
        label = q("#sub").textContent if q("#sub") else ""
        try:
            await job()
        except Exception as err:
            window.console.error(str(err))
            if q("#sub"):
                busy(False, label)
            if q("#e-form"):
                q("#e-form").textContent = "Something went wrong. Please try again."
            else:
                toast("Something went wrong. Please try again.")
    return run()


# ---------------------------------------------------------------- Log in
def login(arg=""):
    CURRENT["page"] = "login"
    if S["acct"]:
        goto(S["last"])                              # already logged in: nothing to do here
        return ""
    return auth_shell("Welcome back", "Log in to see your stamps and order faster.",
                      f'''<div id="af">{txt_field("email", "Email or username", "text", "username")}{pw_field("pw", "Password", "current-password")}<label class="chk"><input type="checkbox" id="f-remember"><span>Keep me logged in on this device</span></label><span class="err" id="e-form" role="alert" style="display:block;margin:6px 0 10px"></span><button class="btn pri" id="sub" type="button" data-act="submit">Log in</button></div>''',
                      'New to Brew Break? <a class="lnk" href="#/register">Create an account</a>')


async def do_login():
    clean()
    ident, password = val("email").strip().lower(), val("pw")
    if not 3 <= len(ident) <= 254:
        bad("email", "Enter your email or username.")
    if not password:
        bad("pw", "Enter your password.")
    if first_bad():
        return
    rec = auth.find_acct(ident)
    key = rec["email"] if rec else ident              # one lockout counter per account, however they type it
    locked = auth.lock_left(key)
    if locked:
        q("#e-form").textContent = auth.try_msg(locked)
        return
    busy(True, "Logging in…")
    digest = await auth.hash_pw(password, rec["salt"] if rec else auth.DUMMY, rec.get("it") if rec else auth.NEW_IT)
    ok = bool(rec) and auth.safe_eq(digest, rec["hash"])
    busy(False, "Log in")
    if not ok:
        auth.note_fail(key)
        again = auth.lock_left(key)
        q("#e-form").textContent = auth.try_msg(again) if again else "Incorrect email, username or password."   # same text for both cases
        return
    auth.clear_fails(key)
    if (rec.get("it") or auth.OLD_IT) < auth.NEW_IT:  # quietly upgrade an older account to stronger hashing
        users = get_users()
        users[rec["email"]].update(await auth.new_cred(password))
        save_json("bb_users", users)
        rec = users[rec["email"]]
    auth.login_as(rec, False, q("#f-remember").checked)
    goto(S["last"])


# ---------------------------------------------------------------- Create account
def register(arg=""):
    CURRENT["page"] = "register"
    if S["acct"]:
        goto(S["last"])                              # already logged in: nothing to do here
        return ""
    meter = '<div class="meter" id="meter" aria-hidden="true"><i></i><i></i><i></i><i></i></div><span class="hint" id="mt">Choose a strong password.</span><ul class="rules" id="rules"><li>At least 8 characters</li><li>A letter and a number</li><li>Not a common password</li></ul>'
    return auth_shell("Create your account", "Save your details, collect stamps and skip the typing at checkout.",
                      f'''<div id="af">{txt_field("name", "Full name", "text", "name")}{txt_field("email", "Email", "email", "email", "email")}{txt_field("mobile", "Mobile number", "tel", "tel", "tel")}
{pw_field("pw", "Password", "new-password", meter)}{pw_field("pw2", "Confirm password", "new-password")}
<label class="chk"><input type="checkbox" id="f-terms"><span>I agree to the <a href="#/terms">Terms</a> and <a href="#/privacy">Privacy</a> policy.</span></label><span class="err" id="e-terms" role="alert" style="display:block;margin-bottom:10px"></span>
<span class="err" id="e-form" role="alert" style="display:block;margin-bottom:10px"></span><button class="btn pri" id="sub" type="button" data-act="submit">Create account</button></div>''',
                      'Already have an account? <a class="lnk" href="#/login">Log in</a>')


async def do_register():
    clean()
    name = " ".join(val("name").split())
    email, mobile, password = val("email").strip().lower(), val("mobile"), val("pw")
    if not auth.valid_name(name):
        bad("name", "Enter your real name using letters only (2 to 60 characters).")
    if not EMAIL.fullmatch(email) or len(email) > 254:
        bad("email", "Enter a valid email, like you@example.com.")
    elif email in get_users():
        bad("email", "An account with this email already exists. Try logging in.")
    if not PH_MOBILE.fullmatch(mobile.replace(" ", "").replace("-", "")):
        bad("mobile", "Enter a Philippine mobile number, like 0917 555 0192.")
    problem = auth.pw_error(password, {"name": name, "email": email})
    if problem:
        bad("pw", problem)
    if val("pw2") != password:
        bad("pw2", "Passwords do not match.")
    if not q("#f-terms").checked:
        bad("terms", "Please accept the terms to continue.")
    if first_bad():
        return
    busy(True, "Creating account…")
    cred = await auth.new_cred(password)
    users = get_users()
    users[email] = {"email": email, "name": name, "mobile": mobile.strip(), **cred, "avatar": avatars.rand_av(),
                    "wallet": [{"code": "WELCOME20", "used": False}], "stamps": 0, "hist": []}
    save_json("bb_users", users)
    busy(False, "Create account")
    auth.login_as(users[email])
    goto(S["last"])


def on_submit(*_):
    return guarded(do_login if CURRENT["page"] == "login" else do_register)


def on_enter(event):
    """Pressing Enter inside a text box submits the form (not for check boxes)."""
    event.preventDefault()
    return on_submit()


def on_eye(btn, _e=None):
    box = btn.previousElementSibling
    show = box.type == "password"
    box.type = "text" if show else "password"
    btn.setAttribute("aria-label", ("Hide" if show else "Show") + " password")
    btn.innerHTML = icon("eyeoff" if show else "eye")


def on_password_input(el):
    """Live password strength and the rule ticks while typing."""
    n = auth.strength(el.value)
    meter = q("#meter")
    meter.className = f"meter l{n}"
    for i, bar in enumerate(meter.children):
        bar.classList.toggle("on", i < n)
    if q("#rules"):
        q("#mt").textContent = (["", "Weak", "Okay", "Good", "Strong"][n] + " password") if n else "Choose a strong password."
        for i, ok in enumerate(auth.pw_rules(el.value)):
            q("#rules").children[i].classList.toggle("ok", ok)
    else:
        q("#mt").textContent = (["", "Weak", "Okay", "Good", "Strong"][n] + " password") if n else "Use at least 8 characters."


# ---------------------------------------------------------------- confirmations
def ask_logout(after=None):
    def done():
        auth.logout()
        if after:
            after()
    dialogs.confirm_box("Log out of Brew Break?", "Your stamps and vouchers stay saved to your account. You can log back in anytime.",
                        "Log out", "Stay logged in", on_ok=done)


def on_logout(*_):
    ask_logout()


def on_logout2(*_):
    ask_logout(lambda: goto("#/home"))


# ---------------------------------------------------------------- Settings
def sec(section_id, title, description, body):
    return f'<section class="sset" id="s-{section_id}"><div class="sl"><h2>{title}</h2><p>{description}</p></div><div class="sr">{body}</div></section>'


def switch(key, title, description, on):
    return (f'<div class="row2"><div><b>{title}</b><p>{description}</p></div><button type="button" role="switch" class="sw" aria-checked="{str(bool(on)).lower()}" '
            f'aria-label="{title}" data-act="sw" data-sw="{key}"></button></div>')


def field(field_id, label, value, extra=""):
    return f'<div class="field"><label for="f-{field_id}">{label}</label><input id="f-{field_id}" value="{esc(value)}" {extra}><span class="err" id="e-{field_id}" role="alert"></span></div>'


def settings(arg=""):
    a = S["acct"]
    if not a:
        goto("#/login")                              # settings need an account
        return ""
    p = auth.prefs_of(a)
    profile = (field("sname", "Full name", a["name"], 'autocomplete="name"')
               + field("suser", "Username", a["username"], 'autocomplete="username" autocapitalize="off" spellcheck="false"')
               + field("semail", "Email", a["email"], 'type="email" disabled')
               + field("smobile", "Mobile number", a["mobile"], 'type="tel" inputmode="tel" autocomplete="tel"')
               + '<button class="btn pri" id="save-profile" type="button" data-act="save-profile">Save profile</button>')
    password = (pw_field("cur", "Current password", "current-password")
                + pw_field("new", "New password", "new-password", '<div class="meter" id="meter" aria-hidden="true"><i></i><i></i><i></i><i></i></div><span class="hint" id="mt">Use at least 8 characters.</span>')
                + pw_field("new2", "Confirm new password", "new-password")
                + '<button class="btn pri" id="save-pw" type="button" data-act="save-pw">Update password</button>')
    notif = (switch("ready", "Order ready alerts", "Text me when my order is ready at the express shelf.", p["notif"]["ready"])
             + switch("rewards", "Rewards updates", "Tell me when I am close to a free drink.", p["notif"]["rewards"])
             + switch("promo", "Promotions", "New drinks and special offers.", p["notif"]["promo"])
             + switch("receipts", "Email receipts", "Send a receipt after every order.", p["notif"]["receipts"]))
    display = (switch("large", "Larger text", "Make text and buttons about 12% bigger.", p["a11y"]["large"])
               + switch("calm", "Reduce motion", "Turn off animations and transitions.", p["a11y"]["calm"]))
    delete = ('<button class="btn ghost" id="del-open" type="button" data-act="del-open">Delete my account…</button>'
              f'<div id="del-box" hidden>{pw_field("del", "Enter your password to confirm", "current-password")}<button class="btn danger" id="del-go" type="button" data-act="del-go">Permanently delete</button></div>')
    return f'''<div class="wrap setp"><div class="shead" id="sh">{avatars.head_html(a)}</div>
{sec("profile", "Profile", "Your name, username and contact details. Your mobile number fills in at checkout.", profile)}
{sec("password", "Password", "Choose a password you do not use anywhere else.", password)}
{sec("notifications", "Notifications", "Saved to your account. This demo does not send real messages.", notif)}
{sec("display", "Display", "Make the page easier to read.", display)}
{sec("delete", "Delete account", "Removes your account, stamps and vouchers from this browser. This cannot be undone.", delete)}</div>'''


def on_switch(btn, _e=None):
    key = btn.getAttribute("data-sw")
    on = btn.getAttribute("aria-checked") != "true"
    btn.setAttribute("aria-checked", str(on).lower())

    def change(rec):
        prefs = auth.prefs_of(rec)
        prefs[SWGRP[key]][key] = on
        rec["prefs"] = prefs
    auth.upd_acct(change)
    auth.apply_prefs(S["acct"])
    toast("Saved")


def on_save_profile(*_):
    clean("#s-profile")
    name, username, mobile = val("sname").strip(), val("suser").strip(), val("smobile")
    if not auth.valid_name(name):
        bad("sname", "Enter your real name using letters only (2 to 60 characters).")
    if not USERNAME.fullmatch(username):
        bad("suser", "Use 3 to 20 letters, numbers, dots or underscores.")
    elif any(u["email"] != S["acct"]["email"] and (u.get("username") or "").lower() == username.lower() for u in get_users().values()):
        bad("suser", "That username is already taken.")
    if not PH_MOBILE.fullmatch(mobile.replace(" ", "").replace("-", "")):
        bad("smobile", "Enter a Philippine mobile number, like 0917 555 0192.")
    if first_bad("#s-profile"):
        return
    auth.upd_acct(lambda rec: rec.update({"name": name, "username": username, "mobile": mobile.strip()}))
    S["user"] = {**S["user"], "name": name, "mobile": mobile.strip()}
    q("#sh").innerHTML = avatars.head_html(S["acct"])
    toast("Profile saved")


async def do_save_password():
    clean("#s-password")
    current, new, again = val("cur"), val("new"), val("new2")
    email = S["acct"]["email"]
    rec = get_users()[email]
    locked = auth.lock_left(email)
    if locked:
        bad("cur", auth.try_msg(locked))
        first_bad("#s-password")
        return
    if not current:
        bad("cur", "Enter your current password.")
    elif not await auth.check_pw(rec, current):
        auth.note_fail(email)
        bad("cur", auth.try_msg(auth.lock_left(email)) if auth.lock_left(email) else "Current password is incorrect.")
    else:
        auth.clear_fails(email)
    problem = auth.pw_error(new, {"name": S["acct"]["name"], "email": email})
    if problem:
        bad("new", problem)
    elif new == current:
        bad("new", "Your new password must be different from the current one.")
    if again != new:
        bad("new2", "Passwords do not match.")
    if first_bad("#s-password"):
        return
    cred = await auth.new_cred(new)
    auth.upd_acct(lambda r: r.update(cred))
    for field_id in ("cur", "new", "new2"):
        q("#f-" + field_id).value = ""
    on_password_input(q("#f-new"))
    toast("Password updated")


def on_save_password(*_):
    return guarded(do_save_password)


def on_delete_open(*_):
    q("#del-box").hidden = False
    q("#del-open").hidden = True
    q("#f-del").focus()


async def do_delete():
    clean("#s-delete")
    email = S["acct"]["email"]
    rec = get_users()[email]
    locked = auth.lock_left(email)
    if locked:
        bad("del", auth.try_msg(locked))
        first_bad("#s-delete")
        return
    if not val("del") or not await auth.check_pw(rec, val("del")):
        if val("del"):
            auth.note_fail(email)
        bad("del", auth.try_msg(auth.lock_left(email)) if auth.lock_left(email) else "Enter your current password to confirm.")
        first_bad("#s-delete")
        return
    auth.clear_fails(email)
    stamps, vouchers = S["stamps"], cart.wallet_avail()

    def delete_now():
        users = get_users()
        users.pop(email, None)
        save_json("bb_users", users)
        auth.logout()
        goto("#/home")
        toast("Your account was deleted")
    dialogs.confirm_box("Delete your account?",
                        f'This permanently removes your account, your {stamps} stamp{"" if stamps == 1 else "s"} and {vouchers} voucher{"" if vouchers == 1 else "s"}. This cannot be undone.',
                        "Yes, delete account", "Keep my account", danger=True, on_ok=delete_now)


def on_delete(*_):
    return guarded(do_delete)


def on_avatar_edit(*_):
    avatars.open_avatar_dialog()
