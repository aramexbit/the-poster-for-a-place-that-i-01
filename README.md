# VELMARA — A Travel Poster for a Place That Isn't There

[![make.fun](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/aramexbit/the-poster-for-a-place-that-i-01/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/aramexbit/the-poster-for-a-place-that-i-01/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)

A [make.fun](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539) bounty entry: a program that paints a travel poster for **VELMARA**, a white-cliff city above a violet sea, under two suns — one large and golden, one small and rose-red. A single sailboat crosses the calm teal water, and the lighthouse beam sweeps out to sea.

The only text in the picture is the name of the place itself.

## The poster

- **Sky (top ~55%):** indigo `#1B2A5E` melting through rose `#E86A7A` to gold `#F5B942` at the horizon. Two suns hang low on the right — one large and golden, one small and rose-red — with a few distant birds.
- **The town:** whitewashed houses with domes and terracotta roofs cluster on a white headland at the left, warm windows lit, a striped lighthouse at its tip sweeping a beam out to sea.
- **The sea (bottom ~30%):** teal `#14506B` to `#1E7A8C`, a golden glitter path under the suns, one small sailboat.
- **The name:** VELMARA, set large and centred just above the horizon in cream `#FFF6E0` with a dark shadow and a thin gold rule beneath it — the eye travels name → lighthouse → two suns → horizon.

## Verification

```sh
python3 main.py   # writes /output/entry.png
python3 main.py   # second run: byte-identical output
sha256sum /output/entry.png
```

Checked locally: 1024×1024, ~17 KB (cap 1,048,576 bytes), two runs produce the same sha256, no errors.

## How it works

`main.py` is pure Python 3.13 standard library — no Pillow, no network, no randomness. It draws the poster into an RGB buffer with small scanline helpers (gradient bands, circles, polygons, a hand-defined 5×7 bitmap font scaled up for the name) and writes a hand-encoded PNG (zlib + struct) to `/output/entry.png`.

The image is fully deterministic: run it twice and the bytes are identical.

## Run it

```sh
python3 main.py
```

Output: `/output/entry.png` (1024×1024, well under the 1 MiB cap).

## License

MIT — see [LICENSE](LICENSE).
