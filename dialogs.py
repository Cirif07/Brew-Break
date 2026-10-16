"""Pop-up screens (modal dialogs): the voucher chooser, confirmations, and in later parts the payment screens.

Every dialog is built the same way by show_dialog(): it adds a dim full-screen layer, keeps keyboard focus
inside the pop-up (Tab), closes on Esc or a click outside, and gives focus back when it closes.
"""
from pyscript import document, window
from pyodide.ffi import create_proxy

import cart
from data import VCAT
from state import S, esc, icon, later, q, toast

_last_focus = None
_timer = None                                    # id of the payment countdown (set by the payment screen)


def set_timer(timer_id):
    global _timer
    _timer = timer_id


def close_dialog(*_):
    """Remove the open dialog (if any) and give focus back to what had it before."""
    global _last_focus, _timer
    if _timer is not None:                       # stop the payment countdown if one is running
        window.clearInterval(_timer)
        _timer = None
    d = q("#dlg")
    if d:
        d.remove()
    if _last_focus is not None and hasattr(_last_focus, "focus"):
        _last_focus.focus()
    _last_focus = None


def show_dialog(inner_html, on_click, on_escape=None, focus_selector=None, trap=True, wrapper_class=""):
    """Open a dialog. on_click(event) receives every click inside the dim layer."""
    global _last_focus
    close_dialog()
    _last_focus = document.activeElement
    d = document.createElement("div")
    d.id = "dlg"
    d.className = "dlgwrap " + wrapper_class
    d.innerHTML = inner_html

    def clicked(event):
        on_click(event)

    def key(event):
        if event.key == "Escape":
            event.stopPropagation()                 # so Esc does not also close the bag behind it
            (on_escape or close_dialog)()
        elif event.key == "Tab" and trap:
            event.preventDefault()
            items = [b for b in d.querySelectorAll("button:not([disabled]),a")]
            if not items:
                return
            current = -1
            for i, el in enumerate(items):
                if el == document.activeElement:
                    current = i
            step = -1 if event.shiftKey else 1
            items[(current + step) % len(items)].focus()

    d.addEventListener("click", create_proxy(clicked))
    d.addEventListener("keydown", create_proxy(key))
    document.body.appendChild(d)
    target = (focus_selector and d.querySelector(focus_selector)) or d.querySelector("[data-x]") or d.querySelector("button")
    if target:
        target.focus()
    return d


def on_backdrop_or_close(event, close):
    """True when the click was on the dim background or on a [data-x] button (and closes in that case)."""
    if event.target.id == "dlg" or event.target.closest("[data-x]"):
        close()
        return True
    return False


# ---------------------------------------------------------------- confirmation (logout, delete account)
def confirm_box(title, body, ok_label, cancel_label="Cancel", danger=False, on_ok=None):
    kind = "danger" if danger else "pri"

    def clicked(event):
        if event.target.id == "dlg" or event.target.closest("[data-x]"):
            close_dialog()
        elif event.target.closest("[data-ok]"):
            close_dialog()
            if on_ok:
                on_ok()

    show_dialog(f'''<div class="dlg" role="alertdialog" aria-modal="true" aria-labelledby="dT" aria-describedby="dB"><h3 id="dT">{esc(title)}</h3><p id="dB">{esc(body)}</p>
<div class="dact"><button class="btn ghost" type="button" data-x>{esc(cancel_label)}</button><button class="btn {kind}" type="button" data-ok>{esc(ok_label)}</button></div></div>''', clicked)


# ---------------------------------------------------------------- voucher chooser (opens from the bag and checkout)
def voucher_option(item):
    v = cart.vdef(item["code"])
    if not v:
        return ""
    applied = S["vapplied"] == item["code"]
    reuse = ' <span class="vtag">Reusable</span>' if v.get("reuse") else ""
    if applied:
        side = '<div class="vside"><span class="vtag on">Applied</span><button type="button" class="vlink" data-unpick>Remove</button></div>'
    else:
        side = f'<button type="button" class="btn ghost vuse2" data-pick="{esc(item["code"])}">Use</button>'
    return (f'<div class="vopt{" on" if applied else ""}"><div><b>{esc(v["title"])}</b><small>{esc(v["desc"])}</small>'
            f'<code>{esc(item["code"])}</code>{reuse}</div>{side}</div>')


def open_voucher_dialog(*_):
    """A small screen listing the wallet vouchers, so nobody has to leave the bag or checkout."""
    avail = [w for w in S["wallet"] if not w["used"] and cart.vdef(w["code"])]
    listing = "".join(voucher_option(w) for w in avail) or '<p class="vmsg" style="margin:4px 0 6px">No vouchers in your wallet yet.</p>'

    def back_to_button():
        def focus():
            b = q("[data-act=vopen]")
            if b:
                b.focus()
        later(focus, 90)

    def shut():
        close_dialog()
        back_to_button()

    def clicked(event):
        if event.target.id == "dlg" or event.target.closest("[data-x]"):
            shut()
            return
        pick = event.target.closest("[data-pick]")
        if pick:
            S["vapplied"] = pick.getAttribute("data-pick")
            close_dialog()
            cart.vrefresh()
            toast("Voucher applied")
            back_to_button()
            return
        if event.target.closest("[data-unpick]"):
            S["vapplied"] = ""
            close_dialog()
            cart.vrefresh()
            toast("Voucher removed")
            back_to_button()
            return
        if event.target.closest("[data-redeem]"):
            close_dialog()
            cart.close_sheet()                       # the link then goes to the Vouchers page

    show_dialog(f'''<div class="dlg vdlg" role="dialog" aria-modal="true" aria-labelledby="dT"><h3 id="dT">Your vouchers</h3>
<p class="vsub">Choose one for this order. Only one voucher can be used per order.</p><div class="vlistd">{listing}</div>
<div class="dact"><button class="btn pri" type="button" data-x>Done</button></div>
<a class="vlink" href="#/vouchers" data-redeem style="display:inline-block;margin-top:14px">Redeem a new code</a></div>''',
                clicked, on_escape=shut, focus_selector="[data-pick]")
