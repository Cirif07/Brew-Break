# Recorded presentation outline (about 12 minutes)

Rehearse with the real site open at http://localhost:8000. Do not describe anything that is not on screen.

| Time | Section | What to show and say |
|---|---|---|
| 0:00-1:30 | **1. Business, group, customers** | Business name Brew Break. Introduce each member: [Name 1], [Name 2], ... (the group fills this in). Concept: proposed mobile coffee and beverage cart at Cebu Eastern College near the CIT building. Target customers: students on campus who want good, affordable drinks fast. Message: "Good-tasting drinks. Student-friendly prices. Your perfect break." |
| 1:30-3:00 | **2. Business process** | Customer journey: browse -> add to bag -> choose pickup time -> pay (pay at the cart, or sample QR) -> collect with a PIN. Say what the website supports (browsing, ordering ahead, totals) and what it does not (no real payments, no shop system, no live tracking). |
| 3:00-6:00 | **3. Website tour** | Landing page and the logo (cup with two "pause" bars = a break). The embedded promotional video: play it on the page **only if the real file has been added**; otherwise say it is still required. Menu: show all 16 items and their prices. Add to bag, change quantity, remove, voucher BREAK10, checkout, order screen. About, contact and footer. Resize the window to show 768 px and 390 px layouts. |
| 6:00-9:30 | **4. PyScript and event-driven code** | Open `index.html`, `main.py` (`@when`, `ACTIONS`), then walk through the demos in `docs/PYSCRIPT_DEMO.md`: category tabs, live search, add to bag, quantity/remove, calculations, checkout validation, order timer. For each: trigger, handler, data, page update, business purpose. State plainly what is JavaScript. |
| 9:30-10:30 | **Honest limits** | No backend, no real payment, data stays in the browser. What the group would build next. |
| 10:30-12:00 | **5. Each member's contribution** | One slot per member: [Name] - [what they built, which files, a commit or screenshot as proof]. Do not claim work that is not in the repository history. |

## Checklist before recording
- [x] Promotional video file added (50 s), plays on the Home page
- [ ] Every member can explain at least one handler
- [ ] Repository history shows each member's commits
- [ ] Screen recording at 1080p, microphone checked
