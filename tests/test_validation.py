import math
import unittest

from api.validation import (
    check_content_type_id,
    check_coordinates,
    check_page,
    check_radius,
    check_region_pair,
    check_rows,
)


class ValidationTests(unittest.TestCase):
    def test_pagination_accepts_documented_bounds(self) -> None:
        self.assertEqual(check_rows(1), 1)
        self.assertEqual(check_rows(100), 100)
        self.assertEqual(check_page(1), 1)
        self.assertEqual(check_page(10_000), 10_000)

    def test_pagination_rejects_normalization_and_unbounded_values(self) -> None:
        for value in (0, -1, 101, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    check_rows(value)
        for value in (0, -1, 10_001, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    check_page(value)

    def test_coordinates_reject_non_finite_values(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    check_coordinates(value, 37.5)

    def test_radius_requires_integer_within_twenty_kilometres(self) -> None:
        self.assertEqual(check_radius(20_000), 20_000)
        for value in (0, 20_001, 1.5, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    check_radius(value)

    def test_district_requires_region(self) -> None:
        self.assertEqual(check_region_pair("11", "110"), ("11", "110"))
        with self.assertRaises(ValueError):
            check_region_pair(None, "110")

    def test_content_type_is_bounded_numeric_text(self) -> None:
        self.assertEqual(check_content_type_id(" 76 "), "76")
        for value in ("", "spa", "1234"):
            with self.subTest(value=value):
                if value == "":
                    self.assertIsNone(check_content_type_id(value))
                else:
                    with self.assertRaises(ValueError):
                        check_content_type_id(value)