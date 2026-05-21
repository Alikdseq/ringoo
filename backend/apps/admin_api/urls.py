"""
Admin API URL configuration.
Префикс: /api/v1/admin/
Доступ: только staff (IsStaff).
"""

from django.urls import path

from .views import content, crm, dashboard, managers, orders, products, promotions, reports, stock, stores, users

app_name = "admin_api"

urlpatterns = [
    path("dashboard/stats/", dashboard.DashboardStatsView.as_view(), name="dashboard-stats"),
    path("orders/<uuid:pk>/", orders.OrderAdminUpdateView.as_view(), name="order-update"),
    path("orders/export/", orders.OrderAdminExportView.as_view(), name="order-export"),
    path("products/", products.ProductAdminListView.as_view(), name="product-list"),
    path("products/create/", products.ProductAdminCreateView.as_view(), name="product-create"),
    path("products/<uuid:pk>/", products.ProductAdminDetailView.as_view(), name="product-detail"),
    path("products/<uuid:pk>/patch/", products.ProductAdminUpdateView.as_view(), name="product-update"),
    path(
        "products/<uuid:pk>/images/",
        products.ProductImageAdminListCreateView.as_view(),
        name="product-image-list-create",
    ),
    path(
        "products/images/<uuid:pk>/",
        products.ProductImageAdminUpdateDeleteView.as_view(),
        name="product-image-update-delete",
    ),
    path(
        "products/<uuid:pk>/specs/",
        products.ProductSpecAdminListCreateView.as_view(),
        name="product-spec-list-create",
    ),
    path(
        "products/specs/<uuid:pk>/",
        products.ProductSpecAdminUpdateDeleteView.as_view(),
        name="product-spec-update-delete",
    ),
    path(
        "products/bulk/set-active/",
        products.ProductAdminBulkSetActiveView.as_view(),
        name="product-bulk-set-active",
    ),
    path(
        "products/bulk/update-prices/",
        products.ProductAdminBulkUpdatePricesView.as_view(),
        name="product-bulk-update-prices",
    ),
    path("products/export/", products.ProductAdminExportView.as_view(), name="product-export"),
    path(
        "products/import/template/",
        products.ProductImportTemplateDownloadView.as_view(),
        name="product-import-template",
    ),
    path("products/import/", products.ProductBulkImportView.as_view(), name="product-bulk-import"),
    path("products/categories/", products.CategoryAdminListView.as_view(), name="category-list"),
    path("products/categories/create/", products.CategoryAdminCreateView.as_view(), name="category-create"),
    path("products/categories/<uuid:pk>/patch/", products.CategoryAdminUpdateView.as_view(), name="category-update"),
    path("stores/stock/", stock.StockAdminListView.as_view(), name="stock-list"),
    path("stores/stock/<uuid:pk>/", stock.StockAdminUpdateView.as_view(), name="stock-update"),
    path("stores/", stores.StoreAdminListView.as_view(), name="store-list"),
    path("stores/create/", stores.StoreAdminCreateView.as_view(), name="store-create"),
    path("stores/<uuid:pk>/patch/", stores.StoreAdminUpdateView.as_view(), name="store-update"),
    path(
        "stores/<uuid:pk>/images/",
        stores.StoreImageAdminListCreateView.as_view(),
        name="store-image-list-create",
    ),
    path(
        "stores/images/<uuid:pk>/",
        stores.StoreImageAdminUpdateDeleteView.as_view(),
        name="store-image-update-delete",
    ),
    path(
        "stores/stock/stores-summary/",
        stock.StockStoresSummaryView.as_view(),
        name="stock-stores-summary",
    ),
    path(
        "stores/stock/by-store/<uuid:store_id>/categories/",
        stock.StockByStoreCategoriesView.as_view(),
        name="stock-by-store-categories",
    ),
    path(
        "stores/stock/by-store/<uuid:store_id>/products/",
        stock.StockByStoreProductsView.as_view(),
        name="stock-by-store-products",
    ),
    path("managers/", managers.ManagerAdminListView.as_view(), name="manager-list"),
    path("managers/create/", managers.ManagerAdminCreateView.as_view(), name="manager-create"),
    path("managers/<uuid:pk>/", managers.ManagerAdminUpdateDeleteView.as_view(), name="manager-update-delete"),
    path("users/", users.UserAdminListView.as_view(), name="user-list"),
    path("users/<uuid:pk>/", users.UserAdminDetailView.as_view(), name="user-detail"),
    path("users/<uuid:pk>/patch/", users.UserAdminUpdateView.as_view(), name="user-update"),
    # Бонусы: REST админка временно скрыта (модели и apps.bonus сохранены).
    # path("bonus/accounts/", bonus.BonusAccountAdminListView.as_view(), name="bonus-account-list"),
    # path("bonus/accounts/<uuid:pk>/", bonus.BonusAccountAdminDetailView.as_view(), name="bonus-account-detail"),
    # path("bonus/accounts/<uuid:pk>/adjust/", bonus.BonusAccountAdjustView.as_view(), name="bonus-account-adjust"),
    path("content/tags/", content.TagAdminListView.as_view(), name="tag-list"),
    path("content/articles/", content.ArticleAdminListView.as_view(), name="article-list"),
    path("content/articles/create/", content.ArticleAdminCreateView.as_view(), name="article-create"),
    path(
        "content/articles/<uuid:pk>/",
        content.ArticleAdminUpdateDeleteView.as_view(),
        name="article-update-delete",
    ),
    path("content/news/", content.NewsAdminListView.as_view(), name="news-list"),
    path("content/news/create/", content.NewsAdminCreateView.as_view(), name="news-create"),
    path(
        "content/news/<uuid:pk>/",
        content.NewsAdminUpdateDeleteView.as_view(),
        name="news-update-delete",
    ),
    path("content/reviews/", content.ReviewAdminListView.as_view(), name="review-list"),
    path("content/reviews/<uuid:pk>/patch/", content.ReviewAdminUpdateView.as_view(), name="review-update"),
    path(
        "content/page-gallery/",
        content.PageGalleryAdminListView.as_view(),
        name="page-gallery-list",
    ),
    path(
        "content/page-gallery/create/",
        content.PageGalleryAdminCreateView.as_view(),
        name="page-gallery-create",
    ),
    path(
        "content/page-gallery/<uuid:pk>/",
        content.PageGalleryAdminUpdateDeleteView.as_view(),
        name="page-gallery-update-delete",
    ),
    path("promotions/", promotions.PromotionAdminListView.as_view(), name="promotion-list"),
    path("promotions/create/", promotions.PromotionAdminCreateView.as_view(), name="promotion-create"),
    path("promotions/<uuid:pk>/", promotions.PromotionAdminUpdateDeleteView.as_view(), name="promotion-update-delete"),
    path("promocodes/", promotions.PromoCodeAdminListView.as_view(), name="promocode-list"),
    path("promocodes/create/", promotions.PromoCodeAdminCreateView.as_view(), name="promocode-create"),
    path("promocodes/<uuid:pk>/", promotions.PromoCodeAdminUpdateDeleteView.as_view(), name="promocode-update-delete"),
    path("crm/requests/", crm.MissingProductRequestAdminListView.as_view(), name="crm-request-list"),
    path("crm/requests/<uuid:pk>/", crm.MissingProductRequestAdminDetailView.as_view(), name="crm-request-detail"),
    path("crm/requests/<uuid:pk>/patch/", crm.MissingProductRequestAdminUpdateView.as_view(), name="crm-request-update"),
    path("reports/revenue/", reports.RevenueReportView.as_view(), name="report-revenue"),
    path("reports/orders/", reports.OrdersReportView.as_view(), name="report-orders"),
    path("reports/top-products/", reports.TopProductsReportView.as_view(), name="report-top-products"),
]
