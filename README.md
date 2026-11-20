# news-image-20261120

One image that sums up Friday 20 November 2026: a dark front page with the
day's lead story (Russia's overnight missile and bomber strike on Kyiv),
four secondary cards (Anthropic's record IPO, the ICJ ruling on Myanmar,
Cyclone Akvan closing on Odisha, Somalia expelling the UAE envoy) and an
"also today" line for the rest.

## Files

- `entry.png` — the finished image, 1024x1024, RGB.
- `main.py` — entry point. Copies `entry.png` into `$MAKEFUN_OUTPUT_DIR`
  (default `/output`) using only the Python standard library. Deterministic:
  no network, no randomness, byte-identical output on every run.
- `make_image.py` — the generator that drew `entry.png` at build time with
  Pillow. It is kept for reference and is never run by the grader.

## Rebuild

```
python3 make_image.py     # writes entry.png beside the script
python3 main.py           # copies it into /output/entry.png
```

Every text block is measured with `textlength` before it is drawn, so nothing
overflows its card; the generator exits non-zero if a block would not fit.