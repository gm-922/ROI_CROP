#!/usr/bin/env python3
"""Resolution-adaptive Stack Mask ROI crop. The original PoC is unchanged.

Calibration can be reused ONLY for a known resize of the SAME camera framing.
Changed FoV, sensor crop, camera position, or angle requires new calibration.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from roi_crop_stack import get_affine, make_preview, mask_bbox_xyxy, read_stack_mask

MODES = ("stretch", "contain", "cover")


def resolve_affine(reference_affine: np.ndarray, reference_wh: tuple[int, int],
                   input_wh: tuple[int, int], mode: str | None) -> tuple[np.ndarray, dict]:
    """Compose mask-to-reference affine with the known reference-to-input resize."""
    rw, rh = reference_wh
    w, h = input_wh
    if any(type(v) is not int or v <= 0 for v in (rw, rh, w, h)):
        raise ValueError("reference_wh and input_wh must contain positive integers")
    m = np.asarray(reference_affine, dtype=np.float64)
    if m.shape != (2, 3) or not np.isfinite(m).all() or abs(np.linalg.det(m[:, :2])) < 1e-10:
        raise ValueError("reference_affine must be a finite non-singular 2x3 matrix")
    sx, sy = w / rw, h / rh
    if mode is None:
        if not math.isclose(sx, sy, rel_tol=1e-6):
            raise ValueError("Aspect ratio changed: set resize_mode after checking image geometry")
        mode = "stretch"
    if mode not in MODES:
        raise ValueError(f"resize_mode must be one of {MODES}")
    if mode == "stretch":
        ax, ay, tx, ty = sx, sy, 0., 0.
    else:
        s = min(sx, sy) if mode == "contain" else max(sx, sy)
        ax = ay = s
        tx, ty = (w - rw * s) / 2, (h - rh * s) / 2
    resize = np.array([[ax, 0, tx], [0, ay, ty]], dtype=np.float64)
    composed = np.empty((2, 3), dtype=np.float64)
    composed[:, :2] = resize[:, :2] @ m[:, :2]
    composed[:, 2] = resize[:, :2] @ m[:, 2] + resize[:, 2]
    return composed, {
        "reference_camera_wh": [rw, rh], "input_camera_wh": [w, h],
        "resize_mode": mode, "reference_to_input_affine_2x3": resize.tolist(),
        "reference_to_input_scale_xy": [ax, ay],
        "auto_rescale_applied": (w, h) != (rw, rh),
    }


def compute_roi_multires(binary: np.ndarray, affine: np.ndarray,
                         input_wh: tuple[int, int], margin_xy: tuple[int, int]) -> dict:
    """Project exclusive-ended mask bbox, add (x,y) margin, clip to image bounds."""
    w, h = input_wh
    mx, my = margin_xy
    if any(type(v) is not int or v < 0 for v in (mx, my)):
        raise ValueError("margin must contain nonnegative integers")
    x0, y0, x1, y1 = mask_bbox_xyxy(binary)
    corners = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float64)
    projected = corners @ affine[:, :2].T + affine[:, 2]
    before = [int(np.floor(projected[:, 0].min())) - mx,
              int(np.floor(projected[:, 1].min())) - my,
              int(np.ceil(projected[:, 0].max())) + mx,
              int(np.ceil(projected[:, 1].max())) + my]
    left, top = max(0, before[0]), max(0, before[1])
    right, bottom = min(w, before[2]), min(h, before[3])
    if right <= left or bottom <= top:
        raise ValueError("Projected ROI does not intersect input camera image")
    return {
        "mask_bbox_xyxy_exclusive": [x0, y0, x1, y1],
        "projected_mask_corners_xy": projected.tolist(),
        "camera_crop_xyxy_exclusive": [left, top, right, bottom],
        "camera_crop_wh": [right - left, bottom - top],
        "margin_camera_xy_px": [mx, my],
        "camera_crop_xyxy_before_clipping": before,
        "roi_clipped_by_image_boundary": before != [left, top, right, bottom],
    }


def process(mask_path: str | Path, camera_path: str | Path,
            calibration_path: str | Path, output_dir: str | Path,
            margin: int = 35, margin_units: str = "reference",
            resize_mode: str | None = None, threshold: int = 10) -> dict:
    if type(margin) is not int or margin < 0:
        raise ValueError("margin must be a nonnegative integer")
    if margin_units not in ("reference", "input"):
        raise ValueError("margin_units must be reference or input")
    _, binary = read_stack_mask(mask_path, threshold=threshold)
    camera = cv2.imread(str(camera_path), cv2.IMREAD_COLOR)
    if camera is None:
        raise FileNotFoundError(f"Cannot read camera image: {camera_path}")
    config = json.loads(Path(calibration_path).read_text(encoding="utf-8"))
    ref = config.get("reference_camera_wh")
    if not (isinstance(ref, list) and len(ref) == 2 and
            all(type(v) is int and v > 0 for v in ref)):
        raise ValueError("Calibration must declare reference_camera_wh [width, height]")
    input_wh = (int(camera.shape[1]), int(camera.shape[0]))
    source_affine = get_affine(calibration_path)
    affine, geometry = resolve_affine(source_affine, tuple(ref), input_wh,
                                      resize_mode or config.get("resize_mode"))
    ax, ay = geometry["reference_to_input_scale_xy"]
    mx, my = (math.ceil(margin * ax), math.ceil(margin * ay)) if margin_units == "reference" else (margin, margin)
    roi = compute_roi_multires(binary, affine, input_wh, (mx, my))
    x0, y0, x1, y1 = roi["camera_crop_xyxy_exclusive"]
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if not (cv2.imwrite(str(output / "input_camera.png"), camera)
            and cv2.imwrite(str(output / "roi_overlay.png"), make_preview(camera, binary, affine, roi))
            and cv2.imwrite(str(output / "roi_crop.png"), camera[y0:y1, x0:x1])
            and cv2.imwrite(str(output / "stack_binary.png"), binary)):
        raise RuntimeError("Failed writing ROI images")
    metadata = {
        "verification_status": "function_output_only__independent_alignment_not_verified",
        "camera_file": Path(camera_path).name, "mask_file": Path(mask_path).name,
        "mask_wh": [int(binary.shape[1]), int(binary.shape[0])],
        "mask_threshold": threshold, "calibration_file": Path(calibration_path).name,
        "mask_to_reference_camera_affine_2x3": source_affine.tolist(),
        "mask_to_input_camera_affine_2x3": affine.tolist(),
        "margin_requested_px": margin, "margin_units": margin_units,
        **geometry, **roi,
    }
    (output / "roi_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return metadata


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mask", required=True)
    p.add_argument("--camera", required=True)
    p.add_argument("--calibration", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--margin", type=int, default=35)
    p.add_argument("--margin-units", choices=("reference", "input"), default="reference")
    p.add_argument("--resize-mode", choices=MODES)
    p.add_argument("--threshold", type=int, default=10)
    a = p.parse_args()
    print(json.dumps(process(a.mask, a.camera, a.calibration, a.output_dir,
                             a.margin, a.margin_units, a.resize_mode, a.threshold),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
