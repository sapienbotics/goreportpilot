"""
Verify C-fix colour parity: user hex in → exact hex in PPTX XML out.

Phase 3 parity fix — C-fix verification.

What it tests
-------------
For every theme whose ``brand_tint_strategy='header_band'``
(modern_clean, dark_executive, gradient_modern):

  1. Runs ``apply_cover_customization`` with a known brand primary hex
     and accent hex.
  2. Saves the PPTX to a temp file, unzips it, reads ``ppt/slides/slide1.xml``.
  3. Walks every ``<a:solidFill>/<a:srgbClr>`` element and asserts:
        * At least one element has ``val="{brand_hex_upper}"``.
        * No ``<a:lumMod>``, ``<a:lumOff>``, ``<a:tint>``, ``<a:shade>``
          children remain on ANY srgbClr (would cause render-time drift).
     Same for accent.

Exits 0 on full parity, 1 otherwise.

Run
---

    python backend/scripts/verify_cover_color_parity.py
"""
from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Allow running as a standalone script: make the backend importable.
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from pptx import Presentation  # noqa: E402

from services.cover_customization import apply_cover_customization  # noqa: E402
from services.theme_layout import THEME_LAYOUT, supports_brand_tint  # noqa: E402


# ── Config ────────────────────────────────────────────────────────────────────

BRAND_HEX  = "#3AB2CB"          # The exact hex that used to drift to #4CC5D5.
ACCENT_HEX = "#3ACBC1"
TEMPLATES  = BACKEND / "templates" / "pptx"


# ── XML parsing helpers ───────────────────────────────────────────────────────

_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

_MODIFIER_TAGS = (
    "lumMod", "lumOff", "tint", "shade",
    "alpha", "gamma", "invGamma",
    "satMod", "satOff", "hueMod", "hueOff",
)


def _read_slide1_xml(pptx_path: Path) -> ET.Element:
    with zipfile.ZipFile(pptx_path) as z:
        with z.open("ppt/slides/slide1.xml") as f:
            return ET.fromstring(f.read())


def _collect_srgb_clrs(root: ET.Element) -> list[ET.Element]:
    """Return every ``<a:srgbClr>`` under ``<a:solidFill>`` in the slide."""
    out: list[ET.Element] = []
    for solid in root.iter(f"{{{_NS['a']}}}solidFill"):
        for srgb in solid.findall(f"{{{_NS['a']}}}srgbClr"):
            out.append(srgb)
    return out


# ── Assertions ────────────────────────────────────────────────────────────────


def _hex_upper(hex_str: str) -> str:
    v = hex_str.strip().lstrip("#").upper()
    return v


def _check_color_present(
    srgbs: list[ET.Element], target_hex: str, label: str,
) -> tuple[bool, str]:
    upper = _hex_upper(target_hex)
    matches = [s for s in srgbs if (s.get("val") or "").upper() == upper]
    if not matches:
        vals = sorted({(s.get("val") or "?") for s in srgbs})
        return False, (
            f"[{label}] expected val={upper!r} not found among {vals}"
        )
    return True, f"[{label}] found {len(matches)} srgbClr with val={upper!r}"


def _check_no_modifiers(
    srgbs: list[ET.Element], target_hex: str, label: str,
) -> tuple[bool, str]:
    upper = _hex_upper(target_hex)
    for srgb in srgbs:
        if (srgb.get("val") or "").upper() != upper:
            continue
        remaining = []
        for tag in _MODIFIER_TAGS:
            found = srgb.findall(f"{{{_NS['a']}}}{tag}")
            if found:
                remaining.append(f"{tag}×{len(found)}")
        if remaining:
            return False, (
                f"[{label}] srgbClr val={upper!r} still has modifiers: "
                + ", ".join(remaining)
            )
    return True, f"[{label}] srgbClr val={upper!r} has no luminance modifiers"


# ── Test driver ───────────────────────────────────────────────────────────────


def run_for_theme(theme: str, tmp_dir: Path) -> list[tuple[str, bool, str]]:
    """Build a customised PPTX for ``theme`` and return assertion results."""
    tpl = TEMPLATES / f"{theme}.pptx"
    prs = Presentation(str(tpl))

    apply_cover_customization(
        prs,
        theme=theme,
        headline="Test Client",
        period_label="April 2026",
        subtitle="Executive Brief",
        brand_primary_color=BRAND_HEX,
        accent_color=ACCENT_HEX,
    )

    out = tmp_dir / f"{theme}_verified.pptx"
    prs.save(str(out))

    root = _read_slide1_xml(out)
    srgbs = _collect_srgb_clrs(root)

    results: list[tuple[str, bool, str]] = []

    # Brand hex parity.
    ok, msg = _check_color_present(srgbs, BRAND_HEX, "brand-present")
    results.append((theme, ok, msg))
    ok, msg = _check_no_modifiers(srgbs, BRAND_HEX, "brand-scrub")
    results.append((theme, ok, msg))

    # Accent hex parity.
    ok, msg = _check_color_present(srgbs, ACCENT_HEX, "accent-present")
    results.append((theme, ok, msg))
    ok, msg = _check_no_modifiers(srgbs, ACCENT_HEX, "accent-scrub")
    results.append((theme, ok, msg))

    return results


def main() -> int:
    if not TEMPLATES.exists():
        print(f"[ERR] Templates dir missing: {TEMPLATES}", file=sys.stderr)
        return 2

    themes = [t for t in THEME_LAYOUT if supports_brand_tint(t)]
    print(f"Testing {len(themes)} brand-tinted themes: {themes}")
    print(f"Brand  hex: {BRAND_HEX}")
    print(f"Accent hex: {ACCENT_HEX}")
    print()

    all_pass = True
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for theme in themes:
            print(f"=== {theme} ===")
            results = run_for_theme(theme, tmp_path)
            for (_, ok, msg) in results:
                status = "PASS" if ok else "FAIL"
                if not ok:
                    all_pass = False
                print(f"  [{status}] {msg}")
            print()

    if all_pass:
        print("All colour-parity assertions passed.")
        return 0
    print("One or more assertions FAILED — see output above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
