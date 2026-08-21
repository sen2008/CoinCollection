#!/usr/bin/env python3
"""Detect coins in a photograph and report their bounding circles."""
import sys
import cv2
import numpy as np
from PIL import Image, ImageOps

def load(path):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return np.array(im)

def looks_metallic(rgb, circle):
    """
    Reject circles that are not made of metal.

    The kitchen scale's readout is a bright cyan rectangle, and a circle landing
    on the digits passes every geometric test. Coins are grey, copper or silver:
    never strongly blue, and never that bright. This checks the average colour
    inside the circle rather than its shape.
    """
    x, y, r = circle
    h, w = rgb.shape[:2]
    y0, y1 = max(0, y - r), min(h, y + r)
    x0, x1 = max(0, x - r), min(w, x + r)
    patch = rgb[y0:y1, x0:x1]
    if patch.size == 0:
        return False
    red, green, blue = (float(patch[:, :, i].mean()) for i in range(3))
    if blue > red * 1.18:          # cyan / blue glow, not metal
        return False
    if blue > 150 and green > 150 and red < green * 0.9:
        return False               # bright backlit display
    return True


def pick_consistent(candidates, n):
    """
    Choose the n circles that look like a set of coins.

    Several of these photographs were taken on a kitchen scale, whose platter rim
    is a large, clean circle the detector loves. Coins in one frame are all about
    the same size, so the right answer is the n circles with the tightest spread
    of radii that do not sit on top of each other.
    """
    import itertools
    if len(candidates) < n:
        return []
    best, best_spread = [], None
    pool = sorted(candidates, key=lambda c: c[2])
    for combo in itertools.combinations(pool, n):
        radii = [c[2] for c in combo]
        spread = max(radii) / min(radii)
        if best_spread is not None and spread >= best_spread:
            continue
        clash = any(((a[0]-b[0])**2 + (a[1]-b[1])**2) ** .5 < (a[2]+b[2]) * 0.6
                    for a, b in itertools.combinations(combo, 2))
        if clash:
            continue
        best, best_spread = list(combo), spread
    return best


def detect(rgb, expected=None):
    h, w = rgb.shape[:2]
    scale = 700 / max(h, w)
    small = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    gray = cv2.medianBlur(gray, 5)
    sh, sw = gray.shape

    # A coin occupies a decent fraction of the frame in these shots.
    rmin, rmax = int(min(sh, sw) * 0.10), int(min(sh, sw) * 0.34)

    best = []
    for p2 in (60, 50, 40, 34, 30, 26):
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1,
                                   minDist=int(rmin * 1.5), param1=120, param2=p2,
                                   minRadius=rmin, maxRadius=rmax)
        if circles is None:
            continue
        # Colour is judged on `small`, because these coordinates are in its space.
        # Testing them against the full-size image samples the wrong patch.
        metallic = [tuple(map(int, c)) for c in np.round(circles[0]).astype(int)
                    if looks_metallic(small, tuple(map(int, c)))]
        if expected and len(metallic) >= expected:
            chosen = pick_consistent(metallic, expected)
            if chosen:
                best = chosen
                break
        if len(metallic) > len(best):
            best = metallic
    return [(int(x / scale), int(y / scale), int(r / scale)) for x, y, r in best]

def reading_order(circles):
    """Top-to-bottom, then left-to-right, tolerating loose placement."""
    if not circles:
        return []
    rows, avg_r = [], sum(c[2] for c in circles) / len(circles)
    for c in sorted(circles, key=lambda c: c[1]):
        for row in rows:
            if abs(row[0][1] - c[1]) < avg_r * 1.2:
                row.append(c); break
        else:
            rows.append([c])
    return [c for row in rows for c in sorted(row, key=lambda c: c[0])]

if __name__ == "__main__":
    path, expected = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None
    rgb = load(path)
    found = reading_order(detect(rgb, expected))
    print(f"{path}: {len(found)} circles in {rgb.shape[1]}x{rgb.shape[0]}")
    for i, (x, y, r) in enumerate(found, 1):
        print(f"  {i}: centre=({x},{y}) r={r}")
