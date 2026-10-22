"""KiCad S-ifade dosyalari icin kucuk okuyucu/yazici."""
import re


class Sym(str):
    """Tirnaksiz atom (ornek: symbol, at, yes)."""


class QStr(str):
    """Tirnakli metin."""


_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text):
    pos = 0
    stack = [[]]
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError("parse error at %d: %r" % (pos, text[pos:pos + 40]))
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            lst = stack.pop()
            stack[-1].append(lst)
        elif m.group(3) is not None:
            s = re.sub(r'\\(["\\n])', lambda mm: {"n": "\n"}.get(mm.group(1), mm.group(1)), m.group(3))
            stack[-1].append(QStr(s))
        elif m.group(4) is not None:
            stack[-1].append(Sym(m.group(4)))
    return stack[0][0] if len(stack[0]) == 1 else stack[0]


def _atom(a):
    if isinstance(a, QStr):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        s = ("%.4f" % a).rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    if isinstance(a, bool):
        return "yes" if a else "no"
    return str(a)


def dumps(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    simple = all(not isinstance(x, list) for x in node)
    if simple:
        return "(" + " ".join(_atom(x) for x in node) + ")"
    pad = "\t" * (indent + 1)
    parts = []
    head = []
    for x in node:
        if isinstance(x, list):
            break
        head.append(_atom(x))
    out = "(" + " ".join(head)
    for x in node[len(head):]:
        if isinstance(x, list):
            out += "\n" + pad + dumps(x, indent + 1)
        else:
            out += " " + _atom(x)
    out += "\n" + "\t" * indent + ")"
    return out


def find(node, key):
    """Ilk (key ...) alt listesini dondurur."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]
