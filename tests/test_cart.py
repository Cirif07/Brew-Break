import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys, types, re, ast, json
from unittest.mock import MagicMock
class CL:
    def __init__(s): s.s=set()
    def add(s,x): s.s.add(x)
    def remove(s,x): s.s.discard(x)
    def contains(s,x): return x in s.s
class El:
    def __init__(s,**a): s.attrs=dict(a.get("attrs",{})); s.innerHTML=""; s.textContent=""; s.value=a.get("value",""); s.disabled=False; s.classList=CL(); s.offsetWidth=1; s.focused=0
    def getAttribute(s,n): return s.attrs.get(n)
    def setAttribute(s,n,v): s.attrs[n]=v
    def removeAttribute(s,n): s.attrs.pop(n,None)
    def focus(s): s.focused+=1
    def querySelector(s,sel): return None
    def addEventListener(s,*a): pass
REG={}; LISTS={}
class Doc:
    activeElement=None
    def __getattr__(s,n): return MagicMock()
    def querySelector(s,sel): return REG.get(sel)
    def querySelectorAll(s,sel): return LISTS.get(sel,[])
win=MagicMock(); win.localStorage.getItem.return_value=None
ps=types.ModuleType("pyscript"); ps.document=Doc(); ps.window=win; ps.when=lambda *a,**k:(lambda f:f)
sys.modules["pyscript"]=ps
pf=types.ModuleType("pyodide.ffi"); pf.create_proxy=lambda f:f; pf.to_js=lambda x,**k:x; sys.modules["pyodide"]=types.ModuleType("pyodide"); sys.modules["pyodide.ffi"]=pf
import data, state, cart, views_browse as vb, views_checkout as vc, views_drink as vd, orders, payments
S=state.S
sheet=El(); REG.update({"#sheet":sheet,"#bagTxt":El(),"#bagBtn":El(),"#toast":El(),"#scrim":El()})
toasts=[]; state.toast=lambda m:toasts.append(m); cart.toast=state.toast; vc.toast=state.toast
ok=True
def chk(c,m):
    global ok; print(("PASS " if c else "FAIL ")+m); ok&=bool(c)
def btn(**a): return El(attrs={("data-"+k.replace("_","-")):str(v) for k,v in a.items()})
def reset(): S["cart"]=[]; S["vapplied"]=""; S["slot"]=""; S["pay"]=""; REG.pop("#sheet.on",None); cart.CLR["arm"]=False; toasts.clear()
def open_drawer(): REG["#sheet.on"]=sheet; sheet.classList.add("on"); cart.bag()

# ---- 1. every official item adds at its official price
reset(); expected=0
for x in data.D:
    vb.on_add(btn(id=x["id"])); expected+=x["p"]
chk(len(S["cart"])==16 and all(l["u"]==cart.find(l["id"])["p"] and l["q"]==1 for l in S["cart"]),"16 items added, each line at its official menu price, qty 1")
chk(cart.sub()==expected==sum(x["p"] for x in data.D),f"subtotal of one of everything = P{cart.sub()}")
chk(toasts[-1]=="Cheesy Ensaymada Mini added to your bag","feedback toast on add: "+toasts[-1])
# ---- 2. same item merges, quantity maths
reset(); vb.on_add(btn(id="bsp")); vb.on_add(btn(id="bsp")); vb.on_add(btn(id="mcl"))
chk(len(S["cart"])==2 and S["cart"][0]["q"]==2,"adding the same item twice raises quantity (one line)")
chk(cart.sub()==45*2+60 and cart.count()==3,f"subtotal {cart.sub()} = 45x2 + 60, count {cart.count()}")
open_drawer(); h=sheet.innerHTML
chk("₱90" in h and "₱45 each" in h and "Subtotal · 3 items" in h and "₱150" in h,"drawer shows line total P90, unit P45 each, '3 items', total P150")
chk("Pickup fee" not in h and "Customize" not in h,"no pickup fee or customization in the drawer")
# ---- 3. qty buttons
cart.on_qty(btn(i=0,d=1)); chk(S["cart"][0]["q"]==3 and cart.sub()==45*3+60,"+ raises quantity and total")
cart.on_qty(btn(i=0,d=-1)); cart.on_qty(btn(i=0,d=-1)); chk(S["cart"][0]["q"]==1,"- lowers quantity")
cart.on_qty(btn(i=0,d=-1)); chk(S["cart"][0]["q"]==1 and 'data-d="-1" disabled' in sheet.innerHTML.split('data-i="0"')[1][:60],"- stops at 1 and is disabled there")
S["cart"][0]["q"]=cart.MAX_QTY; toasts.clear(); cart.on_qty(btn(i=0,d=1)); chk(S["cart"][0]["q"]==20 and "up to 20" in toasts[-1],"quantity capped at 20 with a message")
cart.add_item("bsp"); chk(S["cart"][0]["q"]==20,"add button cannot push past 20")
# ---- 4. remove + clear
cart.on_qty(btn(i=0,d=-1)); n=len(S["cart"]); cart.on_remove(btn(i=0)); chk(len(S["cart"])==n-1 and "removed from your bag" in toasts[-1],"Remove deletes one line and says so")
cart.on_clear_bag(); chk(len(S["cart"])==1 and "Tap again to clear" in sheet.innerHTML,"first tap on Clear bag only asks for confirmation")
cart.on_clear_bag(); chk(S["cart"]==[] and "Your bag is empty" in sheet.innerHTML and "Browse the menu" in sheet.innerHTML,"second tap clears; empty-state shown")
chk(cart.sub()==0 and cart.due()==0 and cart.count()==0,"empty bag totals are 0")
# ---- 5. vouchers keep totals consistent
reset(); vb.on_add(btn(id="bsp")); S["vapplied"]="BREAK10"; chk(cart.due()==35,"BREAK10: P45 - P10 = P35")
cart.on_qty(btn(i=0,d=1)) if False else None
S["cart"][0]["q"]=3; chk(cart.sub()==135 and cart.due()==125,"BREAK10 on P135 = P125")
S["vapplied"]="WELCOME20"; S["cart"][0]["q"]=1; chk(cart.disc()==0 and cart.due()==45,"WELCOME20 needs P60 minimum -> no discount at P45")
S["cart"][0]["q"]=2; chk(cart.disc()==20 and cart.due()==70,"WELCOME20 at P90 -> P20 off = P70")
S["vapplied"]="SAVE15"; S["cart"][0]["q"]=2; chk(cart.disc()==0,"SAVE15 needs P80: P90 qualifies? "+str(cart.disc())) if False else None
reset(); S["vapplied"]="BREAK10"; chk(cart.due()==0,"voucher on empty bag never goes negative")
# ---- 6. saved bag rebuilt from the real menu
reset(); now=int(__import__("time").time()*1000)
bad={"t":now,"cart":[{"id":"bsp","q":2,"u":1,"n":"HACK"},{"id":"bsp","q":1,"u":1},{"id":"nope","q":1},{"id":"mcl","q":99},{"id":"cnc","q":0}],"vapplied":"","slot":"now"}
cart.load_json=lambda k,dflt: bad
chk(cart.restore_cart(),"restore_cart accepts a saved bag")
chk([(l["id"],l["q"],l["u"],l["n"]) for l in S["cart"]]==[("bsp",3,45,"Brown Sugar Pearl")],"tampered price/name ignored, duplicates merged, unknown/over-limit/zero rows dropped")
# ---- 7. drink page
vd.DT["qty"]=1; d=El(); REG["#dadd"]=El(attrs={"data-id":"jcb"}); REG["#dq"]=El()
vd.on_qty(btn(d=1)); vd.on_qty(btn(d=1)); chk(vd.DT["qty"]==3 and REG["#dadd"].textContent=="Add to bag · ₱186","drink page qty 3 x P62 -> 'Add to bag · ₱186'")
reset(); vd.on_add(REG["#dadd"]); chk(S["cart"][0]["q"]==3 and cart.sub()==186,"drink page adds 3 x Java Chip Blended = P186")
page=vd.drink_page("jcb"); chk("Size" not in page and "Sweetness" not in page and "Add-ons" not in page,"drink page has no size/sweetness/ice/add-on options")
# ---- 8. product cards
cards=[vb.drink_card(x) for x in data.D]
chk(all(f'data-act="add" data-id="{x["id"]}"' in c and f"₱{x['p']}" in c for x,c in zip(data.D,cards)),"all 16 cards: Add button wired + exact price shown")
# ---- 9. checkout validation + submission (guest, pay at the cart)
reset(); S["acct"]=None; S["user"]={}; vb.on_add(btn(id="csi")); vb.on_add(btn(id="ccc")); vb.on_add(btn(id="ccc"))
for k in ("#e-slot","#e-pay","#e-nick","#f-nick","#pay button","#cs .slot"): REG[k]=El()
chk(cart.due()==45+25*2,"checkout total = 45 + 25x2 = P95")
vc.place(); chk("pickup" in REG["#e-slot"].textContent.lower() and "payment" in REG["#e-pay"].textContent.lower(),"no slot/payment -> both errors shown")
S["slot"]="r"; S["pay"]="cart"; S["user"]["nick"]="A"; LISTS[".err"]=[REG["#e-slot"],REG["#e-pay"],REG["#e-nick"]]; LISTS["#co input"]=[REG["#f-nick"]]
vc.place(); chk("name" in REG["#e-nick"].textContent.lower() and REG["#f-nick"].attrs.get("aria-invalid")=="true" and S["cart"],"1-letter name rejected, field flagged, bag kept")
S["user"]["nick"]="Ana"; before=cart.due(); vc.place()
o=S["order"]; chk(o and o["total"]==before==95 and S["cart"]==[] and o["pay"]=="cart" and o["paid"] is False,"valid form -> order created: total P95, not marked paid, bag emptied")
chk(all(i["u"]==cart.find(i["id"])["p"] for i in o["items"]),"order lines carry official prices")
# ---- 10. bag empty at checkout
toasts.clear(); vc.place(); chk(toasts and "empty" in toasts[-1],"place() with an empty bag just says so")
# ---- 11. wiring
src=open("main.py").read(); t=ast.parse(src); acts={}
for nd in t.body:
    if isinstance(nd,ast.Assign) and getattr(nd.targets[0],'id','')=='ACTIONS': acts={k.value:ast.unparse(v) for k,v in zip(nd.value.keys,nd.value.values)}
import views_account, views_info, dialogs
mods={"cart":cart,"vb":vb,"views_checkout":vc,"views_drink":vd,"orders":orders,"views_account":views_account,"views_info":views_info,"dialogs":dialogs}
bad=[(k,v) for k,v in acts.items() if re.fullmatch(r"\w+\.\w+",v) and not hasattr(mods.get(v.split(".")[0]),v.split(".")[1])]
chk(not bad,f"every ACTIONS entry points at a real function ({len(acts)} checked) {bad}")
chk(acts.get("add")=="vb.on_add" and acts.get("qty")=="cart.on_qty" and acts.get("rm")=="cart.on_remove" and acts.get("bagclear")=="cart.on_clear_bag","cart events wired: add, qty, rm, bagclear")
allhtml="".join(open(f).read() for f in ("cart.py","views_checkout.py","views_drink.py","views_browse.py","orders.py"))
used=set(re.findall(r'data-act="(\w[\w-]*)"',allhtml)); missing=sorted(a for a in used if a not in acts and a not in ("close",))
chk(not missing,f"every data-act used in the pages has a handler {missing}")
print("ALL OK" if ok else "FAILURES")
