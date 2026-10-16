import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys, types, re, ast
from unittest.mock import MagicMock
# ---- minimal fake browser so the project's own modules import and run in plain Python
class El:
    def __init__(s,**k): s.attrs=dict(k.get('attrs',{})); s.innerHTML=""; s.textContent=""; s.duration=k.get('duration'); s.readyState=k.get('ready',0); s.l={}
    def getAttribute(s,n): return s.attrs.get(n)
    def setAttribute(s,n,v): s.attrs[n]=v
    def addEventListener(s,ev,fn): s.l[ev]=fn
REG={}
class Doc:
    def querySelector(s,sel): return REG.get(sel)
    def querySelectorAll(s,sel): return REG.get(sel+"*",[])
    def __getattr__(s,n): return MagicMock()
win=MagicMock(); win.localStorage.getItem.return_value=None; win.sessionStorage.getItem.return_value=None
ps=types.ModuleType("pyscript"); ps.document=Doc(); ps.window=win; ps.when=lambda *a,**k:(lambda f:f)
sys.modules["pyscript"]=ps
pf=types.ModuleType("pyodide.ffi"); pf.create_proxy=lambda f:f; sys.modules["pyodide"]=types.ModuleType("pyodide"); sys.modules["pyodide.ffi"]=pf
import data, views_browse as vb
OFF={"mt":("Milk Tea",[("Brown Sugar Pearl",45),("Wintermelon Cream Cheese",48),("Okinawa Grass Jelly",40),("Taro Velvet Pearl",45)]),
"ic":("Iced Coffee",[("Creamy Spanish Iced Coffee",45),("Creamy Barako Iced Brew",30),("Iced Vanilla Americano",35),("Caramel Macchiato",50)]),
"fr":("Fruit Refreshers",[("Strawberry Lychee Fizz",38),("Mango Passion Cooler",35),("Honey Calamansi Tea",32)]),
"fb":("Frappes",[("Cookies and Cream",58),("Java Chip Blended",62),("Matcha Cloud",60)]),
"bk":("Bakes",[("Choco Chip Chunk",25),("Cheesy Ensaymada Mini",28)])}
ok=True
def chk(c,m):
    global ok; print(("PASS " if c else "FAIL ")+m); ok&=bool(c)
chk(len(data.D)==16,f"product count = {len(data.D)}")
chk(len(data.CATS)==5,"5 categories")
for cid,(cn,items) in OFF.items():
    cur=[(x['n'],x['p']) for x in data.D if x['cat']==cid]
    chk(cur==items,f"{cn}: {len(cur)} items match names+prices exactly, in order")
    chk([c['n'] for c in data.CATS if c['id']==cid]==[cn],f"category name '{cn}'")
chk([c['id'] for c in data.CATS]==list(OFF),"category order")
# ---- homepage render, placeholder mode
html=vb.home()
chk('<video' not in html and 'id="promo-ph"' in html and 'Promotional video placeholder' in html,"no video file -> placeholder shown, no fake <video>")
tabs=re.findall(r'data-act="hcat" data-c="(\w+)"',html); chk(tabs==list(OFF),"5 homepage category tabs")
chk(all(n in html for n,_ in OFF["mt"][1]),"default grid (Milk Tea) shows its 4 official items")
chk("Brew Break" in html and 'href="#/menu"' in html,"brand name + menu CTA present")
# ---- video mode
data.PROMO.update(src="assets/brew-break-promo.mp4",captions="assets/c.vtt",poster="assets/p.jpg"); vb.PROMO=data.PROMO
p=vb.promo_section(); chk(all(t in p for t in ['<video id="promo" controls','<source src="assets/brew-break-promo.mp4"','kind="captions"','playsinline','poster=']) and 'promo-ph' not in p,"with src: accessible <video controls> + captions track + poster, no placeholder")
# ---- PyScript handler: category tab click
tabs_el=[El(attrs={"data-c":c,"aria-pressed":"false"}) for c in OFF]
REG["#hcats .tab*"]=tabs_el; grid=El(); REG["#hgrid"]=grid
vb.on_hcat(El(attrs={"data-c":"fb"}))
chk(vb.HC["cat"]=="fb","on_hcat stores chosen category")
chk([t.attrs["aria-pressed"] for t in tabs_el]==["false","false","false","true","false"],"aria-pressed updated on tabs")
chk(all(n in grid.innerHTML for n,_ in OFF["fb"][1]) and not any(n in grid.innerHTML for n,_ in OFF["mt"][1]),"grid redrawn with only Frappes items")
chk(grid.innerHTML.count('class="dc')>=3 or grid.innerHTML.count("data-act")>=3,"cards rendered in grid")
# ---- video metadata listener
for dur,want in [(42.0,"0:42"),(20.0,"outside")]:
    v=El(duration=dur,ready=0); n=El(); REG["#promo"]=v; REG["#promo-note"]=n
    vb.after_home(); v.l["loadedmetadata"]()
    chk((want in n.textContent) if want=="0:42" else ("30–60" in n.textContent),f"loadedmetadata with {dur}s -> '{n.textContent}'")
REG.pop("#promo")
chk(vb.after_home() is None,"after_home is a no-op when there is no video")
# ---- wiring in main.py
src=open("main.py").read(); t=ast.parse(src); acts={}
for nd in t.body:
    if isinstance(nd,ast.Assign) and getattr(nd.targets[0],'id','')=='ACTIONS':
        acts={k.value:ast.unparse(v) for k,v in zip(nd.value.keys,nd.value.values)}
chk(acts.get("hcat")=="vb.on_hcat","ACTIONS['hcat'] -> vb.on_hcat"); chk("vb.after_home()" in src,"route calls vb.after_home() on Home")
print("ALL OK" if ok else "FAILURES")
