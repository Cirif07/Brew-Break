# README outline (fill in the bracketed parts; do not invent facts)

1. **Brew Break** - one-line pitch: "Good-tasting drinks. Student-friendly prices. Your perfect break."
2. **Business concept** - a proposed mobile coffee and beverage cart for students at Cebu Eastern College, especially near the College of Information Technology building. Priorities: great-tasting drinks and food, affordable prices, convenient browsing and ordering. Target customers: [confirm with the group].
3. **Live demo / screenshots** - [GitHub Pages link once approved] and screenshots of Home, Menu, Bag, Checkout, About.
4. **Promotional video** - [link or embedded location]. Status: [missing until the 30-60 s video file is added to `assets/`].
5. **Features** - the 16-item official menu in 5 categories; live search and filters; bag with quantity, remove and clear; voucher codes; pickup windows; checkout with validation; sample cashless QR and pay-at-the-cart; demo order status; rewards stamps; accounts stored in the browser; About, Contact and Visit details.
6. **What is real and what is a demo** - no backend, no real payment, no live tracking; data lives in the browser only.
7. **Setup** - `python -m http.server 8000`, then open http://localhost:8000 (double-clicking `index.html` will not work). Needs internet for PyScript, fonts, Lucide and the QR library.
8. **PyScript implementation** - link to `PYSCRIPT_EVENTS.md` and `docs/PYSCRIPT_DEMO.md`; short explanation of `@when`, `data-act` and `ACTIONS`.
9. **Project structure** - file table (reuse the one in the current README, then remove outdated lines: customize sheet, drink options, "live order tracker", perks).
10. **Menu data** - how to edit `data.py`; the official 16 items and prices.
11. **Group members and contributions** - table: Member | Role | Files/features | Evidence (commits). [Names and contributions to be written by the group.]
12. **Credits and licenses** - Lucide (ISC), PyScript (Apache-2.0), qrcode-generator (MIT), Fraunces and Geist fonts (SIL OFL). [Choose a license for this repo.]
