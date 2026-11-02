"""库存管理器的单元测试。"""

import threading
import unittest

from inventory import InventoryManager


class TestInventoryManager(unittest.TestCase):
    """覆盖需求文档中的用例、边界条件与异常输入。"""

    def setUp(self):
        self.manager = InventoryManager({"SKU001": 10, "SKU002": 5})

    def test_query_initial_stock(self):
        """初始库存可正确查询。"""
        self.assertEqual(self.manager.get_stock("SKU001"), 10)
        self.assertEqual(self.manager.get_stock("SKU002"), 5)
        self.assertEqual(self.manager.get_available_stock("SKU001"), 10)
        self.assertEqual(self.manager.available_stock("SKU002"), 5)

    def test_query_unknown_sku_raises(self):
        """查询不存在的 SKU 抛出 ValueError。"""
        with self.assertRaises(ValueError):
            self.manager.get_stock("SKU999")

    def test_reserve_reduces_stock(self):
        """预留成功后减少可用库存。"""
        remaining = self.manager.reserve("SKU001", 3, "req-1")
        self.assertEqual(remaining, 7)
        self.assertEqual(self.manager.get_stock("SKU001"), 7)
        # 其他 SKU 不受影响。
        self.assertEqual(self.manager.get_stock("SKU002"), 5)

    def test_reserve_same_request_is_idempotent(self):
        """相同 request_id 重复请求不会重复扣减库存。"""
        self.assertEqual(self.manager.reserve("SKU001", 3, "req-1"), 7)
        self.assertEqual(self.manager.reserve("SKU001", 3, "req-1"), 7)
        self.assertEqual(self.manager.reserve("SKU001", 3, "req-1"), 7)
        self.assertEqual(self.manager.get_stock("SKU001"), 7)

    def test_reserve_same_request_different_quantity_raises(self):
        """相同 request_id 携带不同数量时抛出 ValueError。"""
        self.manager.reserve("SKU001", 3, "req-1")
        with self.assertRaises(ValueError):
            self.manager.reserve("SKU001", 4, "req-1")
        self.assertEqual(self.manager.get_stock("SKU001"), 7)

    def test_reserve_same_request_different_sku_raises(self):
        """相同 request_id 携带不同 SKU 时抛出 ValueError。"""
        self.manager.reserve("SKU001", 3, "req-1")
        with self.assertRaises(ValueError):
            self.manager.reserve("SKU002", 3, "req-1")
        self.assertEqual(self.manager.get_stock("SKU001"), 7)
        self.assertEqual(self.manager.get_stock("SKU002"), 5)

    def test_reserve_insufficient_stock_raises(self):
        """可用库存不足时抛出 ValueError 且库存不变。"""
        with self.assertRaises(ValueError):
            self.manager.reserve("SKU001", 20, "req-1")
        self.assertEqual(self.manager.get_stock("SKU001"), 10)

    def test_reserve_exact_available_stock_succeeds(self):
        """预留数量恰好等于可用库存时成功，库存降为 0。"""
        self.assertEqual(self.manager.reserve("SKU002", 5, "req-1"), 0)
        self.assertEqual(self.manager.get_stock("SKU002"), 0)

    def test_reserve_unknown_sku_raises(self):
        """对不存在的 SKU 预留时抛出 ValueError。"""
        with self.assertRaises(ValueError):
            self.manager.reserve("SKU999", 1, "req-1")

    def test_reserve_invalid_quantity_raises(self):
        """预留数量不是正整数时抛出 ValueError。"""
        for quantity in (0, -1, 1.5, "3", None, True, False):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    self.manager.reserve("SKU001", quantity, f"req-{quantity}")
        self.assertEqual(self.manager.get_stock("SKU001"), 10)

    def test_reserve_invalid_request_id_raises(self):
        """request_id 不是非空字符串时抛出 ValueError。"""
        for request_id in ("", None, 123):
            with self.subTest(request_id=request_id):
                with self.assertRaises(ValueError):
                    self.manager.reserve("SKU001", 1, request_id)

    def test_release_restores_stock(self):
        """释放预留后恢复库存。"""
        self.manager.reserve("SKU001", 3, "req-1")
        self.assertEqual(self.manager.release("req-1"), 10)
        self.assertEqual(self.manager.get_stock("SKU001"), 10)

    def test_release_twice_does_not_double_restore(self):
        """同一笔预留重复释放不会重复增加库存。"""
        self.manager.reserve("SKU001", 3, "req-1")
        self.assertEqual(self.manager.release("req-1"), 10)
        self.assertEqual(self.manager.release("req-1"), 10)
        self.assertEqual(self.manager.get_stock("SKU001"), 10)

    def test_release_unknown_request_raises(self):
        """释放不存在的预留 ID 抛出 ValueError。"""
        with self.assertRaises(ValueError):
            self.manager.release("req-missing")

    def test_release_multiple_reservations(self):
        """多笔预留可在任意顺序下正确释放。"""
        self.manager.reserve("SKU001", 3, "req-1")
        self.manager.reserve("SKU001", 4, "req-2")
        self.assertEqual(self.manager.get_stock("SKU001"), 3)

        self.assertEqual(self.manager.release("req-1"), 6)
        self.assertEqual(self.manager.release("req-2"), 10)
        self.assertEqual(self.manager.get_stock("SKU001"), 10)

    def test_reserve_replay_after_release_does_not_deduct_again(self):
        """预留释放后，相同 request_id 的重放仍不会再次扣减库存。"""
        self.manager.reserve("SKU001", 3, "req-1")
        self.manager.release("req-1")
        self.assertEqual(self.manager.reserve("SKU001", 3, "req-1"), 10)
        self.assertEqual(self.manager.get_stock("SKU001"), 10)

    def test_failed_reserve_does_not_consume_request_id(self):
        """失败的预留不会占用 request_id，后续可用同一 ID 成功预留。"""
        with self.assertRaises(ValueError):
            self.manager.reserve("SKU001", 20, "req-1")
        self.assertEqual(self.manager.reserve("SKU001", 3, "req-1"), 7)

    def test_initial_stock_is_copied(self):
        """外部字典的后续修改不会影响管理器内部库存。"""
        source = {"SKU001": 10}
        manager = InventoryManager(source)
        source["SKU001"] = 0
        source["SKU002"] = 99
        self.assertEqual(manager.get_stock("SKU001"), 10)
        with self.assertRaises(ValueError):
            manager.get_stock("SKU002")

    def test_empty_initial_stock(self):
        """不传初始库存时为空库存。"""
        manager = InventoryManager()
        with self.assertRaises(ValueError):
            manager.get_stock("SKU001")

    def test_invalid_initial_stock_raises(self):
        """非法初始库存抛出 ValueError。"""
        for initial_stock in (
            {"SKU001": -1},
            {"SKU001": 1.5},
            {"SKU001": "10"},
            {"": 10},
            {None: 10},
        ):
            with self.subTest(initial_stock=initial_stock):
                with self.assertRaises(ValueError):
                    InventoryManager(initial_stock)

    def test_concurrent_reservations_do_not_oversell(self):
        """并发预留不会超卖，成功次数恰为可用库存数。"""
        manager = InventoryManager({"SKU001": 10})
        successes = []
        failures = []
        lock = threading.Lock()

        def worker(index):
            try:
                manager.reserve("SKU001", 1, f"req-{index}")
                with lock:
                    successes.append(index)
            except ValueError:
                with lock:
                    failures.append(index)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len(successes), 10)
        self.assertEqual(len(failures), 10)
        self.assertEqual(manager.get_stock("SKU001"), 0)


if __name__ == "__main__":
    unittest.main()
