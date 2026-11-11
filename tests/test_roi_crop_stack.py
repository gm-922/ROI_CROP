import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from roi_crop_stack import mask_bbox_xyxy, compute_roi


class TestRoiCrop(unittest.TestCase):
    def test_bbox_including_exclusive_edges(self):
        mask = np.zeros((12, 15), dtype=np.uint8)
        mask[2:6, 3:11] = 255
        self.assertEqual(mask_bbox_xyxy(mask), (3, 2, 11, 6))

    def test_affine_and_margin(self):
        mask = np.zeros((12, 15), dtype=np.uint8)
        mask[2:6, 3:11] = 255
        M = np.array([[2, 0, 1], [0, 3, 2]], dtype=float)
        result = compute_roi(mask, M, (50, 50, 3), margin=2)
        self.assertEqual(result['camera_crop_xyxy_exclusive'], [5, 6, 25, 22])
        self.assertEqual(result['camera_crop_wh'], [20, 16])

    def test_clipping_and_empty(self):
        mask = np.zeros((12, 15), dtype=np.uint8)
        with self.assertRaises(ValueError):
            mask_bbox_xyxy(mask)
        mask[0:2, 0:2] = 255
        M = np.array([[1, 0, 0], [0, 1, 0]], dtype=float)
        result = compute_roi(mask, M, (5, 5, 3), margin=10)
        self.assertEqual(result['camera_crop_xyxy_exclusive'], [0, 0, 5, 5])


if __name__ == '__main__':
    unittest.main()
