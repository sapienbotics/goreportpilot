"""
Logo processor — handles background removal for uploaded logos.
Uses Pillow for lightweight background removal (detects solid white/light
backgrounds and makes them transparent). This avoids the heavy rembg
dependency which conflicts with matplotlib's numpy requirements.

For complex backgrounds, users should upload transparent PNGs directly.
"""
import io
import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


def _is_light_color(r: int, g: int, b: int, threshold: int = 240) -> bool:
    """Check if an RGB color is close to white/light."""
    return r >= threshold and g >= threshold and b >= threshold


def remove_background(image_bytes: bytes) -> Optional[bytes]:
    """
    Remove solid white/light backgrounds from a logo image.

    Strategy:
    1. Sample the 4 corners of the image to detect the background color
    2. If 3+ corners are the same light color, treat it as background
    3. Replace all pixels matching that color (within tolerance) with transparency

    Returns transparent PNG bytes, or None if no background was detected.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Already has transparency — just ensure PNG format
        if img.mode == "RGBA":
            alpha = img.getchannel("A")
            min_alpha = alpha.getextrema()[0]
            if min_alpha < 250:
                logger.info("Logo already has transparency — converting to PNG")
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                return buf.getvalue()

        # Convert to RGBA for transparency support
        img = img.convert("RGBA")
        w, h = img.size

        # Sample corners (5px in from each edge to avoid anti-aliasing artifacts)
        inset = min(5, w // 10, h // 10)
        corners = [
            img.getpixel((inset, inset)),              # top-left
            img.getpixel((w - 1 - inset, inset)),      # top-right
            img.getpixel((inset, h - 1 - inset)),      # bottom-left
            img.getpixel((w - 1 - inset, h - 1 - inset)),  # bottom-right
        ]

        # Check how many corners are light/white
        light_corners = [c for c in corners if _is_light_color(c[0], c[1], c[2])]
        if len(light_corners) < 3:
            logger.info("Logo background does not appear to be white/light — skipping removal")
            # Still convert to PNG for consistency
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()

        # Use the most common corner color as the background reference
        bg_color = light_corners[0][:3]  # RGB only
        tolerance = 20  # Allow slight color variation

        # Replace background pixels with transparency
        pixels = img.load()
        transparent_count = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if (abs(r - bg_color[0]) <= tolerance and
                    abs(g - bg_color[1]) <= tolerance and
                    abs(b - bg_color[2]) <= tolerance):
                    pixels[x, y] = (r, g, b, 0)  # Make transparent
                    transparent_count += 1

        pct = transparent_count / (w * h) * 100
        logger.info(
            "Logo background removed: %d pixels (%.1f%%) made transparent",
            transparent_count, pct,
        )

        # Sanity check: if we made >95% transparent, background detection was probably wrong
        if pct > 95:
            logger.warning("Background removal made >95%% transparent — reverting to original")
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    except Exception as exc:
        logger.warning("Logo background removal failed: %s — using original", exc)
        return None


def process_logo_upload(image_bytes: bytes, original_ext: str) -> tuple[bytes, str, bool]:
    """
    Process an uploaded logo: attempt background removal and return best version.

    Returns:
        (processed_bytes, extension, bg_removed)
        - processed_bytes: the image bytes to save
        - extension: "png" (always — for transparency support)
        - bg_removed: True if background was successfully removed
    """
    transparent = remove_background(image_bytes)
    if transparent is not None:
        return transparent, "png", True

    # Fallback: return original bytes, still convert to PNG
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "png", False
    except Exception:
        return image_bytes, original_ext, False
