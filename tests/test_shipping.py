"""订单运费计算的单元测试。"""

import unittest

from shipping import calculate_shipping


class TestCalculateShipping(unittest.TestCase):
    """覆盖需求文档中的用例、边界条件与异常输入。"""

    def test_free_shipping_over_threshold(self):
        """订单金额达到 99 元时免运费。"""
        self.assertEqual(calculate_shipping(120, 5), 0.00)
        self.assertEqual(calculate_shipping(99, 10), 0.00)

    def test_short_distance_uses_base_fee(self):
        """金额不足 99 元、距离在 3 公里以内时只收基础运费。"""
        self.assertEqual(calculate_shipping(50, 2), 8.00)
        self.assertEqual(calculate_shipping(50, 3), 8.00)

    def test_extra_distance_fee_exact_km(self):
        """超出 3 公里的整公里部分每公里加收 2 元。"""
        self.assertEqual(calculate_shipping(50, 4), 10.00)
        self.assertEqual(calculate_shipping(50, 10), 22.00)

    def test_extra_distance_fee_rounds_up(self):
        """不足 1 公里按 1 公里计算。"""
        self.assertEqual(calculate_shipping(50, 4.5), 12.00)
        self.assertEqual(calculate_shipping(50, 3.01), 10.00)
        self.assertEqual(calculate_shipping(50, 3.1), 10.00)

    def test_boundary_values(self):
        """覆盖阈值、零值与上下边界。"""
        self.assertEqual(calculate_shipping(0, 0), 8.00)
        self.assertEqual(calculate_shipping(98.99, 3), 8.00)
        self.assertEqual(calculate_shipping(98.99, 3.01), 10.00)
        self.assertEqual(calculate_shipping(99, 0), 0.00)
        self.assertEqual(calculate_shipping(100, 100), 0.00)

    def test_negative_amount_raises(self):
        """订单金额为负数时抛出 ValueError。"""
        with self.assertRaises(ValueError):
            calculate_shipping(-10, 2)

    def test_negative_distance_raises(self):
        """配送距离为负数时抛出 ValueError。"""
        with self.assertRaises(ValueError):
            calculate_shipping(50, -1)
        with self.assertRaises(ValueError):
            calculate_shipping(120, -1)

    def test_result_is_float_with_two_decimals(self):
        """返回值为保留两位小数的浮点数。"""
        result = calculate_shipping(50, 2)
        self.assertIsInstance(result, float)
        self.assertEqual(result, round(result, 2))


if __name__ == "__main__":
    unittest.main()
