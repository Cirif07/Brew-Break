# PyScript event map (Stage 4)

## How an event becomes behavior
1. `index.html` loads `main.py` with `pyscript.toml`. PyScript runs the Python in the browser.
2. `main.py` registers three listeners with the documented `pyscript.when` decorator: `@when("click", "body")` (line 130), `@when("input", "body")` (line 139), `@when("keydown", "body")` (line 149).
3. A click on any element with `data-act="name"` looks `name` up in the `ACTIONS` table (`main.py`) and calls that Python function.
4. The function changes data (`S["cart"]` in `state.py`) and redraws only what changed. There is one listener per event type, so handlers are never registered twice.

## Cart and ordering events (Stage 4)
| Event | data-act | Python handler | Does |
|---|---|---|---|
| Add button click (menu, home, search) | `add` | `views_browse.on_add` -> `cart.add_item` | add one item, or raise its quantity (max 20) |
| Add button click (drink page) | `dadd` | `views_drink.on_add` -> `cart.add_item` | add the chosen quantity, open the bag |
| Quantity + / - (drink page) | `dqty` | `views_drink.on_qty` | change the number shown on the Add button |
| Quantity + / - (bag and checkout) | `qty` | `cart.on_qty` | change one line, recalculate, redraw |
| Remove click | `rm` | `cart.on_remove` | delete one line |
| Clear bag click (two taps) | `bagclear` | `cart.on_clear_bag` | empty the bag |
| Confirm pre-order click | `place` | `views_checkout.place` | validate the form, then create the order |
| Typing in checkout fields | (input listener) | `views_checkout.on_field_input` | keep the typed value |
| Typing in menu search | (input listener) | `views_browse.on_menu_input` | live filter |

## Cart calculation logic (`cart.py`)
- A bag line is `{id, n, u, q}`: `u` is always the item's official price from `data.py`. No sizes, add-ons, sweetness or ice options exist, and there are no fees or taxes.
- `line total = u x q`, `sub() = sum of line totals`, `count() = sum of q`.
- `disc()` is the applied voucher's discount (0 when none or when its minimum is not met); `due() = max(0, sub() - disc())`.
- Every handler ends with `refresh_views()`, which redraws the header total, the open bag drawer, and the checkout summary from the same data, so all three always agree.
- Saved bags are rebuilt from the official menu on load (`restore_cart`), so edited saved data cannot change a price or name.

## Form validation (`views_checkout.place`)
Needs a pickup time and payment method. Guests need a name (2-20 characters); account holders need a name and a Philippine mobile number. Errors are written next to the field and the first bad field gets focus.

## PyScript versus JavaScript
| Part | Language |
|---|---|
| Every click, input and key handler; cart maths; validation; building and redrawing the bag, menu, checkout and order pages; reading and writing browser storage (Python calling `window.localStorage`) | **PyScript (Python)** |
| `index.html` icon observer (turns `<i data-lucide>` into SVG icons) and the Lucide library | **JavaScript** |
| The `qrcode-generator` library (Python calls it to draw the sample QR) | **JavaScript library**, called from Python |
| PyScript itself and Pyodide | runtime |

No custom JavaScript handles clicks, cart changes or form checks.

## All registered actions (39)
| data-act | Python handler | File |
|---|---|---|
| `bag` | `cart.bag` | cart.py |
| `close` | `lambda t, e: cart.close_sheet()` | main.py |
| `add` | `vb.on_add` | views_browse.py |
| `qty` | `cart.on_qty` | cart.py |
| `rm` | `cart.on_remove` | cart.py |
| `bagclear` | `cart.on_clear_bag` | cart.py |
| `bslot` | `cart.on_bslot` | cart.py |
| `bsugg` | `cart.on_bsugg` | cart.py |
| `again` | `cart.on_again` | cart.py |
| `vremove` | `cart.on_vremove` | cart.py |
| `vuse` | `cart.on_vuse` | cart.py |
| `vapply` | `cart.on_vapply` | cart.py |
| `vopen` | `dialogs.open_voucher_dialog` | dialogs.py |
| `hslot` | `vb.on_hslot` | views_browse.py |
| `hcat` | `vb.on_hcat` | views_browse.py |
| `mf` | `vb.on_filter` | views_browse.py |
| `mc` | `vb.on_category` | views_browse.py |
| `clr` | `vb.on_clear` | views_browse.py |
| `mreset` | `reset_menu` | main.py |
| `reload` | `lambda t, e: window.location.reload()` | main.py |
| `dqty` | `views_drink.on_qty` | views_drink.py |
| `dadd` | `views_drink.on_add` | views_drink.py |
| `cslot` | `views_checkout.on_slot` | views_checkout.py |
| `cpay` | `views_checkout.on_pay` | views_checkout.py |
| `sslot` | `views_checkout.on_suggest_slot` | views_checkout.py |
| `spay` | `views_checkout.on_suggest_pay` | views_checkout.py |
| `place` | `views_checkout.place` | views_checkout.py |
| `pickedup` | `orders.on_pickedup` | orders.py |
| `reorder` | `orders.on_reorder` | orders.py |
| `logout` | `views_account.on_logout` | views_account.py |
| `logout2` | `views_account.on_logout2` | views_account.py |
| `avedit` | `views_account.on_avatar_edit` | views_account.py |
| `eye` | `views_account.on_eye` | views_account.py |
| `submit` | `views_account.on_submit` | views_account.py |
| `sw` | `views_account.on_switch` | views_account.py |
| `save-profile` | `views_account.on_save_profile` | views_account.py |
| `save-pw` | `views_account.on_save_password` | views_account.py |
| `del-open` | `views_account.on_delete_open` | views_account.py |
| `del-go` | `views_account.on_delete` | views_account.py |

## What this demo is not
- There is **no backend or database**. Nothing is sent to a shop or anyone else.
- **No real payment** is taken. The QR is a sample and the result is chosen from a dropdown (`demoPayments` in `data.py`).
- Accounts, vouchers, stamps and orders live only in this browser's storage. Passwords are hashed in the browser; this is a demonstration, not secure sign-in.
- The order tracker is a timer in the page (it advances every 7 seconds); it is not live tracking.

## Tested
Plain-Python tests drive these real handlers with a fake browser object (not a real browser): adding all 16 items at their official prices, merging, quantity limits, remove, two-step clear, voucher maths, saved-bag rebuilding, drink page, checkout validation and order creation, and that every `data-act` has a handler. They passed. The handlers have not been run in a real browser here.
