"""Captura los overlays HTML en PNG transparentes usando Chrome instalado."""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--out", default="frames")
    args = parser.parse_args()

    root = Path.cwd()
    files = [Path(name) for name in args.files]
    if args.all:
        files = sorted(p for p in root.glob("[0-9][0-9]_*.html") if not p.name.startswith("00"))
    if not files:
        raise SystemExit("Indica archivos HTML o usa --all")

    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if not chrome.exists():
        raise SystemExit(f"No se encontró Chrome en {chrome}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            executable_path=str(chrome),
            args=["--hide-scrollbars", "--force-color-profile=srgb", "--allow-file-access-from-files"],
        )
        for html in files:
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.goto(html.resolve().as_uri() + "?paused=1&loop=0", wait_until="load", timeout=15_000)
            page.wait_for_function("window.Overlay && window.Overlay.duration > 0", timeout=15_000)
            meta = page.evaluate("() => ({duration: Overlay.duration, canvas: Overlay.canvas})")
            duration = float(meta["duration"])
            canvas = meta["canvas"]
            page.set_viewport_size({"width": int(canvas["width"]), "height": int(canvas["height"])})
            total = round(duration * args.fps) + 1
            dest = root / args.out / html.stem
            dest.mkdir(parents=True, exist_ok=True)
            print(f"{html.stem}: {canvas['width']}x{canvas['height']} · {duration:.2f}s · {total} frames")
            for index in range(total):
                page.evaluate("t => Overlay.seek(t)", index / args.fps)
                page.screenshot(path=str(dest / f"{index:04d}.png"), omit_background=True)
                if index % 30 == 0:
                    print(f"  {index}/{total}")
            audit = page.evaluate("() => Overlay.audit()")
            print(f"  audit={audit}")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()

