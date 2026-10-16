"""Avatars: a Phosphor icon on a colour, as a circle or rounded square, picked from a small pop-up screen."""
import random

import dialogs
from data import AVC, AVG, DEF_AV
from state import S, esc, icon, later, q, toast


def rand_av():
    """New accounts start with a random ready-made avatar."""
    return {"g": random.choice(AVG)[0], "c": random.choice(AVC)[1], "s": "round"}


def avatar_html(av, size=""):
    av = av or DEF_AV
    glyph = next((g for g in AVG if g[0] == av.get("g")), AVG[0])
    colour = av["c"] if any(c[1] == av.get("c") for c in AVC) else AVC[0][1]          # only palette colours are ever used
    soft = " soft" if av.get("s") == "soft" else ""
    return f'<span class="av2 {size}{soft}" style="--c:{colour}" aria-hidden="true">{icon(glyph[1])}</span>'


def head_html(acct):
    """The big avatar with its pencil badge, the name and username, and the Log out button (top of Settings)."""
    return (f'<span class="avwrap">{avatar_html(acct.get("avatar"), "xl")}<button type="button" class="avedit" id="avedit" data-act="avedit" '
            f'aria-label="Edit avatar" title="Edit avatar">{icon("pencil")}</button></span>'
            f'<div><h1>{esc(acct["name"])}</h1><p class="sub2"><span>@{esc(acct["username"])}</span></p></div>'
            f'<button class="btn ghost" id="lo2" type="button" data-act="logout2">Log out</button>')


def avatar_body(acct):
    av = {**DEF_AV, **(acct.get("avatar") or {})}
    grid = "".join(
        f'<button type="button" class="avb" data-g="{g[0]}" aria-pressed="{str(av["g"] == g[0]).lower()}" aria-label="{g[2]}" title="{g[2]}">'
        f'{avatar_html({"g": g[0], "c": av["c"], "s": av["s"]}, "sm")}</button>' for g in AVG)
    colours = "".join(
        f'<button type="button" class="swc" style="--c:{c[1]}" data-c="{c[1]}" aria-pressed="{str(av["c"] == c[1]).lower()}" aria-label="{c[0]}" title="{c[0]}">{icon("check")}</button>'
        for c in AVC)
    return f'''<div class="avprev">{avatar_html(av, "lg")}<div><b>{esc(acct["name"])}</b><p class="fine" style="margin-top:2px">This is how you appear in the header.</p></div></div>
<b class="avl">Pick an avatar</b><div class="avgrid" role="group" aria-label="Avatars">{grid}</div>
<b class="avl">Colour</b><div class="cols" role="group" aria-label="Colours">{colours}</div>
<b class="avl">Shape</b><div class="seg" role="group" aria-label="Shape"><button type="button" data-s="round" aria-pressed="{str(av["s"] != "soft").lower()}">Circle</button><button type="button" data-s="soft" aria-pressed="{str(av["s"] == "soft").lower()}">Rounded square</button></div>'''


def open_avatar_dialog(*_):
    import auth                                       # imported here because auth also imports this module

    def shut():
        dialogs.close_dialog()
        edit = q("#avedit")
        if edit:
            edit.focus()

    def clicked(event):
        t = event.target
        if t.id == "dlg" or t.closest("[data-x]"):
            shut()
            return
        b = t.closest("[data-g],[data-c],[data-s]")
        if not b:
            return
        key = "g" if b.hasAttribute("data-g") else "c" if b.hasAttribute("data-c") else "s"
        value = b.getAttribute("data-" + key)
        auth.upd_acct(lambda rec: rec.update({"avatar": {**DEF_AV, **(rec.get("avatar") or {}), key: value}}))   # saved the moment you tap
        q("#avbody").innerHTML = avatar_body(S["acct"])
        sh = q("#sh")
        if sh:
            sh.innerHTML = head_html(S["acct"])
        again = q(f'#avbody [data-{key}="{value}"]')
        if again:
            again.focus()

    dialogs.show_dialog(f'''<div class="dlg avdlg" role="dialog" aria-modal="true" aria-labelledby="dT"><h3 id="dT">Choose your avatar</h3><div id="avbody">{avatar_body(S["acct"])}</div>
<div class="dact"><button class="btn pri" type="button" data-x>Done</button></div></div>''', clicked, on_escape=shut,
                        focus_selector=".avb[aria-pressed=true]")
