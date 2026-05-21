"""Admin API: Отчёты — выручка, заказы, топ товаров.

Все представления здесь используют агрегаты ORM (без обхода заказов в Python),
поэтому классический N+1 на уровне списков не характерен. Для новых отчётов и
тяжёлых list-view см. docs/ADMIN_API_PERFORMANCE.md.
"""

from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order, OrderItem

from ..permissions import RINGOO_GROUP_REPORTS, admin_permissions


class RevenueReportView(APIView):
  """
  GET /api/v1/admin/reports/revenue/ — выручка за период.

  Параметры:
  - date_from, date_to (YYYY-MM-DD, опционально; по умолчанию последние 30 дней)

  Группировка по дням.
  """

  permission_classes = admin_permissions(RINGOO_GROUP_REPORTS)

  def get(self, request):
    date_from_str = (request.query_params.get("date_from") or "").strip()
    date_to_str = (request.query_params.get("date_to") or "").strip()

    today = timezone.now().date()
    if date_to_str:
      try:
        date_to = timezone.datetime.fromisoformat(date_to_str).date()
      except ValueError:
        date_to = today
    else:
      date_to = today

    if date_from_str:
      try:
        date_from = timezone.datetime.fromisoformat(date_from_str).date()
      except ValueError:
        date_from = date_to - timezone.timedelta(days=30)
    else:
      date_from = date_to - timezone.timedelta(days=30)

    valid_statuses = [
      Order.STATUS_CONFIRMED,
      Order.STATUS_IN_PROGRESS,
      Order.STATUS_COMPLETED,
    ]

    qs = (
      Order.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        status__in=valid_statuses,
      )
      .annotate(period=TruncDate("created_at"))
      .values("period")
      .annotate(
        total_revenue=Sum("total_amount"),
        orders_count=Count("id"),
      )
      .order_by("period")
    )

    data = [
      {
        "date": row["period"].isoformat(),
        "total_revenue": str(row["total_revenue"] or Decimal("0")),
        "orders_count": row["orders_count"],
      }
      for row in qs
    ]

    return Response(
      {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "rows": data,
      }
    )


class OrdersReportView(APIView):
  """
  GET /api/v1/admin/reports/orders/ — агрегированный отчёт по заказам.

  Параметры:
  - date_from, date_to (YYYY-MM-DD, опционально; по умолчанию последние 30 дней)
  """

  permission_classes = admin_permissions(RINGOO_GROUP_REPORTS)

  def get(self, request):
    date_from_str = (request.query_params.get("date_from") or "").strip()
    date_to_str = (request.query_params.get("date_to") or "").strip()

    today = timezone.now().date()
    if date_to_str:
      try:
        date_to = timezone.datetime.fromisoformat(date_to_str).date()
      except ValueError:
        date_to = today
    else:
      date_to = today

    if date_from_str:
      try:
        date_from = timezone.datetime.fromisoformat(date_from_str).date()
      except ValueError:
        date_from = date_to - timezone.timedelta(days=30)
    else:
      date_from = date_to - timezone.timedelta(days=30)

    qs = Order.objects.filter(
      created_at__date__gte=date_from,
      created_at__date__lte=date_to,
    )

    by_status = (
      qs.values("status")
      .annotate(count=Count("id"))
      .order_by("status")
    )
    by_payment = (
      qs.values("payment_type")
      .annotate(count=Count("id"))
      .order_by("payment_type")
    )
    by_delivery = (
      qs.values("delivery_type")
      .annotate(count=Count("id"))
      .order_by("delivery_type")
    )

    return Response(
      {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "by_status": list(by_status),
        "by_payment_type": list(by_payment),
        "by_delivery_type": list(by_delivery),
      }
    )


class TopProductsReportView(APIView):
  """
  GET /api/v1/admin/reports/top-products/ — топ товаров за период.

  Параметры:
  - date_from, date_to (YYYY-MM-DD, опционально; по умолчанию последние 30 дней)
  - limit (int, по умолчанию 10)
  """

  permission_classes = admin_permissions(RINGOO_GROUP_REPORTS)

  def get(self, request):
    date_from_str = (request.query_params.get("date_from") or "").strip()
    date_to_str = (request.query_params.get("date_to") or "").strip()
    limit_str = (request.query_params.get("limit") or "").strip()

    today = timezone.now().date()
    if date_to_str:
      try:
        date_to = timezone.datetime.fromisoformat(date_to_str).date()
      except ValueError:
        date_to = today
    else:
      date_to = today

    if date_from_str:
      try:
        date_from = timezone.datetime.fromisoformat(date_from_str).date()
      except ValueError:
        date_from = date_to - timezone.timedelta(days=30)
    else:
      date_from = date_to - timezone.timedelta(days=30)

    try:
      limit = int(limit_str) if limit_str else 10
    except ValueError:
      limit = 10
    limit = max(1, min(limit, 100))

    valid_statuses = [
      Order.STATUS_CONFIRMED,
      Order.STATUS_IN_PROGRESS,
      Order.STATUS_COMPLETED,
    ]

    qs = (
      OrderItem.objects.filter(
        order__created_at__date__gte=date_from,
        order__created_at__date__lte=date_to,
        order__status__in=valid_statuses,
      )
      .values("product_title", "product_sku")
      .annotate(
        quantity_sold=Sum("quantity"),
        revenue=Sum("item_total"),
      )
      .order_by("-quantity_sold")[:limit]
    )

    data = [
      {
        "product_title": row["product_title"],
        "product_sku": row["product_sku"] or "",
        "quantity_sold": row["quantity_sold"] or 0,
        "revenue": str(row["revenue"] or Decimal("0")),
      }
      for row in qs
    ]

    return Response(
      {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "rows": data,
      }
    )

