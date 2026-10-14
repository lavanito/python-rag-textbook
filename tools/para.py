"""Helpers to find and extract numbered paragraphs from pdftotext output.
Usage:
  python3 -I tools/para.py find FILE REGEX [N]       # list matching lines with line numbers
  python3 -I tools/para.py para FILE NUMBER          # extract paragraph starting "NUMBER "
  python3 -I tools/para.py lines FILE START END      # raw lines
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data" / "raw" / "text" / "corpus_raw"
PARA_START = re.compile(r"^\d{1,2}\.\d{1,3}\s")


def load(name):
    return (BASE / name).read_text(encoding="utf-8", errors="replace").splitlines()


def join(lines):
    text = ""
    for line in lines:
        line = line.strip()
        if text.endswith("-") and line and line[0].islower():
            text = text[:-1] + line
        elif text:
            text = text + " " + line
        else:
            text = line
    return re.sub(r"\s+", " ", text).strip()


def para(name, number):
    lines = load(name)
    out = []
    for i, line in enumerate(lines):
        if line.startswith(number + " "):
            out.append(line)
            for nxt in lines[i + 1:]:
                if PARA_START.match(nxt) or nxt.strip() == "":
                    break
                out.append(nxt)
            text = join(out)
            complete = text.endswith((".", ":", ";", ")", "”"))
            print(f"[line {i+1}] complete={complete}\n{text}\n")
            out = []


cmd = sys.argv[1]
if cmd == "find":
    lines = load(sys.argv[2])
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 15
    shown = 0
    for i, line in enumerate(lines):
        if re.search(sys.argv[3], line, re.I):
            print(i + 1, line[:150])
            shown += 1
            if shown >= limit:
                break
elif cmd == "para":
    para(sys.argv[2], sys.argv[3])
elif cmd == "lines":
    lines = load(sys.argv[2])
    for i in range(int(sys.argv[3]) - 1, int(sys.argv[4])):
        print(lines[i])
