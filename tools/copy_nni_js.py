"""Copy nni-model's js/nni.js into the page (app/js/nni.js), at the pinned commit.

Run from the repository folder, with a clone of nni-model checked out at the
commit requirements.txt pins:
    python tools/copy_nni_js.py ../nni-model
It copies js/nni.js unchanged and writes app/js/nni_js_source.json with the
commit and the file's SHA-256. tests/test_locked_block_js.py fails if the copy
changed, or if the commit is not the one requirements.txt pins.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGET = REPO / "app" / "js" / "nni.js"
SOURCE_RECORD = REPO / "app" / "js" / "nni_js_source.json"


def pinned_commit():
    """The nni-model commit requirements.txt installs."""
    text = (REPO / "requirements.txt").read_text(encoding="utf-8")
    return re.search(r"lavanito/nni-model@([0-9a-f]{40})", text).group(1)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(clone):
    clone = Path(clone)
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != pinned_commit():
        sys.exit(f"The clone is at {head}; requirements.txt pins {pinned_commit()}. Check out the pin first.")
    shutil.copyfile(clone / "js" / "nni.js", TARGET)
    record = {"note": "Written by tools/copy_nni_js.py; do not edit by hand.",
              "repository": "lavanito/nni-model", "file": "js/nni.js", "commit": head,
              "sha256": sha256(TARGET)}
    SOURCE_RECORD.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(f"Copied js/nni.js at {head[:7]} to {TARGET.relative_to(REPO)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else REPO.parent / "nni-model")
