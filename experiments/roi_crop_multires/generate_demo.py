#!/usr/bin/env python3
"""Recreate real PNG outputs from synthetic fixtures (not actual camera photos)."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from roi_crop_multires import process


def main():
    outputs = HERE / "runs"
    outputs.mkdir(parents=True, exist_ok=True)
    mask = np.zeros((60, 80), np.uint8)
    mask[10:30, 20:40] = 255
    mask_path = outputs / "stack_mask_synthetic.png"
    assert cv2.imwrite(str(mask_path), mask)
    source = np.zeros((1536, 2048, 3), np.uint8)
    source[220:460, 400:600, :] = (40, 220, 240)
    summaries = []
    for width, height in ((2048, 1536), (1920, 1080), (1280, 720), (640, 480)):
        cam = cv2.resize(source, (width, height), interpolation=cv2.INTER_NEAREST)
        frame = outputs / f"camera_{width}x{height}.png"
        assert cv2.imwrite(str(frame), cam)
        info = process(mask_path, frame, HERE / "demo_calibration.json",
                       outputs / f"{width}x{height}")
        summaries.append({"resolution_wh": [width, height],
                          "crop_xyxy": info["camera_crop_xyxy_exclusive"],
                          "crop_wh": info["camera_crop_wh"],
                          "margin_xy": info["margin_camera_xy_px"]})
        print(f"{width}x{height}: {info['camera_crop_xyxy_exclusive']} -> {info['camera_crop_wh']}")
    (outputs / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
