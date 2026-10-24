"""Convert a Claude Docs prose read (saved JSON) to Markdown for book/."""

import json
import sys
import xml.etree.ElementTree as ET


def runs(element, fmt=(), href=None):
    """Yield (text, formats, href) for every piece of text inside element."""
    if element.text:
        yield element.text, fmt, href
    for child in element:
        tag = child.tag
        if tag in ("bold", "italic", "code"):
            yield from runs(child, fmt + (tag,), href)
        elif tag == "link":
            yield from runs(child, fmt, child.get("href"))
        else:
            yield from runs(child, fmt, href)
        if child.tail:
            yield child.tail, fmt, href


def inline(paragraph):
    merged = []
    for text, fmt, href in runs(paragraph):
        key = (tuple(sorted(set(fmt))), href)
        if merged and merged[-1][1] == key:
            merged[-1][0] += text
        else:
            merged.append([text, key])
    # group by link
    out = []
    i = 0
    while i < len(merged):
        href = merged[i][1][1]
        group = []
        while i < len(merged) and merged[i][1][1] == href:
            group.append(merged[i])
            i += 1
        piece = "".join(style(text, key[0]) for text, key in group)
        out.append(f"[{piece}]({href})" if href else piece)
    return "".join(out)


def style(text, fmt):
    if "code" in fmt:
        return f"`{text}`"
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    core = text.strip()
    if not core:
        return text
    if "bold" in fmt:
        core = f"**{core}**"
    if "italic" in fmt:
        core = f"*{core}*"
    return lead + core + trail


def block(element, depth=0):
    tag = element.tag
    if tag == "paragraph":
        level = element.get("heading")
        text = inline(element)
        return ("#" * int(level) + " " + text) if level else text
    if tag == "codeBlock":
        code = "".join(element.itertext())
        return f"```{element.get('language') or ''}\n{code}\n```"
    if tag == "list":
        lines = []
        ordered = element.get("kind") == "ordered"
        for number, item in enumerate(element.findall("listItem"), start=1):
            marker = f"{number}." if ordered else "-"
            parts = [block(child, depth + 1) for child in item]
            first = parts[0]
            lines.append("    " * depth + f"{marker} {first}")
            for rest in parts[1:]:
                lines.append(rest)
        return "\n".join(lines)
    if tag == "table":
        rows = []
        for row in element.findall("row"):
            cells = [" ".join(inline(p) for p in cell.findall("paragraph")) for cell in row.findall("cell")]
            rows.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
        rows.insert(1, "| " + " | ".join("---" for _ in element.find("row").findall("cell")) + " |")
        return "\n".join(rows)
    raise ValueError(tag)


def main(saved, output):
    data = json.loads(json.load(open(saved))[1]["text"])["data"]
    root = ET.fromstring(data["xml"])
    blocks = [block(child) for child in root]
    # drop the status line (second block)
    assert blocks[1].startswith("Status:"), blocks[1][:40]
    del blocks[1]
    open(output, "w", encoding="utf-8").write("\n\n".join(blocks) + "\n")
    print(f"rev {data['rev']}: {len(blocks)} blocks written")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
