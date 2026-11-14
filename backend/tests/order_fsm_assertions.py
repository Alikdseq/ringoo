"""
Общие проверки FSM v2 (migration 0012 / BLOCK 4).

Отмена клиента/системы: status=closed + closure_result=cancelled.
Legacy status='cancelled' ещё читается через Order.is_cancelled().
"""

from __future__ import annotations

from apps.orders.models import Order


def fsm_v2_create_kwargs(**kwargs):
    """
    B8-010 / Fix G: при создании тестового заказа с legacy status='cancelled'
    пишем FSM v2 closed+cancelled (не оставляем устаревшую запись статуса).

    Не трогаем STATUS_COMPLETED: в модели это алиас STATUS_CLOSED («closed»),
    отличить от голого closed без caller-side closure_result нельзя.
    """
    data = dict(kwargs)
    if data.get("status") == Order.STATUS_CANCELLED:
        data["status"] = Order.STATUS_CLOSED
        data.setdefault("closure_result", Order.CLOSURE_CANCELLED)
    return data


def assert_order_cancelled(testcase, order: Order) -> None:
    order.refresh_from_db()
    testcase.assertTrue(
        order.is_cancelled(),
        msg=f"expected cancelled, got status={order.status!r} closure_result={order.closure_result!r}",
    )
    testcase.assertEqual(order.status, Order.STATUS_CLOSED)
    testcase.assertEqual(order.closure_result, Order.CLOSURE_CANCELLED)


def assert_order_completed(testcase, order: Order) -> None:
    order.refresh_from_db()
    testcase.assertTrue(
        order.is_fulfilled(),
        msg=f"expected completed, got status={order.status!r} closure_result={order.closure_result!r}",
    )
    testcase.assertEqual(order.status, Order.STATUS_CLOSED)
    testcase.assertEqual(order.closure_result, Order.CLOSURE_COMPLETED)
    testcase.assertFalse(order.is_cancelled())


def assert_order_not_cancelled(testcase, order: Order) -> None:
    order.refresh_from_db()
    testcase.assertFalse(
        order.is_cancelled(),
        msg=f"expected not cancelled, got status={order.status!r} closure_result={order.closure_result!r}",
    )
