# news-image-20261120 (make.fun entry)

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/friederickemiddleton7/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard)
[![reward](https://make.fun/badge/news-image-20261120/friederickemiddleton7/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120)

One image that sums up the world news of Friday 20 November 2026: Russia's overnight missile and
bomber strike on Kyiv after Putin's vow of revenge, Anthropic's record Nasdaq listing past $2
trillion, the ICJ ruling that Myanmar committed genocide against the Rohingya, Cyclone Akvan closing
on India's Odisha coast, and Somalia ordering the UAE ambassador out — with a bottom line for the
Berlin coalition, bitcoin's four-month low, the COP31 draft and Colombia's protests.

## Files

- `entry.png` — the finished image, 1024x1024, RGB.
- `main.py` — entry point. Copies `entry.png` into `$MAKEFUN_OUTPUT_DIR` (default `/output`) using
  only the Python standard library. Deterministic: no network, no randomness, byte-identical output
  on every run.
- `make_image.py` — the generator that drew `entry.png` at build time with Pillow. Kept for
  reference; the grader never runs it.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

The program copies `entry.png` to `/output/entry.png` unchanged. Every text block is measured with
`textlength` before it is drawn, so nothing overflows its card; the generator exits non-zero if a
block would not fit.

## Licence

MIT — see `LICENSE`.