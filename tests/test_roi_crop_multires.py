"""Independent synthetic regression tests for the multi-resolution experiment."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from roi_crop_multires import resolve_affine, compute_roi_multires, process


class TestMultiResolutionRoi(unittest.TestCase):
    def test_coordinates_for_four_resolutions(self):
        m = np.array([[10, 0, 200], [0, 12, 100]], dtype=float)
        expected = {
            (2048, 1536): [365, 185, 635, 495],
            (1920, 1080): [342, 129, 596, 349],
            (1280, 720): [228, 86, 397, 233],
            (640, 480): [114, 57, 199, 155],
        }
        mask = np.zeros((60, 80), np.uint8)
        mask[10:30, 20:40] = 255
        for (w, h), target in expected.items():
            with self.subTest(resolution=(w, h)):
                affine, details = resolve_affine(m, (2048, 1536), (w, h), "stretch")
                mx = int(np.ceil(35 * details["reference_to_input_scale_xy"][0]))
                my = int(np.ceil(35 * details["reference_to_input_scale_xy"][1]))
                roi = compute_roi_multires(mask, affine, (w, h), (mx, my))
                self.assertEqual(roi["camera_crop_xyxy_exclusive"], target)

    def test_unknown_resize_rejected(self):
        m = np.array([[1, 0, 0], [0, 1, 0]], float)
        with self.assertRaisesRegex(ValueError, "Aspect ratio changed"):
            resolve_affine(m, (2048, 1536), (1280, 720), None)
        with self.assertRaises(ValueError):
            resolve_affine(m, (2048, 1536), (1280, 720), "unknown")

    def test_contain_and_cover(self):
        m = np.array([[1, 0, 0], [0, 1, 0]], float)
        contained, _ = resolve_affine(m, (2048, 1536), (1280, 720), "contain")
        covered, _ = resolve_affine(m, (2048, 1536), (1280, 720), "cover")
        np.testing.assert_allclose(contained, [[0.46875, 0, 160], [0, 0.46875, 0]])
        np.testing.assert_allclose(covered, [[0.625, 0, 0], [0, 0.625, -120]])

    def test_clipping_and_empty_mask(self):
        m = np.array([[1, 0, 0], [0, 1, 0]], float)
        binary = np.zeros((10, 10), np.uint8)
        with self.assertRaises(ValueError):
            compute_roi_multires(binary, m, (10, 10), (0, 0))
        binary[:2, :2] = 255
        roi = compute_roi_multires(binary, m, (10, 10), (20, 20))
        self.assertEqual(roi["camera_crop_xyxy_exclusive"], [0, 0, 10, 10])
        self.assertTrue(roi["roi_clipped_by_image_boundary"])

    def test_four_synthetic_file_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mask = np.zeros((60, 80), np.uint8)
            mask[10:30, 20:40] = 255
            self.assertTrue(cv2.imwrite(str(root / "mask.png"), mask))
            cal = {"reference_camera_wh": [2048, 1536], "resize_mode": "stretch",
                   "mask_to_camera_affine_2x3": [[10, 0, 200], [0, 12, 100]]}
            (root / "cal.json").write_text(json.dumps(cal), encoding="utf-8")
            reference = np.zeros((1536, 2048, 3), np.uint8)
            reference[220:460, 400:600, :] = (40, 220, 240)
            for w, h in ((2048, 1536), (1920, 1080), (1280, 720), (640, 480)):
                with self.subTest(resolution=(w, h)):
                    camera = cv2.resize(reference, (w, h), interpolation=cv2.INTER_NEAREST)
                    camera_path = root / f"camera_{w}x{h}.png"
                    self.assertTrue(cv2.imwrite(str(camera_path), camera))
                    out = root / f"output_{w}x{h}"
                    info = process(root / "mask.png", camera_path, root / "cal.json", out)
                    self.assertEqual(info["input_camera_wh"], [w, h])
                    cropped = cv2.imread(str(out / "roi_crop.png"))
                    self.assertEqual(list(cropped.shape[1::-1]), info["camera_crop_wh"])
                    self.assertTrue((cropped[:, :, 1] > 150).any())
                    self.assertTrue((out / "roi_overlay.png").is_file())
                    self.assertFalse(info["roi_clipped_by_image_boundary"])
                    stored = json.loads((out / "roi_metadata.json").read_text(encoding="utf-8"))
                    self.assertEqual(info["camera_crop_xyxy_exclusive"], stored["camera_crop_xyxy_exclusive"])


if __name__ == "__main__":
    unittest.main()
