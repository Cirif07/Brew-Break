# PyScript demonstration guide (for the group)

How the page starts: `index.html` loads `main.py` with `pyscript.toml` (`<script type="py" ...>`). `main.py` registers **three** listeners with PyScript's `@when` decorator: `click`, `input`, `keydown` on `body` (`main.py` lines 129-165 area), plus the router's `hashchange`. A click on any element with `data-act="name"` is looked up in the `ACTIONS` table (39 entries) and the matching Python function runs. Line numbers below are for the files in this repo; re-check them if the code moves.

| # | Demo | What triggers it | PyScript handler | Data read / changed | How the page updates | Business purpose |
|---|---|---|---|---|---|---|
| 1 | Category tabs on Home | Click a tab (`data-act="hcat"`) | `views_browse.on_hcat` (line 296) | reads the tab's `data-c`; changes `HC["cat"]` | tab `aria-pressed` flips; only `#hgrid` is redrawn with that category's cards | Students find the kind of drink they want quickly |
| 2 | Live menu search | Typing in the search box (`input` event) | `main.on_input` -> `views_browse.on_menu_input` (line 290) | reads the text; changes `M["q"]` | filters and the list are redrawn on every keystroke | Browse 16 items without scrolling |
| 3 | Add to bag | Click Add (`data-act="add"`) | `views_browse.on_add` -> `cart.add_item` (line 65) | reads the item from `D`; changes `S["cart"]` (max 20 per item) | `cart.refresh_views` (line 99) updates the header total, the bag drawer and the checkout summary; a toast confirms | Build an order |
| 4 | Quantity, remove, clear | Click +, -, Remove, Clear bag | `cart.on_qty` (408), `cart.on_remove` (425), `cart.on_clear_bag` (437; two taps) | changes `S["cart"]` | same `refresh_views`; empty state appears when the bag is empty | Fix mistakes before ordering |
| 5 | Calculations | Any bag change | `cart.sub` (43), `cart.disc` (157), `cart.due` (161), `cart.vcalc` (128) | reads `S["cart"]`, `S["vapplied"]`; nothing stored | subtotal, voucher line and total are recomputed from the same data everywhere | Correct pesos at checkout |
| 6 | Pickup time on Home | Click a pickup window (`data-act="hslot"`) | `views_browse.on_hslot` (line 260) | changes `S["slot"]` | slot buttons update and the hero button text changes | Plan the break around class time |
| 7 | Checkout form validation and submission | Click Confirm pre-order (`data-act="place"`) | `views_checkout.place` (line 98) -> `orders.commit_order` (line 25) | reads slot, payment, name (and mobile for account holders); creates `S["order"]`, empties the bag | error text appears beside the bad field and it gets focus; on success the page goes to the order screen | Hand the cart a clear order |
| 8 | Order status timer (simulation) | A repeating timer every 7 seconds | `orders.start_tracker` (line 172), `window.setInterval` through `create_proxy` | changes the stage number | the status screen advances by itself | Shows dynamic updates over time. It is NOT live tracking |

## Two sentences to say for each demo
1. *What happened*: "When the user does X (the event), PyScript calls function Y."
2. *Why it matters*: "It reads/changes Z and redraws only that part of the page, which supports <business step>."

## What is JavaScript, not PyScript
Lucide icon rendering (`index.html` observer), the `qrcode-generator` library (Python calls it), and the PyScript/Pyodide runtime. No custom JavaScript handles clicks, the cart or form checks.

## Limits to state honestly
No backend, no real payment, no live tracking. Orders, accounts and stamps are saved only in the visitor's own browser.
