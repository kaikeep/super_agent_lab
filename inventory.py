"""商品库存管理与幂等扣减模块。

使用内存数据结构保存库存与预留记录，适用于单进程场景。对外提供：

* :meth:`InventoryManager.get_stock`：按 SKU 查询当前可用库存；
* :meth:`InventoryManager.reserve`：按 ``request_id`` 幂等地预留库存；
* :meth:`InventoryManager.release`：释放一笔预留并恢复库存。

业务规则：
1. 查询不存在的 SKU 抛出 ``ValueError``；
2. 预留数量必须为正整数；
3. 可用库存不足时抛出 ``ValueError``；
4. 相同 ``request_id`` 的重复预留不会重复扣减库存；
5. 相同 ``request_id`` 携带不同参数时抛出 ``ValueError``；
6. 同一笔预留重复释放不会重复恢复库存；
7. 释放不存在的预留 ID 抛出 ``ValueError``。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Mapping


@dataclass
class _Reservation:
    """一笔成功预留的内部记录。"""

    sku: str
    quantity: int
    released: bool = False


class InventoryManager:
    """基于内存的商品库存管理器。

    该类是线程安全的：查询、预留与释放均在同一个锁内完成，避免并发
    请求造成的超卖或重复扣减。

    Args:
        initial_stock: 初始库存映射，键为 SKU，值为非负整数库存量。
            不传时初始化为空库存。

    Raises:
        ValueError: 初始库存包含非字符串 SKU 或非法库存量时抛出。
    """

    def __init__(self, initial_stock: Mapping[str, int] | None = None) -> None:
        self._lock = threading.Lock()
        self._available: dict[str, int] = {}
        # request_id -> 预留记录，释放后仍保留，以保证重复请求的幂等性。
        self._reservations: dict[str, _Reservation] = {}

        for sku, quantity in (initial_stock or {}).items():
            if not isinstance(sku, str) or not sku:
                raise ValueError("SKU 必须是非空字符串")
            if isinstance(quantity, bool) or not isinstance(quantity, int):
                raise ValueError(f"SKU {sku!r} 的库存量必须是整数")
            if quantity < 0:
                raise ValueError(f"SKU {sku!r} 的库存量不能为负数")
            self._available[sku] = quantity

    def get_stock(self, sku: str) -> int:
        """查询 SKU 的当前可用库存。

        Args:
            sku: 商品 SKU。

        Returns:
            当前可用库存数量。

        Raises:
            ValueError: SKU 不存在时抛出。
        """
        with self._lock:
            return self._get_available(sku)

    def get_available_stock(self, sku: str) -> int:
        """``get_stock`` 的别名，语义更明确。"""
        return self.get_stock(sku)

    # 兼容不同调用方的命名习惯。
    available_stock = get_stock

    def reserve(self, sku: str, quantity: int, request_id: str) -> int:
        """预留库存；相同 ``request_id`` 的重复请求不会重复扣减。

        Args:
            sku: 商品 SKU。
            quantity: 预留数量，必须是正整数。
            request_id: 幂等键，标识一次预留请求。

        Returns:
            本次请求处理完成后该 SKU 的当前可用库存。

        Raises:
            ValueError: 数量不是正整数、SKU 不存在、库存不足，或相同
                ``request_id`` 携带了不同的 SKU/数量时抛出。
        """
        self._validate_quantity(quantity)
        self._validate_request_id(request_id)

        with self._lock:
            self._get_available(sku)

            existing = self._reservations.get(request_id)
            if existing is not None:
                if existing.sku != sku or existing.quantity != quantity:
                    raise ValueError(
                        f"request_id {request_id!r} 已用于其他预留请求"
                    )
                # 幂等重放：不重复扣减，返回当前可用库存。
                return self._available[sku]

            available = self._available[sku]
            if available < quantity:
                raise ValueError(
                    f"SKU {sku!r} 库存不足：可用 {available}，请求 {quantity}"
                )

            self._available[sku] = available - quantity
            self._reservations[request_id] = _Reservation(
                sku=sku, quantity=quantity
            )
            return self._available[sku]

    def release(self, request_id: str) -> int:
        """释放一笔预留并恢复对应库存。

        重复释放同一笔预留是幂等的，不会再次增加库存。

        Args:
            request_id: 预留时使用的幂等键。

        Returns:
            释放处理完成后该 SKU 的当前可用库存。

        Raises:
            ValueError: 预留 ID 不存在时抛出。
        """
        self._validate_request_id(request_id)

        with self._lock:
            reservation = self._reservations.get(request_id)
            if reservation is None:
                raise ValueError(f"预留 ID {request_id!r} 不存在")

            if not reservation.released:
                self._available[reservation.sku] += reservation.quantity
                reservation.released = True

            return self._available[reservation.sku]

    def _get_available(self, sku: str) -> int:
        """返回 SKU 的可用库存；调用方需持有锁。"""
        if not isinstance(sku, str) or sku not in self._available:
            raise ValueError(f"SKU {sku!r} 不存在")
        return self._available[sku]

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        """预留数量必须是正整数。"""
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("预留数量必须是正整数")
        if quantity <= 0:
            raise ValueError("预留数量必须是正整数")

    @staticmethod
    def _validate_request_id(request_id: str) -> None:
        """幂等键必须是非空字符串。"""
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id 必须是非空字符串")
