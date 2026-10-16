# Brew Break (PyScript edition)

A pre-order website for Brew Break, a proposed mobile coffee and beverage cart for students at Cebu Eastern College, written in
**Python** that runs in the browser with [PyScript](https://pyscript.net). Customers browse the 16-item menu, build a bag,
choose a pickup time and place a **demonstration** pre-order. There is no backend: payments, order tracking, accounts and stamps
are simulated in the browser (see "Payments are a demo" below).

## Run it
PyScript downloads the `.py` files with HTTP requests, so opening `index.html` by double-clicking will not work.
From this folder run:

    python -m http.server 8000

then open http://localhost:8000 . It also works on GitHub Pages (Settings, Pages, deploy from the main branch).
The page needs an internet connection to load PyScript, the Lucide icons, the QR library and Google Fonts.

Tests (plain Python 3, no installs; they use a fake browser, so they do not replace clicking through the site):

    python tests/check_menu.py
    python tests/test_home.py
    python tests/test_cart.py
    python tests/test_menu_pages.py
    python tests/test_checkout.py

## How it is organised
| File | What it does |
|---|---|
| `index.html` | The page shell: header, bottom tabs, empty `<main>`, and the PyScript tags |
| `style.css` | All styling |
| `pyscript.toml` | Lists every Python file PyScript must download |
| `main.py` | Starts the app, draws pages (router) and receives all events |
| `state.py` | Shared state dictionary, small DOM helpers, browser storage |
| `data.py` | The menu, prices, pickup times, vouchers, perks and shop details (edit this to change the menu) |
| `cart.py` | Bag maths (add, quantity, remove, clear), vouchers, saved bag, "Order again", the bag drawer |
| `dialogs.py` | Pop-up screens: voucher chooser and confirmation boxes |
| `views_browse.py` | Home and Menu pages |
| `views_drink.py` | Drink detail page (facts, quantity, Add button) |
| `views_checkout.py` | Checkout page, order summary, validation, "same as last time" offers |
| `payments.py` | QR code, "Scan to pay" screen, checking step, successful / unsuccessful / failed screens |
| `auth.py` | Accounts and security: password hashing (WebCrypto PBKDF2), lockout, sessions, login and logout |
| `avatars.py` | Avatar pictures, the avatar picker pop-up and the Settings header |
| `views_account.py` | Login, register and Settings pages (profile, password, notifications, display, delete account) |
| `views_info.py` | About and contact, Rewards (stamp card), Vouchers (redeem and wallet), Privacy and Terms pages |
| `seo.py` | Page titles and descriptions, and the cafe + menu data for search engines (JSON-LD) |
| `orders.py` | Placing an order (`commit_order`), saving it, the Orders status page (a timer simulation), claiming guest stamps |
| `tests/` | Python tests that run the real handlers with a fake browser |
| `docs/` | PyScript demo guide, README and presentation outlines, GitHub readiness notes |
| `assets/` | Where the promotional video and product photos go (see `assets/README.txt`) |

## Event-driven design (what to explain in the video)
1. **One listener per event type.** `main.py` listens once for `click`, `input` and `keydown` on the page.
2. **`data-act` names.** Every button has an attribute like `data-act="qty"`. The click handler looks the name up in
   the `ACTIONS` dictionary and calls that Python function. Buttons created later work with no extra wiring (event delegation).
3. **Events change state, state redraws the page.** A handler updates the `S` dictionary (the bag, chosen voucher, ...)
   and then redraws only the part of the page that changed.
4. **`hashchange` is the router.** Links like `#/menu` fire an event; `route()` reads the address and shows the page.
5. **Other events used:** `input` (live menu search), `keydown` (Esc closes pop-ups, Tab stays inside them),
   `pagehide` and `visibilitychange` (save the bag), a repeating timer (save every few seconds).

## Payments are a demo
No payment provider is connected, so no real money moves. With `BIZ["demoPayments"] = True` (in `data.py`) the QR is a
sample and the "Scan to pay" screen has a dropdown to choose the result. Set it to `False` and "I have paid" reports that
payment checking is not connected yet. A real QR and the payment check must come from a payment provider through a server.
The QR image is drawn by the small `qrcode-generator` JavaScript library (loaded in `index.html`) which Python calls.

## Security (what is real and what is a demo)
Passwords are hashed in the browser with a random salt and 600,000 rounds of PBKDF2 (WebCrypto, called from Python with `await`).
Five wrong tries lock an account (30 s, doubling up to 15 min), the error message is the same for "no such account" and
"wrong password", and sessions expire. But accounts, vouchers and stamps are stored in this browser only, so anyone with access
to the browser can read or change them. A real shop needs a server for accounts, vouchers and payments.

## Features
The official 16-item menu in 5 categories (Milk Tea, Iced Coffee, Fruit Refreshers, Frappes, Bakes) with live search and filters;
a bag with quantity, remove and clear; a saved bag; "Order again" and "Same as last time"; vouchers (redeem a code, wallet,
a free-drink voucher from stamps); checkout with pickup time and validation; a sample cashless QR screen or pay at the cart;
a demonstration order status page; accounts stored in the browser; Rewards; About, contact and visit details.

## Status and known gaps
- **Promotional video: not added yet.** Home shows a labelled placeholder. Add a 30-60 second MP4 (see `assets/README.txt`).
- **Product photos: not added yet.** Cards use icon tiles. Photos can be embedded through `PHOTOS` in `data.py`.
- No backend, no real payment, no live tracking. Everything is saved in the visitor's own browser.
- Tested with plain-Python tests and a headless browser on rendered pages; the live PyScript app still needs a manual click-through.

## Working as a group on GitHub
Every member must make real commits. Modules are separate on purpose, so one person can own each area:

| Area | Files |
|---|---|
| Pages and layout | `index.html`, `style.css`, `views_browse.py`, `views_drink.py`, `views_info.py` |
| Cart, vouchers, orders | `cart.py`, `orders.py`, `views_checkout.py` |
| Payments and pop-ups | `payments.py`, `dialogs.py` |
| Accounts and security | `auth.py`, `views_account.py`, `avatars.py` |
| App core, data, search | `main.py`, `state.py`, `data.py`, `seo.py` |

Tips: commit small and often with clear messages (for example "Add voucher validation"), and each member should push from their own account.
