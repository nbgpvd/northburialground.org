#!/usr/bin/env python3
"""Draw the two federal emblems as SVG into ../emblems/ (standard library only).

    US.svg   national colors as of April 1865: 13 stripes, 35 stars (official from July 4, 1863,
             after West Virginia; Nevada's 36th star became official July 4, 1865)
    USN.svg  First Navy Jack: thirteen red and white stripes, an uncoiled rattlesnake, and
             DONT TREAD ON ME. Chosen by the editor as the sailors' emblem. It is not the jack of
             1865 (then the blue union with its stars); it is the 1776 design as revived by the
             Navy in 2002.

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


def first_navy_jack():
    import math
    W,H=190,100; sh=H/13
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><title>First Navy Jack</title>']
    for i in range(13): out.append(f'<rect y="{i*sh:.3f}" width="{W}" height="{sh+.05:.3f}" fill="{"#B22234" if i%2==0 else "#FFFFFF"}"/>')
    # snake centreline: lower-left (tail) to upper-right (head), undulating
    pts=[]
    x0,y0,x1,y1=22,70,160,22
    for k in range(0,201):
        t=k/200; x=x0+(x1-x0)*t; y=y0+(y1-y0)*t
        amp=9*math.sin(math.pi*min(1,t*1.15))   # taper at the ends
        nx,ny=0.33,0.94                          # normal to the diagonal (approx)
        s=math.sin(t*math.pi*4.0)
        pts.append((x+nx*amp*s, y+ny*amp*s))
    d="M"+" L".join(f"{x:.2f},{y:.2f}" for x,y in pts)
    out.append(f'<path d="{d}" fill="none" stroke="#2b1d0e" stroke-width="7.6" stroke-linecap="round" stroke-linejoin="round"/>')
    out.append(f'<path d="{d}" fill="none" stroke="#a07a35" stroke-width="5.8" stroke-linecap="round" stroke-linejoin="round"/>')
    out.append(f'<path d="{d}" fill="none" stroke="#5a3f17" stroke-width="2.2" stroke-dasharray="2.2 2.6" stroke-linecap="round"/>')
    # rattle at the tail
    tx,ty=pts[0]; ang=math.atan2(pts[0][1]-pts[6][1], pts[0][0]-pts[6][0])
    for j in range(5):
        cx=tx+math.cos(ang)*(2.2+j*2.3); cy=ty+math.sin(ang)*(2.2+j*2.3); r=2.9-j*0.35
        out.append(f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{r*0.75:.2f}" ry="{r:.2f}" transform="rotate({math.degrees(ang):.1f} {cx:.2f} {cy:.2f})" fill="#d9c48f" stroke="#2b1d0e" stroke-width=".6"/>')
    # head
    hx,hy=pts[-1]; a=math.atan2(pts[-1][1]-pts[-8][1], pts[-1][0]-pts[-8][0]); deg=math.degrees(a)
    out.append(f'<g transform="translate({hx:.2f} {hy:.2f}) rotate({deg:.1f})">'
               '<path d="M-2,-4.3 C4,-5.2 9,-3 10.5,0 C9,3 4,5.2 -2,4.3 Z" fill="#a07a35" stroke="#2b1d0e" stroke-width=".8"/>'
               '<circle cx="5.2" cy="-1.9" r=".9" fill="#111"/>'
               '<path d="M10.3,0 L15,0 M15,0 L17,-1.3 M15,0 L17,1.3" stroke="#111" stroke-width=".7" fill="none" stroke-linecap="round"/></g>')
    out.append('<text x="95" y="93.5" text-anchor="middle" font-family="Georgia, \'Times New Roman\', serif" font-weight="bold" font-size="10.2" letter-spacing=".6" fill="#111">DONT TREAD ON ME</text>')
    out.append('</svg>')

    return "\n".join(out) + "\n"


def main():
    OUT.mkdir(exist_ok=True)
    sh = H / 13
    stripes = "".join(f'<rect y="{i * sh:.3f}" width="{W:g}" height="{sh:.3f}" fill="{RED if i % 2 == 0 else WHITE}"/>'
                      for i in range(13))
    union = f'<rect width="{UW:g}" height="{UH:.3f}" fill="{BLUE}"/><g fill="{WHITE}">{stars(UW, UH)}</g>'
    (OUT / "US.svg").write_text(svg(W, H, stripes + union, "Flag of the United States, 35 stars, April 1865"))
    (OUT / "USN.svg").write_text(first_navy_jack())
    print("wrote", OUT / "US.svg", OUT / "USN.svg")


if __name__ == "__main__":
    main()
