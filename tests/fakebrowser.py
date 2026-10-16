"""A tiny fake browser so the project's Python can run in plain Python 3 (no PyScript needed).

It is NOT a real browser: it only lets tests call the real handlers and read the HTML they produce.
"""
import sys
import types
from unittest.mock import MagicMock


class ClassList:
    def __init__(self): self.s = set()
    def add(self, x): self.s.add(x)
    def remove(self, x): self.s.discard(x)
    def contains(self, x): return x in self.s


class El:
    def __init__(self, **a):
        self.attrs = dict(a.get("attrs", {})); self.innerHTML = ""; self.textContent = ""; self.value = a.get("value", "")
        self.disabled = False; self.classList = ClassList(); self.offsetWidth = 1
    def getAttribute(self, n): return self.attrs.get(n)
    def setAttribute(self, n, v): self.attrs[n] = v
    def removeAttribute(self, n): self.attrs.pop(n, None)
    def focus(self): pass
    def querySelector(self, sel): return None
    def addEventListener(self, *a): pass


REG, LISTS = {}, {}


class Doc:
    activeElement = None
    def __getattr__(self, n): return MagicMock()
    def querySelector(self, sel): return REG.get(sel)
    def querySelectorAll(self, sel): return LISTS.get(sel, [])


def install():
    win = MagicMock(); win.localStorage.getItem.return_value = None
    ps = types.ModuleType("pyscript"); ps.document = Doc(); ps.window = win; ps.when = lambda *a, **k: (lambda f: f)
    sys.modules["pyscript"] = ps
    pf = types.ModuleType("pyodide.ffi"); pf.create_proxy = lambda f: f; pf.to_js = lambda x, **k: x
    sys.modules["pyodide"] = types.ModuleType("pyodide"); sys.modules["pyodide.ffi"] = pf
    for k in ("#ml", "#cf", "#cc", "#sheet", "#toast", "#bagBtn", "#bagTxt", "#scrim"): REG[k] = El()


class Checker:
    def __init__(self): self.ok = True; self.n = 0
    def __call__(self, cond, msg):
        self.n += 1; self.ok &= bool(cond); print(("PASS " if cond else "FAIL ") + msg)
    def done(self):
        print(f"{self.n} checks, " + ("ALL OK" if self.ok else "FAILURES")); sys.exit(0 if self.ok else 1)
