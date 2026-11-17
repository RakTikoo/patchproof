"""Synthetic UI panel factory with known ground-truth 9-slice borders.

Used to generate the shipped examples/ panels and the test fixtures.
Panels are built so the true borders are exact: corner blocks carry the
ornaments and rounded-corner cut-outs, edge strips are flat or bevelled
only along their cross direction, and the centre is flat or a smooth
2D linear gradient -- so the true centre is exactly the stretchable part.

Run directly to (re)generate the examples and the demo comparison image:
    python examples/make_examples.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

FRAME = (58, 64, 78, 255)        # frame / corner colour
FRAME_DARK = (38, 42, 54, 255)   # inner frame line
ACCENT = (232, 182, 66, 255)     # rivet colour
CENTRE_FLAT = (196, 205, 219, 255)


def _corner_block(arr, x0, y0, bw, bh, rivet: bool):
    """Paint one corner block: frame colour, elliptical transparent cut-out
    at the outer corner, optional rivet."""
    sub = arr[y0:y0 + bh, x0:x0 + bw]
    sub[:, :] = FRAME
    # local coords measured from the INNER corner of the block
    lx = np.abs(np.arange(bw)[None, :] - (bw - 1 if x0 == 0 else 0))
    ly = np.abs(np.arange(bh)[:, None] - (bh - 1 if y0 == 0 else 0))
    # distance from inner corner, normalised: >1 near the outer corner
    d = np.sqrt((lx / max(bw - 1, 1)) ** 2 + (ly / max(bh - 1, 1)) ** 2)
    outside = d > 1.0
    # only cut the part of the block that is towards the outer corner
    if x0 == 0:
        outside &= (np.arange(bw)[None, :] < bw - 1)
    else:
        outside &= (np.arange(bw)[None, :] > 0)
    if y0 == 0:
        outside &= (np.arange(bh)[:, None] < bh - 1)
    else:
        outside &= (np.arange(bh)[:, None] > 0)
    sub[outside] = (0, 0, 0, 0)
    if rivet:
        cx, cy = bw // 2, bh // 2
        r = max(2, min(bw, bh) // 5)
        yy, xx = np.mgrid[0:bh, 0:bw]
        disc = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
        opaque = sub[:, :, 3] > 0
        sub[disc & opaque] = ACCENT


def make_panel(kind="flat", w=120, h=96, borders=(14, 14, 14, 14),
               padding=(0, 0, 0, 0), noise=0.0, seed=7):
    """Build a panel. borders = (left, right, top, bottom) of the CONTENT;
    padding = (left, top, right, bottom) transparent margin around it.
    Returns (PIL.Image, truth dict)."""
    left, right, top, bottom = borders
    cw, ch = w - padding[0] - padding[2], h - padding[1] - padding[3]
    arr = np.zeros((ch, cw, 4), dtype=np.float64)

    yy, xx = np.mgrid[0:ch, 0:cw]
    if kind == "gradient":
        base = np.stack([
            120 + 0.55 * xx + 0.25 * yy,
            140 + 0.30 * xx + 0.45 * yy,
            175 + 0.20 * xx + 0.20 * yy,
            np.full_like(xx, 255.0),
        ], axis=2)
    else:  # flat centre (also the base for ornament / asym)
        base = np.zeros((ch, cw, 4))
        base[:, :] = CENTRE_FLAT
    arr[:] = base

    cx0, cx1, cy0, cy1 = left, cw - right, top, ch - bottom
    # top / bottom edge strips: bevel varies only along y (row), so each row
    # is constant along x across the centre columns.
    for y in range(top):
        shade = 0.82 + 0.18 * (y / max(top - 1, 1))
        arr[y, cx0:cx1] = tuple(c * shade for c in FRAME[:3]) + (255,)
    for i, y in enumerate(range(ch - bottom, ch)):
        shade = 1.0 - 0.18 * (i / max(bottom - 1, 1))
        arr[y, cx0:cx1] = tuple(c * shade for c in FRAME[:3]) + (255,)
    # left / right edge strips: bevel varies only along x (column).
    for x in range(left):
        shade = 0.82 + 0.18 * (x / max(left - 1, 1))
        arr[cy0:cy1, x] = tuple(c * shade for c in FRAME[:3]) + (255,)
    for i, x in enumerate(range(cw - right, cw)):
        shade = 1.0 - 0.18 * (i / max(right - 1, 1))
        arr[cy0:cy1, x] = tuple(c * shade for c in FRAME[:3]) + (255,)
    # inner frame lines, just inside the border strips
    if top >= 2:
        arr[top - 2:top, cx0:cx1] = FRAME_DARK
    if bottom >= 2:
        arr[ch - bottom:ch - bottom + 2, cx0:cx1] = FRAME_DARK
    if left >= 2:
        arr[cy0:cy1, left - 2:left] = FRAME_DARK
    if right >= 2:
        arr[cy0:cy1, cw - right:cw - right + 2] = FRAME_DARK
    # corners (painted last, they own their blocks)
    rivet = kind in ("ornament", "asym")
    _corner_block(arr, 0, 0, left, top, rivet)
    _corner_block(arr, cw - right, 0, right, top, rivet)
    _corner_block(arr, 0, ch - bottom, left, bottom, rivet)
    _corner_block(arr, cw - right, ch - bottom, right, bottom, rivet)

    if noise > 0:
        rng = np.random.default_rng(seed)
        arr[:, :, :3] += rng.uniform(-noise, noise, arr.shape[:2] + (1,))

    content = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    if any(padding):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        img.paste(content, (padding[0], padding[1]))
    else:
        img = content
    truth = {
        "borders": {"left": padding[0] + left, "right": padding[2] + right,
                    "top": padding[1] + top, "bottom": padding[3] + bottom},
        "padding": {"left": padding[0], "top": padding[1],
                    "right": padding[2], "bottom": padding[3]},
    }
    return img, truth


def make_photo(w=200, h=160, seed=3):
    """A smooth, photo-like image: no stretchable centre exists."""
    rng = np.random.default_rng(seed)
    small = rng.uniform(0, 255, (12, 16, 3)).astype(np.uint8)
    img = Image.fromarray(small, "RGB").resize((w, h), Image.BICUBIC)
    yy, xx = np.mgrid[0:h, 0:w]
    blob = np.exp(-(((xx - w * 0.7) ** 2) / (2 * (w * 0.18) ** 2)
                    + ((yy - h * 0.3) ** 2) / (2 * (h * 0.18) ** 2)))
    arr = np.asarray(img).astype(np.float64)
    arr[:, :, 0] = np.clip(arr[:, :, 0] + 90 * blob, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] - 60 * blob, 0, 255)
    out = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
    return out


def make_diagonal(w=160, h=120):
    """A panel-like image ruined by a diagonal stripe through the centre."""
    img = Image.new("RGBA", (w, h), CENTRE_FLAT)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=FRAME, width=10)
    d.line([0, h - 1, w - 1, 0], fill=(198, 64, 52, 255), width=14)
    return img


# The shipped example set: (filename, kwargs)
EXAMPLES = [
    ("panel_flat.png", dict(kind="flat", w=120, h=96,
                            borders=(14, 14, 14, 14), noise=1.0)),
    ("panel_gradient.png", dict(kind="gradient", w=128, h=96,
                                borders=(12, 12, 12, 12), noise=1.0)),
    ("panel_ornament.png", dict(kind="ornament", w=132, h=100,
                                borders=(18, 18, 18, 18))),
    ("panel_asym.png", dict(kind="asym", w=120, h=96,
                            borders=(10, 22, 8, 16))),
    ("panel_padded.png", dict(kind="flat", w=140, h=116,
                              borders=(12, 12, 12, 12),
                              padding=(10, 10, 10, 10), noise=1.0)),
    ("panel_photo.png", None),  # the abstention example
]


def build_examples(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    truths = {}
    for name, kwargs in EXAMPLES:
        if kwargs is None:
            img, truth = make_photo(), None
        else:
            img, truth = make_panel(**kwargs)
        img.save(out_dir / name)
        truths[name] = truth
    return truths


def build_demo_compare(out_dir: Path):
    """Naive stretch vs detected 9-slice, side by side at an odd size."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from patchproof.core import detect, render_9slice

    img, _ = make_panel(kind="ornament", w=132, h=100, borders=(18, 18, 18, 18))
    det = detect(img)
    if det.verdict != "PROVEN":
        raise RuntimeError(f"demo panel did not prove: {det.reason}")
    b = (det.borders["left"], det.borders["right"],
         det.borders["top"], det.borders["bottom"])
    tw, th = img.width + 90, img.height + 55  # 222 x 155, deliberately odd
    naive = img.resize((tw, th), Image.BILINEAR)
    sliced = render_9slice(img, b, tw, th)
    canvas = Image.new("RGBA", (tw * 2 + 12, th), (24, 24, 28, 255))
    canvas.paste(naive, (0, 0))
    canvas.paste(sliced, (tw + 12, 0))
    canvas.save(out_dir / "demo_compare.png")
    return det


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    build_examples(here)
    det = build_demo_compare(here)
    print(f"examples written to {here}")
    print(f"demo panel verdict: {det.verdict} score {det.score:.2f} "
          f"borders {det.borders}")
