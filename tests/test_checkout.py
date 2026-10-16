"""Checkout paths: guest, account validation, pay at the cart, sample QR, and honest demo wording. Run:  python tests/test_checkout.py"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakebrowser as fb
fb.install()
import data, state, cart, orders, payments, dialogs, views_checkout as vc
from fakebrowser import El, REG, LISTS
chk = fb.Checker(); S = state.S
shown = []
dialogs.show_dialog = lambda html, *a, **k: shown.append(html)
payments.dialogs.show_dialog = dialogs.show_dialog
state.toast = lambda m: None; cart.toast = vc.toast = state.toast
for k in ("#e-slot", "#e-pay", "#e-nick", "#f-nick", "#e-name", "#f-name", "#e-mobile", "#f-mobile", "#pay button", "#cs .slot", "#place"): REG[k] = El()
LISTS[".err"] = [REG["#e-slot"], REG["#e-pay"], REG["#e-nick"], REG["#e-name"], REG["#e-mobile"]]; LISTS["#co input"] = [REG["#f-nick"], REG["#f-name"], REG["#f-mobile"]]
def fresh(items=("bsp", "ccc")):
    S.update(cart=[], vapplied="", slot="r", pay="cart", acct=None, user={}, order=None); shown.clear()
    for i in items: cart.add_item(i)

# guest, pay at the cart
fresh(); S["user"]["nick"] = "Ana"; due = cart.due(); vc.place()
o = S["order"]
chk(o and o["total"] == due == 70 and o["paid"] is False and S["cart"] == [], "guest pay-at-cart: order created for P70, not marked paid, bag emptied")
chk(shown and "Order placed" in shown[-1] and "Pay ₱70 at the cart" in shown[-1], "confirmation says to pay at the cart")
# account: name and mobile are validated
fresh(); S["acct"] = {"id": "x", "name": "Ana Reyes", "email": "ana", "role": "student"}; S["user"] = {"name": "A", "mobile": "123"}; vc.place()
chk(S["order"] is None and S["cart"] and "full name" in REG["#e-name"].textContent and "mobile" in REG["#e-mobile"].textContent.lower(), "account holder: bad name and mobile rejected, bag kept")
S["user"] = {"name": "Ana Reyes", "mobile": "0917 555 0192"}; vc.place()
chk(S["order"] and S["order"]["total"] == 70, "account holder: valid name and mobile place the order")
# sample QR (demo): dialog opens first, order only after 'payment goes through'
fresh(); S["pay"] = "cashless"; S["user"]["nick"] = "Ana"; calls = []
payments.open_pay_dialog = lambda *a: calls.append("qr"); vc.payments.open_pay_dialog = payments.open_pay_dialog
vc.place(); chk(calls == ["qr"] and S["order"] is None and S["cart"], "cashless: the sample QR opens and no order exists yet")
payments.finish_order()
o = S["order"]; chk(o and o["paid"] is True, "after the demo payment succeeds the order is created")
chk(data.BIZ["demoPayments"] and "Demo payment complete" in shown[-1] and "no real" in shown[-1] and "Payment received" not in shown[-1] and "We received your" not in shown[-1], "success screen says it is a demonstration and takes no real money")
page = orders.live_html(S["order"])
chk("Demo payment: no real money was taken" in page and "Paid by QR code" not in page and "Demo only" in page, "order page: demo wording, no 'Paid by QR code'")
payments.status_dialog("fail"); chk("simulated failure" in shown[-1] and "If money left your account" not in shown[-1], "failure screen is clearly simulated")
chk.done()
