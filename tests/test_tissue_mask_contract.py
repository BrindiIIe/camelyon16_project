from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tissue_mask import make_clean_tissue_mask, make_tissue_mask


class TissueMaskContractTest(unittest.TestCase):
    def test_clean_accessor_does_not_return_raw_otsu_mask(self):
        image = np.full((120, 120, 3), 255, dtype=np.uint8)
        image[40:80, 40:80] = 80
        image[82:92, 82:92] = 80

        raw_mask, cleaned_mask, _ = make_tissue_mask(image)
        selected_mask = make_clean_tissue_mask(image)

        self.assertTrue(raw_mask[86, 86])
        self.assertFalse(cleaned_mask[86, 86])
        self.assertTrue(cleaned_mask[60, 60])
        np.testing.assert_array_equal(selected_mask, cleaned_mask)


if __name__ == "__main__":
    unittest.main()
