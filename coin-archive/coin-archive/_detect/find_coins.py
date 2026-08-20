#!/usr/bin/env python3
"""Detect coins in a photograph and report their bounding circles."""
import sys
import cv2
import numpy as np
from PIL import Image, ImageOps

def load(path):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return np.array(im)

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
        found = np.round(circles[0]).astype(int)
        if expected and len(found) >= expected:
            best = found[:expected]
            break
        if len(found) > len(best):
            best = found
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
