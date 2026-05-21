"""Admin API: Дашборд — агрегированная аналитика."""

from decimal import Decimal

from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order, OrderItem

from ..permissions import admin_permissions_dashboard


class DashboardStatsView(APIView):
    """
    GET /api/v1/admin/dashboard/stats/ — статистика для дашборда.
    Доступ: staff.
    """

    permission_classes = admin_permissions_dashboard()

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timezone.timedelta(days=7)
        month_start = now - timezone.timedelta(days=30)

        completed = Order.objects.exclude(status=Order.STATUS_CANCELLED)

        orders_today = completed.filter(created_at__gte=today_start).count()
        orders_week = completed.filter(created_at__gte=week_start).count()
        orders_month = completed.filter(created_at__gte=month_start).count()

        rev_week = completed.filter(created_at__gte=week_start).aggregate(
            s=Sum("total_amount")
        )["s"] or Decimal("0")
        rev_month = completed.filter(created_at__gte=month_start).aggregate(
            s=Sum("total_amount")
        )["s"] or Decimal("0")

        avg_week = completed.filter(created_at__gte=week_start).aggregate(
            a=Avg("total_amount")
        )["a"]
        avg_month = completed.filter(created_at__gte=month_start).aggregate(
            a=Avg("total_amount")
        )["a"]

        top_n = min(int(request.query_params.get("top_n", 5) or 5), 20)
        top_items = (
            OrderItem.objects.filter(
                order__created_at__gte=month_start,
                order__status__in=[
                    Order.STATUS_CONFIRMED,
                    Order.STATUS_IN_PROGRESS,
                    Order.STATUS_COMPLETED,
                ],
            )
            .values("product_title", "product_sku")
            .annotate(total_qty=Sum("quantity"))
            .order_by("-total_qty")[:top_n]
        )
        top_products = [
            {
                "product_title": x["product_title"],
                "product_sku": x["product_sku"] or "",
                "quantity_sold": x["total_qty"],
            }
            for x in top_items
        ]

        return Response({
            "orders_today": orders_today,
            "orders_week": orders_week,
            "orders_month": orders_month,
            "revenue_week": str(rev_week),
            "revenue_month": str(rev_month),
            "avg_check_week": round(float(avg_week or 0), 2),
            "avg_check_month": round(float(avg_month or 0), 2),
            "top_products": top_products,
        })
