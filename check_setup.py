"""
Setup check — run this first.
=============================

    python check_setup.py

Checks your Python version and the (tiny) package list. Makes NO API calls and
needs NO key — this whole dive is an offline simulator. Uses only the standard
library, so it runs even before `pip install`.
"""

import importlib.util
import os
import sys

_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def _c(text, code):
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def ok(msg):
    print(f"  {_c('✓', '32')} {msg}")


def fail(msg):
    print(f"  {_c('✗', '31')} {msg}")


def check_python():
    print("Python version")
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 10):
        ok(f"Python {major}.{minor} (3.10+ required)")
        return True
    fail(f"Python {major}.{minor} — this repo needs Python 3.10 or newer.")
    return False


def check_dependencies():
    print("\nDependencies")
    missing = []
    for import_name, pip_name, purpose in [
        ("rich", "rich", "renders the timeline output"),
        ("dotenv", "python-dotenv", "parity with the sibling repos (no key needed)"),
    ]:
        if importlib.util.find_spec(import_name) is not None:
            ok(f"{pip_name} — {purpose}")
        else:
            fail(f"{pip_name} MISSING — {purpose}")
            missing.append(pip_name)
    if missing:
        print("\n    Install with:  pip install -r requirements.txt")
    return not missing


def main():
    print(_c("Checking your setup for the Realtime Voice deep dive...\n", "1"))
    py = check_python()
    deps = check_dependencies()
    print("\nAPI key")
    ok("none needed — this dive is a fully offline simulator.")
    print()
    if py and deps:
        print(_c("All set! 🎉", "1;32"))
        print("Start here:  python examples/01_audio_is_frames.py")
        return 0
    print(_c("Not ready yet — fix the ✗ items above, then run this again.", "1;31"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
