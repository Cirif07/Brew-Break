"""Brew Break: entry point (PyScript).

HOW EVENTS WORK HERE
Instead of attaching a listener to every button, we attach ONE listener per event type to the page
(click, input, keydown). Buttons carry a data-act="name" attribute; the handler looks that name up in
ACTIONS and calls the matching Python function. Buttons created later (menu rows, the bag drawer)
therefore work without any extra wiring. This is event delegation, a core event-driven pattern.

HOW PAGES CHANGE
The address bar uses #/page links. The browser fires "hashchange", route() reads the new address,
asks the right view for its HTML and puts it on the page.
"""
import asyncio

from pyscript import document, window, when
from pyodide.ffi import create_proxy

import auth
import cart
import dialogs
import orders
import payments
import seo
import views_account
import views_browse as vb
import views_checkout
import views_drink
import views_info
from data import D
from state import M, S, esc, guest_wallet, icon, later, q, toast

NAV = [("home", "Home", "home"), ("menu", "Menu", "menu"), ("live", "Orders", "live"),
       ("rewards", "Rewards", "gift"), ("vouchers", "Vouchers", "ticket")]
VIEWS = {"home": lambda arg: vb.home(), "menu": vb.menu, "drink": views_drink.drink_page,
         "checkout": views_checkout.checkout, "live": lambda arg: orders.live(),
         "login": views_account.login, "register": views_account.register, "settings": views_account.settings,
         "about": lambda arg: views_info.about(), "rewards": lambda arg: views_info.rewards(), "vouchers": lambda arg: views_info.vouchers(), "privacy": lambda arg: views_info.privacy(), "terms": lambda arg: views_info.terms()}
HIGHLIGHT = {"drink": "menu", "checkout": "menu"}
_first = True

# ---------------------------------------------------------------- router
def route_inner():
    global _first
    orders.stop_tracker()
    if S["acct"] and not auth.read_session():      # the login has expired
        auth.logout(redraw=False)
    parts = (window.location.hash.replace("#/", "") or "home").split("/")
    name, arg = parts[0], (parts[1] if len(parts) > 1 else "")
    if name not in ("login", "register"):
        S["last"] = window.location.hash or "#/home"
    view = VIEWS.get(name)
    if view:
        html = view(arg)
    else:
        html = vb.coming_soon("That cup is empty.", "Error 404")
    q("#app").innerHTML = f'<div class="view">{html}</div>'
    current = HIGHLIGHT.get(name, name)
    q("#links").innerHTML = "".join(
        f'<a href="#/{k}" {"aria-current=page" if k == current else ""} aria-label="{label}" title="{label}">{icon(i)}<span class="lt">{label}</span></a>'
        for k, label, i in NAV)
    q("#mtabs").innerHTML = "".join(f'<a href="#/{k}" {"aria-current=page" if k == current else ""}>{icon(i)}{label}</a>' for k, label, i in NAV)
    q("#foot").innerHTML = vb.footer_html()
    seo.set_page_meta(name, arg)
    window.scrollTo(0, 0)
    if not _first:
        q("#app").focus()
    _first = False
    if name == "home":
        vb.after_home()
    if name == "menu":
        vb.draw_controls()
        vb.menu_list()
    elif name == "checkout":
        views_checkout.after_render()
    elif name == "drink":
        views_drink.after_render()
    elif name == "live":
        orders.start_tracker()
    elif name in ("login", "register", "settings"):
        views_account.after_render()


def route(*_):
    """Draw the current page. If a page ever fails, show a friendly message instead of a blank screen."""
    try:
        route_inner()
    except Exception as err:
        window.console.error(str(err))
        q("#app").innerHTML = ('<div class="view"><div class="wrap"><div class="empty" style="padding:100px 0"><h2>Something went wrong</h2>'
                               '<p>Sorry about that. Your bag is saved. Try reloading the page.</p>'
                               '<button class="btn pri" type="button" data-act="reload">Reload the page</button></div></div></div>')


def reset_menu(*_):
    M.update({"cat": "all", "q": "", "fs": []})
    route()


# ---------------------------------------------------------------- events (one listener per event type)
ACTIONS = {
    "bag": cart.bag, "close": lambda t, e: cart.close_sheet(),
    "add": vb.on_add, "qty": cart.on_qty, "rm": cart.on_remove, "bagclear": cart.on_clear_bag,
    "bslot": cart.on_bslot, "bsugg": cart.on_bsugg, "again": cart.on_again,
    "vremove": cart.on_vremove, "vuse": cart.on_vuse, "vapply": cart.on_vapply, "vopen": dialogs.open_voucher_dialog,
    "hslot": vb.on_hslot, "hcat": vb.on_hcat, "mf": vb.on_filter, "mc": vb.on_category, "clr": vb.on_clear, "mreset": reset_menu,
    "reload": lambda t, e: window.location.reload(),
    # drink page
    "dqty": views_drink.on_qty, "dadd": views_drink.on_add,
    # checkout
    "cslot": views_checkout.on_slot, "cpay": views_checkout.on_pay, "sslot": views_checkout.on_suggest_slot,
    "spay": views_checkout.on_suggest_pay, "place": views_checkout.place,
    # orders
    "pickedup": orders.on_pickedup, "reorder": orders.on_reorder,
    # accounts
    "logout": views_account.on_logout, "logout2": views_account.on_logout2, "avedit": views_account.on_avatar_edit,
    "eye": views_account.on_eye, "submit": views_account.on_submit, "sw": views_account.on_switch,
    "save-profile": views_account.on_save_profile, "save-pw": views_account.on_save_password,
    "del-open": views_account.on_delete_open, "del-go": views_account.on_delete,
}
cart.HOOKS.update({"vlist": views_info.refresh_voucher_list, "sum": views_checkout.wire_summary, "route": lambda: route()})


def run(result):
    """Async handlers (payments, password hashing) return a coroutine; start it in the background."""
    if asyncio.iscoroutine(result):
        asyncio.ensure_future(result)


@when("click", "body")
def on_click(event):
    target = event.target.closest("[data-act]") if hasattr(event.target, "closest") else None
    if target:
        handler = ACTIONS.get(target.getAttribute("data-act"))
        if handler:
            run(handler(target, event))


@when("input", "body")
def on_input(event):
    if event.target.id == "q":                      # live menu search
        vb.on_menu_input(event.target.value)
    elif event.target.id in ("f-pw", "f-new") and q("#meter"):     # password strength while typing
        views_account.on_password_input(event.target)
    elif event.target.closest("#co") and event.target.getAttribute("name"):   # checkout fields: keep what is typed
        views_checkout.on_field_input(event.target)


@when("keydown", "body")
def on_keydown(event):
    if event.key == "Escape":
        cart.close_sheet()
    elif (event.key == "Enter" and event.target.tagName == "INPUT" and event.target.type != "checkbox"
          and event.target.closest("#af")):          # Enter submits the login / register form
        run(views_account.on_enter(event))
    elif event.key == "Enter" and event.target.classList.contains("vin"):      # Enter redeems the typed voucher code
        event.preventDefault()
        event.target.closest("[data-vbox]").querySelector("[data-act=vapply]").click()


# ---------------------------------------------------------------- start
S["wallet"] = guest_wallet()                       # vouchers a guest redeemed earlier on this device
restored = cart.restore_cart()                     # bring back a saved bag before the first draw
orders.restore_order()                             # ... and the order being tracked
orders.restore_pending()                           # ... and stamps a guest can still claim


def drop_unowned_voucher():
    """A saved bag must not keep a one-time voucher that is not really in the wallet (saved data can be edited by hand)."""
    code = S["vapplied"]
    v = cart.vdef(code) if code else None
    if v and not v.get("reuse") and not any(w["code"] == code and not w["used"] for w in S["wallet"]):
        S["vapplied"] = ""


cart.render_bag()
auth.restore_session()                             # log back in if a session is saved
drop_unowned_voucher()
route()
seo.inject_json_ld()                               # cafe + menu data for search engines
window.addEventListener("hashchange", create_proxy(route))
window.addEventListener("pagehide", create_proxy(lambda e: cart.persist()))
document.addEventListener("visibilitychange", create_proxy(lambda e: cart.persist() if document.hidden else None))
window.setInterval(create_proxy(cart.persist), 3000)
if restored:
    later(lambda: toast("We saved your bag for you"), 700)
