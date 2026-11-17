# patchproof — Independent Adversarial Review

Reviewer: an agent that did **not** build patchproof (SkillScan-standard gauntlet).
Date: 2026-11-17. Method: read all code first, re-ran the tool's own suite, did a
fresh-venv install, then attacked it with a **separately written** generator,
renderer, and export parsers (probe script kept at `/tmp/pp_probe.py` during the
review; all numbers below are from that independent code, not the tool's tests).

## 1. The tool's own test suite — re-run by reviewer

```
~/workspace/astro-tools/.venv/bin/python run_tests.py
Ran 17 tests — OK
border recovery over 28 sides: exact 28 (100.0%), within 1px 28 (100.0%)
```

**Claim "17/17, 28/28 border sides exact": VERIFIED** on the tool's own suite.

## 2. Fresh-install proof — PASS

- New venv in `/tmp/pp_fresh_venv` (`python3 -m venv`), `pip install` of the local
  folder succeeded (exit 0), console script `patchproof 0.1.0` present.
- Ran the installed CLI on `examples/`: output matches the README demo table
  exactly (6 PROVEN with the same borders/scores, `panel_photo.png` UNCERTAIN,
  score 29.2 vs threshold 6.0).
- Outputs present for every PROVEN panel: copied PNG, Unity `.meta`, Godot
  `.tres`, Android `.9.png`, plus `report.json`. No exports for the UNCERTAIN panel.

## 3. Independent ground-truth recovery — PASS (stronger than claimed)

Reviewer's own generator (direct numpy slicing, solid frame + accent corners,
no reuse of `examples/make_examples.py`): 6 new panels — flat 100×80 (15/15/10/10),
horizontal-gradient asymmetric 160×120 (25/8/20/30), thin-border 90×90 (6 all),
large-border 180×140 (40/40/35/35), asymmetric transparent padding
(7/5/13/9 padding + 13/19/11/17 borders), vertical-gradient 140×100 (18 all).

**Result: 24/24 border sides EXACT (0 px error on every side), 24/24 within 1 px,
all verdicts PROVEN, all content-padding values exact.** The headline claim
generalises beyond the tool's own fixtures.

## 4. Abstention — PASS

- Checkerboard centre (150×110): **UNCERTAIN**, score 73.25.
- Brick-pattern centre (150×110): **UNCERTAIN**, score 31.50.
- Photo-like image (reviewer's own method: coarse random noise, bicubic upscale,
  sinusoidal shading): **UNCERTAIN**, score 44.85.

Pattern/textured centres abstain as the README promises — no silent wrong borders,
and no engine exports are written for UNCERTAIN panels.

## 5. Independent resynthesis proof — PASS

Reviewer's own 9-slice renderer (corners copied verbatim, edges/centre bilinear)
using the detected borders of the asymmetric gradient panel, at 5 sizes
(160×120, 191×137, 321×241, 177×263, 250×199 — odd sizes included):
**all four corners pixel-identical to the original at every size.**

## 6. Export round-trips with reviewer's own parsers — PASS

- **Unity .meta:** my regex parser read `spriteBorder {x: 25, y: 30, z: 8, w: 20}`
  = (left, **bottom**, right, **top**) exactly as Unity requires for the
  L25/R8/T20/B30 panel. GUID is 32 lowercase hex chars (md5-based, deterministic).
- **Godot .tres:** all 4 patch margins and all 4 content margins parse back to
  the detected values.
- **Android .9.png:** size is (W+2)×(H+2); top marker row spans exactly columns
  1+L … W−R, left marker column exactly rows 1+T … H−B, marker pixels solid black;
  right/bottom content-box markers present (120 and 160 px for the test panel,
  matching its zero padding).

## 7. Flip symmetry — PASS

Flipping the reviewer's asymmetric panel (L25/R8/T20/B30) left-right gave
L8/R25/T20/B30, PROVEN — L/R swap exactly.

## 8. Malformed inputs — PASS (no tracebacks anywhere)

| Input | Result |
|---|---|
| Corrupt PNG (garbage bytes) | exit 0, panel verdict UNCERTAIN in report.json |
| Truncated real PNG (first ⅓ of bytes) | exit 0, UNCERTAIN |
| 1×1 PNG | UNCERTAIN, reason "content is only 1x1px — too small to slice" |
| Fully transparent 64×64 | UNCERTAIN, reason cites transparency |
| Empty folder | exit 2, one-line error "no PNG files found" |
| Non-PNG file as target | exit 2, one-line error "not a PNG file" |
| JPEG bytes in a `.png` file | No crash (Pillow sniffs content and loads it; panel PROVEN). Observation only — see limits. |

## 9. Bug found and FIXED

**report.json gave border numbers for UNCERTAIN panels.** For `panel_photo.png`
the JSON contained `"borders": {"left": 74, "right": 93, "top": 26, "bottom": 108}`
— failed-detection candidates presented in the same field as proven values,
against the README's "never given made-up numbers" promise (the CLI table and
exports already withheld them; only the JSON leaked them).

Fix (one place, `patchproof/cli.py`, `_process`): the report entry now writes
`borders = det.borders if verdict == "PROVEN" else None`, with a comment saying why.
After the fix: full suite still **17/17 OK (28/28 exact)**, all 21 independent
probes still pass, and `panel_photo.png` reports `"borders": null` with its reason.

No other bugs found. No other code was changed.

## 10. Honest remaining limits (reviewer-confirmed or observed)

- README's stated limits all held up under probing: flat/gradient centres only
  (patterns abstain), one panel per image, PNG only, exports format-checked but
  not yet imported into a live Unity/Godot project by this review either.
- `demo_compare.png` (a side-by-side comparison picture, not a panel) is reported
  PROVEN with left border 252 — the score (1.78) is genuinely low because both
  halves share a flat centre, so the slice is *provably* low-distortion, but the
  numbers are semantically meaningless for that image. The README already flags
  this case; users should only feed actual panels.
- A JPEG renamed to `.png` is loaded by content sniffing (Pillow behaviour) and
  can be PROVEN. Harmless for a local tool, but "PNG only" means "extension-checked,
  content-sniffed", not strict format validation.
- The `detect()` API (unlike the CLI report after the fix) still returns the
  candidate borders dict on UNCERTAIN detections; API callers must check
  `verdict` before using `borders`. The CLI — the shipped surface — is now safe.
- Detection is score-based, not semantic: a low distortion score proves a slice
  stretches cleanly, not that the borders are where a designer would put them.
  The README says this too.

## Addendum — benchmark round (2026-11-17)

A rival-benchmark round was run after this review (details in the internal
`BENCHMARK_INTERNAL.md`, which is not part of the public repo). A shared
real-world-style suite (14 panels with known ground-truth borders: textured
centres, asymmetric ornaments, 2–4px borders, drop shadow/glow,
semi-transparent edges, a photographic panel, odd sizes) plus a held-out set
(8 panels, different seeds/sizes) found one real defect in patchproof and
one unserved class:

- **Fixed: a silent wrong PROVEN.** On a stationary-texture (parchment)
  centre the classic settle could drift to borders far from the truth that
  still scored just under the threshold (shrinking a noisy centre lowers
  its RMS residual). Fix, at technique level in `core.py`: an independent
  mean-profile estimator cross-checks any borderline classic pass
  (disagreement > 2px discards it), and a stationary-texture verification
  path (mean-stationarity within the same threshold + an autocorrelation
  periodicity veto + the usual corner-identity resynthesis) can prove
  texture centres honestly.
- **Closed: parchment / stationary-grain centres** are now PROVEN exact on
  the shared suite and on the held-out set (which also validated the fix
  with no regressions: 0 wrong on both sets after the fix).
- **Left open, deliberately:** repeating-pattern centres and directional
  (wood-grain) centres still abstain — stretching would rescale the
  pattern/grain period, and the honest fix (tile-mode export) is a future
  feature. README's limits were updated to say exactly this.
- Re-verified after the fix: own suite **17/17, 28/28 exact**; shipped
  examples output identical to the README demo; pattern/photo abstention
  and export round-trips unaffected.

## Verdict

**PASS.** Headline claims verified independently: 17/17 own tests (28/28 exact),
24/24 exact on brand-new independent fixtures, abstention on pattern/photo
centres, corner-identical resynthesis under an independent renderer, and correct
Unity/Godot/Android export formats under independent parsers. One honesty bug
(UNCERTAIN borders in report.json) found, fixed, and re-verified.
