#!/usr/bin/env python3
"""Draw the two federal emblems as SVG into ../emblems/ (standard library only).

    US.svg   national colors as of April 1865: 13 stripes, 35 stars (official from July 4, 1863,
             after West Virginia; Nevada's 36th star became official July 4, 1865)
    USN.svg  U.S. Navy union jack of the same date: the blue union alone, 35 stars

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
    (OUT / "USN.svg").write_text(svg(UW, UH, union, "U.S. Navy union jack, 35 stars, 1865"))
    print("wrote", OUT / "US.svg", OUT / "USN.svg")


if __name__ == "__main__":
    main()
