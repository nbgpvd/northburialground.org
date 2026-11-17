#!/usr/bin/env python3
"""Draw the national-colors emblem as SVG into ../emblems/ (standard library only).

    US.svg     national colors as of April 1865: 13 stripes, 35 stars (official from July 4, 1863,
               after West Virginia; Nevada's 36th star became official July 4, 1865)
    USCAV.svg  U.S. cavalry company guidon, pattern of War Department General Orders No. 4,
               January 18, 1862 ("like the United States flag with stars and stripes"), on the
               1834 swallow-tailed form, 27 x 41 in with a 15 in swallowtail; 35 gilt stars in two
               concentric circles (21 and 10) with one star in each corner of the canton.

No star pattern was fixed by law until 1912. Five rows of seven, used here, is one of the
common 35-star arrangements. Colors are the conventional red, white and dark blue.
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "emblems"
RED, WHITE, BLUE = "#B22234", "#FFFFFF", "#3C3B6E"
H, W = 100.0, 160.0                 # flag hoist and fly
UH, UW = H * 7 / 13, H * 0.76       # union: seven stripes deep


def star(cx, cy, r):
    import math
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.382
        pts.append(f"{cx + rr * math.cos(a):.2f},{cy + rr * math.sin(a):.2f}")
    return f'<polygon points="{" ".join(pts)}"/>'


def stars(w, h, rows=5, cols=7):
    dx, dy = w / cols, h / rows
    r = min(dx, dy) * 0.42
    return "".join(star(dx * (c + .5), dy * (rr + .5), r) for rr in range(rows) for c in range(cols))


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:.2f}" width="{w:g}" height="{h:.2f}">'
            f"<title>{title}</title>{body}</svg>\n")


def main():
    OUT.mkdir(exist_ok=True)
    sh = H / 13
    stripes = "".join(f'<rect y="{i * sh:.3f}" width="{W:g}" height="{sh:.3f}" fill="{RED if i % 2 == 0 else WHITE}"/>'
                      for i in range(13))
    union = f'<rect width="{UW:g}" height="{UH:.3f}" fill="{BLUE}"/><g fill="{WHITE}">{stars(UW, UH)}</g>'
    (OUT / "US.svg").write_text(svg(W, H, stripes + union, "Flag of the United States, 35 stars, April 1865"))
    print("wrote", OUT / "US.svg")
    guidon()


def guidon():
    """Swallow-tailed cavalry guidon: hoist 27, fly 41, tails cut 15 deep (inches, scaled x4)."""
    import math
    k = 4.0
    gh, gw, cut = 27 * k, 41 * k, 15 * k
    sh = gh / 13
    stripes = "".join(f'<rect y="{i * sh:.3f}" width="{gw:g}" height="{sh:.3f}" fill="{RED if i % 2 == 0 else WHITE}"/>'
                      for i in range(13))
    cw, ch = gh * 0.62, sh * 7          # canton: seven stripes deep
    gold = "#D4A93A"
    cx, cy = cw / 2, ch / 2
    r = min(cw, ch) * 0.043
    st = [star(cx + rad * math.cos(-math.pi / 2 + 2 * math.pi * i / n), cy + rad * math.sin(-math.pi / 2 + 2 * math.pi * i / n), r)
          for n, rad in ((21, min(cw, ch) * 0.40), (10, min(cw, ch) * 0.22)) for i in range(n)]
    m = r * 1.7
    st += [star(x, y, r) for x in (m, cw - m) for y in (m, ch - m)]
    canton = f'<rect width="{cw:.2f}" height="{ch:.3f}" fill="{BLUE}"/><g fill="{gold}">{"".join(st)}</g>'
    clip = (f'<clipPath id="tail"><polygon points="0,0 {gw:g},0 {gw - cut:g},{gh / 2:g} {gw:g},{gh:g} 0,{gh:g}"/></clipPath>')
    body = f'<defs>{clip}</defs><g clip-path="url(#tail)">{stripes}{canton}</g>'
    (OUT / "USCAV.svg").write_text(svg(gw, gh, body, "U.S. cavalry guidon, pattern of 1862, 35 stars"))
    print("wrote", OUT / "USCAV.svg")


if __name__ == "__main__":
    main()
