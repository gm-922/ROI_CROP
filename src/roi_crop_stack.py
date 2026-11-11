#!/usr/bin/env python3
"""Crop a camera frame using a G-code Stack Mask outline.

The Mask->camera mapping is supplied separately. This script does NOT
infer camera calibration from G-code data alone.

Example:
  python src/roi_crop_stack.py \
      --mask /path/to/stack.png --camera /path/to/frame.jpg \
      --calibration experiments/roi_crop_stack_poc/demo_calibration.json \
      --output-dir output --margin 35
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def read_stack_mask(path: str | Path, threshold: int = 10) -> tuple[np.ndarray, np.ndarray]:
    """Read an 8-bit Stack Mask; select nonblack predicted-print regions.

    Threshold 10 applies to synthetic black/gray/white masks, NOT camera photos.
    """
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Cannot read stack mask: {path}")
    if image.ndim == 2:
        gray = image
    elif image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if gray.dtype != np.uint8:
        raise ValueError("This PoC supports only 8-bit image masks")
    binary = np.uint8(gray > threshold) * 255
    return gray, binary


def mask_bbox_xyxy(binary: np.ndarray) -> tuple[int, int, int, int]:
    """Exclusive-ended bbox (xmin, ymin, xmax, ymax) over nonzero mask pixels."""
    coords = cv2.findNonZero(binary)
    if coords is None:
        raise ValueError("The reference stack mask contains no non-black pixels")
    x, y, w, h = cv2.boundingRect(coords)
    return int(x), int(y), int(x + w), int(y + h)


def get_affine(calibration_path: str | Path) -> np.ndarray:
    d = json.loads(Path(calibration_path).read_text(encoding="utf-8"))
    M = np.asarray(d["mask_to_camera_affine_2x3"], dtype=np.float64)
    if M.shape != (2, 3) or not np.isfinite(M).all():
        raise ValueError("mask_to_camera_affine_2x3 must be a finite 2x3 matrix")
    if abs(np.linalg.det(M[:, :2])) < 1e-10:
        raise ValueError("Singular affine calibration matrix")
    return M


def compute_roi(binary: np.ndarray, affine: np.ndarray, camera_shape: tuple[int, ...],
                margin: int = 35) -> dict:
    if margin < 0:
        raise ValueError("Margin must be >= 0")
    bbox = mask_bbox_xyxy(binary)
    x0, y0, x1, y1 = bbox
    corners = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float64)
    projected = corners @ affine[:, :2].T + affine[:, 2]
    left = int(np.floor(np.min(projected[:, 0]))) - margin
    top = int(np.floor(np.min(projected[:, 1]))) - margin
    right = int(np.ceil(np.max(projected[:, 0]))) + margin
    bottom = int(np.ceil(np.max(projected[:, 1]))) + margin
    h, w = camera_shape[:2]
    left, right = max(0, left), min(w, right)
    top, bottom = max(0, top), min(h, bottom)
    if right <= left or bottom <= top:
        raise ValueError("Transformed ROI does not intersect camera image")
    return {
        "mask_bbox_xyxy_exclusive": list(map(int, bbox)),
        "projected_mask_corners_xy": projected.tolist(),
        "camera_crop_xyxy_exclusive": [left, top, right, bottom],
        "camera_crop_wh": [right - left, bottom - top],
        "margin_camera_px": margin,
    }


def make_preview(camera: np.ndarray, binary_mask: np.ndarray, affine: np.ndarray, result: dict) -> np.ndarray:
    image = camera.copy()
    h, w = camera.shape[:2]
    transformed = cv2.warpAffine(
        binary_mask, affine, (w, h), flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0
    ) > 0
    cyan = np.array((255, 200, 35), dtype=np.float32)  # OpenCV BGR
    out = image.astype(np.float32)
    out[transformed] = 0.73 * out[transformed] + 0.27 * cyan
    image = np.uint8(np.clip(out, 0, 255))
    polygon = np.round(result["projected_mask_corners_xy"]).astype(np.int32)
    cv2.polylines(image, [polygon], True, (0, 195, 255), 3, cv2.LINE_AA)
    x1, y1, x2, y2 = result["camera_crop_xyxy_exclusive"]
    cv2.rectangle(image, (x1, y1), (x2 - 1, y2 - 1), (42, 225, 60), 4, cv2.LINE_AA)
    label_y = max(32, y1 - 14)
    label = "STACK MASK -> CAMERA (PROVISIONAL)"
    cv2.putText(image, label, (max(4, x1 - 30), label_y),
                cv2.FONT_HERSHEY_SIMPLEX, .82, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(image, label, (max(4, x1 - 30), label_y),
                cv2.FONT_HERSHEY_SIMPLEX, .82, (255, 255, 255), 2, cv2.LINE_AA)
    return image


def process(mask_path: str | Path, camera_path: str | Path, calibration_path: str | Path,
            output_dir: str | Path, margin: int = 35, threshold: int = 10) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _, binary = read_stack_mask(mask_path, threshold=threshold)
    camera = cv2.imread(str(camera_path), cv2.IMREAD_COLOR)
    if camera is None:
        raise FileNotFoundError(f"Cannot read camera image: {camera_path}")
    affine = get_affine(calibration_path)
    result = compute_roi(binary, affine, camera.shape, margin)
    x1, y1, x2, y2 = result["camera_crop_xyxy_exclusive"]
    cropped = camera[y1:y2, x1:x2]
    preview = make_preview(camera, binary, affine, result)
    ok1 = cv2.imwrite(str(out / "roi_overlay.jpg"), preview)
    ok2 = cv2.imwrite(str(out / "roi_crop.jpg"), cropped)
    ok3 = cv2.imwrite(str(out / "stack_binary.png"), binary)
    if not all((ok1, ok2, ok3)):
        raise RuntimeError("Could not write one or more result files")
    cal = json.loads(Path(calibration_path).read_text(encoding="utf-8"))
    metadata = {
        "status": "proof_of_concept__not_same_layer__uncalibrated",
        "mask_file": Path(mask_path).name,
        "camera_file": Path(camera_path).name,
        "camera_wh": list(camera.shape[1::-1]),
        "stack_mask_wh": list(binary.shape[1::-1]),
        "mask_foreground_threshold": threshold,
        "calibration_file": Path(calibration_path).name,
        "calibration_notes": cal.get("notes", ""),
        "mask_to_camera_affine_2x3": affine.tolist(),
        **result,
    }
    (out / "roi_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mask", required=True)
    p.add_argument("--camera", required=True)
    p.add_argument("--calibration", required=True)
    p.add_argument("--output-dir", default="output")
    p.add_argument("--margin", type=int, default=35, help="Camera-space pixels")
    p.add_argument("--threshold", type=int, default=10, help="Synthetic stack mask threshold")
    a = p.parse_args()
    print(json.dumps(
        process(a.mask, a.camera, a.calibration, a.output_dir, a.margin, a.threshold),
        ensure_ascii=False, indent=2
    ))


if __name__ == "__main__":
    main()
