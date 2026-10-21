"""Tiny YAML-subset reader (stdlib only).

The skill may only depend on moadian-full and the standard library, and
moadian-full does not pull in PyYAML. We also deliberately do NOT use PyYAML
when it is installed: YAML 1.1 reads `0300101` as octal (98369) and
`0012345678` as a number, which silently corrupts IDs. This parser keeps any
leading-zero number as a string. It handles the simple files build_invoice.py
expects:

    seller_tin: "10101234567"     # comments are allowed
    buyer:
      tin: "14011576540"
      type: 1
    items:
      - sstid: "2330004219206"
        sstt: پرینتر
        fee: 120000000
        am: 2

Supported: nested mappings by indentation, lists of scalars or mappings,
quoted/unquoted strings, ints, floats, true/false/null. Not supported: flow
style ({a: 1}), anchors, multi-line strings. Unsupported input raises
ValueError with a line number instead of being silently misread.
"""

from __future__ import annotations

import re


def loads(text: str):
    lines = []
    for no, raw in enumerate(text.splitlines(), 1):
        stripped = _strip_comment(raw).rstrip()
        if stripped.strip() and stripped.strip() != "---":
            if "\t" in raw[: len(raw) - len(raw.lstrip())]:
                raise ValueError(f"line {no}: tabs are not allowed for indentation")
            lines.append((no, len(stripped) - len(stripped.lstrip()), stripped.strip()))
    if not lines:
        return None
    value, pos = _parse_block(lines, 0, lines[0][1])
    if pos != len(lines):
        raise ValueError(f"line {lines[pos][0]}: unexpected indentation")
    return value


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out)


def _scalar(token: str):
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    if token.startswith(("{", "[", "&", "*", "|", ">")):
        raise ValueError(f"unsupported YAML syntax: {token!r} (use the JSON input format instead)")
    low = token.lower()
    if low in ("null", "~", ""):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    if re.fullmatch(r"[-+]?\d+", token) and not (len(token.lstrip("+-")) > 1 and token.lstrip("+-")[0] == "0"):
        return int(token)
    if re.fullmatch(r"[-+]?\d+\.\d+", token):
        return float(token)
    return token  # leading-zero numbers stay strings (codes like 0300101)


def _split_key(text: str, no: int):
    m = re.match(r"^(\"[^\"]*\"|'[^']*'|[^:]+?)\s*:(\s+|$)(.*)$", text)
    if not m:
        raise ValueError(f"line {no}: expected 'key: value', got {text!r}")
    key = m.group(1).strip("\"'")
    return key, m.group(3)


def _parse_block(lines, pos, indent):
    if lines[pos][2].startswith("- ") or lines[pos][2] == "-":
        return _parse_list(lines, pos, indent)
    return _parse_map(lines, pos, indent)


def _parse_map(lines, pos, indent):
    result = {}
    while pos < len(lines):
        no, ind, text = lines[pos]
        if ind < indent:
            break
        if ind > indent:
            raise ValueError(f"line {no}: unexpected indentation")
        if text.startswith("- "):
            break
        key, rest = _split_key(text, no)
        pos += 1
        if rest.strip():
            result[key] = _scalar(rest)
        elif pos < len(lines) and lines[pos][1] > indent:
            result[key], pos = _parse_block(lines, pos, lines[pos][1])
        elif pos < len(lines) and lines[pos][1] == indent and lines[pos][2].startswith("- "):
            result[key], pos = _parse_list(lines, pos, indent)
        else:
            result[key] = None
    return result, pos


def _parse_list(lines, pos, indent):
    result = []
    while pos < len(lines):
        no, ind, text = lines[pos]
        if ind != indent or not (text.startswith("- ") or text == "-"):
            if ind > indent:
                raise ValueError(f"line {no}: unexpected indentation")
            break
        body = text[1:].strip()
        if not body:
            pos += 1
            item, pos = _parse_block(lines, pos, lines[pos][1])
            result.append(item)
            continue
        if re.match(r"^(\"[^\"]*\"|'[^']*'|[^:\"']+?)\s*:(\s|$)", body):
            # "- key: value" starts a mapping; its other keys sit at indent+2
            child_indent = ind + (len(text) - len(body))
            lines[pos] = (no, child_indent, body)
            item, pos = _parse_map(lines, pos, child_indent)
            result.append(item)
        else:
            result.append(_scalar(body))
            pos += 1
    return result, pos
