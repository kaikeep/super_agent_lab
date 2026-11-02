"""订单运费计算模块。

业务规则：
1. 订单金额大于等于 99 元时免运费；
2. 订单金额不足 99 元时基础运费为 8 元；
3. 配送距离 3 公里以内不收取额外距离费用；
4. 超过 3 公里的部分，每增加 1 公里加收 2 元（不足 1 公里按 1 公里计算）；
5. 订单金额和配送距离不能为负数；
6. 返回运费，保留两位小数。
"""

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

#: 免运费订单金额阈值（元）。
FREE_SHIPPING_THRESHOLD = Decimal("99")
#: 不满免运费阈值时的基础运费（元）。
BASE_FEE = Decimal("8")
#: 免费配送距离（公里）。
FREE_DISTANCE_KM = Decimal("3")
#: 超出免费距离后每公里加收的费用（元）。
EXTRA_FEE_PER_KM = Decimal("2")
#: 运费保留的小数位数。
FEE_QUANTUM = Decimal("0.01")


def calculate_shipping(order_amount: float, distance_km: float) -> float:
    """计算订单运费。

    Args:
        order_amount: 订单金额（元），不能为负数。
        distance_km: 配送距离（公里），不能为负数。

    Returns:
        运费（元），保留两位小数。

    Raises:
        ValueError: 订单金额或配送距离为负数时抛出。
    """
    if order_amount < 0 or distance_km < 0:
        raise ValueError("订单金额和配送距离不能为负数")

    # 订单金额达到阈值时免运费。
    if Decimal(str(order_amount)) >= FREE_SHIPPING_THRESHOLD:
        return 0.00

    fee = BASE_FEE

    # 超出免费距离的部分按整公里向上取整计费。
    distance = Decimal(str(distance_km))
    if distance > FREE_DISTANCE_KM:
        billable_km = (distance - FREE_DISTANCE_KM).to_integral_value(
            rounding=ROUND_CEILING
        )
        fee += billable_km * EXTRA_FEE_PER_KM

    return float(fee.quantize(FEE_QUANTUM, rounding=ROUND_HALF_UP))
