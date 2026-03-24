"""
============================================================
  ERP APPLICATION — urls.py
============================================================
  في settings.py:
    path('api/erp/', include('erp.urls')),
============================================================

  SALES
  GET/POST     /api/erp/quotations/
  GET/PUT/PATCH/DELETE  /api/erp/quotations/<pk>/
  GET/POST     /api/erp/quotations/<pk>/items/
  GET/POST     /api/erp/sales-orders/
  GET/PUT/PATCH/DELETE  /api/erp/sales-orders/<pk>/
  GET/POST     /api/erp/sales-orders/<pk>/items/

  INVENTORY
  GET/POST     /api/erp/warehouses/
  GET/PUT/PATCH/DELETE  /api/erp/warehouses/<pk>/
  GET          /api/erp/stock/
  GET/PATCH    /api/erp/stock/<pk>/
  GET          /api/erp/stock-movements/
  GET/POST     /api/erp/stock-alerts/
  GET/PUT/PATCH/DELETE  /api/erp/stock-alerts/<pk>/

  PURCHASING
  GET/POST     /api/erp/suppliers/
  GET/PUT/PATCH/DELETE  /api/erp/suppliers/<pk>/
  GET/POST     /api/erp/purchase-orders/
  GET/PUT/PATCH/DELETE  /api/erp/purchase-orders/<pk>/
  GET/POST     /api/erp/purchase-orders/<pk>/items/
  GET/POST     /api/erp/goods-receipts/

  RETURNS
  GET/POST     /api/erp/returns/
  GET/PUT/PATCH/DELETE  /api/erp/returns/<pk>/
  GET/POST     /api/erp/returns/<pk>/items/

  FINANCE
  GET/POST     /api/erp/expense-categories/
  GET/PUT/PATCH/DELETE  /api/erp/expense-categories/<pk>/
  GET/POST     /api/erp/expenses/
  GET/PUT/PATCH/DELETE  /api/erp/expenses/<pk>/
  GET/POST     /api/erp/revenues/
  GET/PUT/PATCH/DELETE  /api/erp/revenues/<pk>/
  GET          /api/erp/financial-summaries/

  SHIPPING
  GET/POST     /api/erp/shipping-carriers/
  GET/PUT/PATCH/DELETE  /api/erp/shipping-carriers/<pk>/
  GET/POST     /api/erp/shipments/
  GET/PUT/PATCH/DELETE  /api/erp/shipments/<pk>/
  GET/POST     /api/erp/shipments/<pk>/events/

  CRM
  GET/POST     /api/erp/customer-tags/
  GET/PUT/PATCH/DELETE  /api/erp/customer-tags/<pk>/
  GET/POST     /api/erp/customers/
  GET/PUT/PATCH/DELETE  /api/erp/customers/<pk>/
  GET/POST     /api/erp/customers/<pk>/notes/
  GET/POST     /api/erp/customer-segments/
  GET/PUT/PATCH/DELETE  /api/erp/customer-segments/<pk>/

  REPORTS
  GET/POST     /api/erp/reports/
  GET/PUT/PATCH/DELETE  /api/erp/reports/<pk>/

  HR
  GET/POST     /api/erp/departments/
  GET/PUT/PATCH/DELETE  /api/erp/departments/<pk>/
  GET/POST     /api/erp/employees/
  GET/PUT/PATCH/DELETE  /api/erp/employees/<pk>/
  GET/POST     /api/erp/attendance/
  GET/PUT/PATCH/DELETE  /api/erp/attendance/<pk>/
  GET/POST     /api/erp/leave-requests/
  GET/PUT/PATCH/DELETE  /api/erp/leave-requests/<pk>/
  GET/POST     /api/erp/sales-targets/
  GET/PUT/PATCH/DELETE  /api/erp/sales-targets/<pk>/
============================================================
"""

from django.urls import path
from .views import (
    # Sales
    QuotationListCreateView, QuotationDetailView, QuotationItemListCreateView,
    SalesOrderListCreateView, SalesOrderDetailView, SalesOrderItemListCreateView,
    # Inventory
    WarehouseListCreateView, WarehouseDetailView,
    WarehouseStockListView, WarehouseStockDetailView,
    StockMovementListView,
    StockAlertListCreateView, StockAlertDetailView,
    # Purchasing
    SupplierListCreateView, SupplierDetailView,
    PurchaseOrderListCreateView, PurchaseOrderDetailView, PurchaseOrderItemListCreateView,
    GoodsReceiptListCreateView,
    # Returns
    ReturnRequestListCreateView, ReturnRequestDetailView, ReturnItemListCreateView,
    # Finance
    ExpenseCategoryListCreateView, ExpenseCategoryDetailView,
    ExpenseListCreateView, ExpenseDetailView,
    RevenueListCreateView, RevenueDetailView,
    FinancialSummaryListView,
    # Shipping
    ShippingCarrierListCreateView, ShippingCarrierDetailView,
    ShipmentRecordListCreateView, ShipmentRecordDetailView, ShipmentEventListCreateView,
    # CRM
    CustomerTagListCreateView, CustomerTagDetailView,
    CustomerProfileListCreateView, CustomerProfileDetailView, CustomerNoteListCreateView,
    CustomerSegmentListCreateView, CustomerSegmentDetailView,
    # Reports
    ReportSnapshotListCreateView, ReportSnapshotDetailView,
    # HR
    DepartmentListCreateView, DepartmentDetailView,
    EmployeeListCreateView, EmployeeDetailView,
    AttendanceListCreateView, AttendanceDetailView,
    LeaveRequestListCreateView, LeaveRequestDetailView,
    SalesTargetListCreateView, SalesTargetDetailView,
)

urlpatterns = [

    # ── SALES ──────────────────────────────────────────────
    path('quotations/',                         QuotationListCreateView.as_view()),
    path('quotations/<int:pk>/',                QuotationDetailView.as_view()),
    path('quotations/<int:quotation_pk>/items/', QuotationItemListCreateView.as_view()),

    path('sales-orders/',                       SalesOrderListCreateView.as_view()),
    path('sales-orders/<int:pk>/',              SalesOrderDetailView.as_view()),
    path('sales-orders/<int:order_pk>/items/',  SalesOrderItemListCreateView.as_view()),

    # ── INVENTORY ──────────────────────────────────────────
    path('warehouses/',                         WarehouseListCreateView.as_view()),
    path('warehouses/<int:pk>/',                WarehouseDetailView.as_view()),

    path('stock/',                              WarehouseStockListView.as_view()),
    path('stock/<int:pk>/',                     WarehouseStockDetailView.as_view()),

    path('stock-movements/',                    StockMovementListView.as_view()),

    path('stock-alerts/',                       StockAlertListCreateView.as_view()),
    path('stock-alerts/<int:pk>/',              StockAlertDetailView.as_view()),

    # ── PURCHASING ─────────────────────────────────────────
    path('suppliers/',                          SupplierListCreateView.as_view()),
    path('suppliers/<int:pk>/',                 SupplierDetailView.as_view()),

    path('purchase-orders/',                    PurchaseOrderListCreateView.as_view()),
    path('purchase-orders/<int:pk>/',           PurchaseOrderDetailView.as_view()),
    path('purchase-orders/<int:po_pk>/items/',  PurchaseOrderItemListCreateView.as_view()),

    path('goods-receipts/',                     GoodsReceiptListCreateView.as_view()),

    # ── RETURNS ────────────────────────────────────────────
    path('returns/',                            ReturnRequestListCreateView.as_view()),
    path('returns/<int:pk>/',                   ReturnRequestDetailView.as_view()),
    path('returns/<int:return_pk>/items/',      ReturnItemListCreateView.as_view()),

    # ── FINANCE ────────────────────────────────────────────
    path('expense-categories/',                 ExpenseCategoryListCreateView.as_view()),
    path('expense-categories/<int:pk>/',        ExpenseCategoryDetailView.as_view()),

    path('expenses/',                           ExpenseListCreateView.as_view()),
    path('expenses/<int:pk>/',                  ExpenseDetailView.as_view()),

    path('revenues/',                           RevenueListCreateView.as_view()),
    path('revenues/<int:pk>/',                  RevenueDetailView.as_view()),

    path('financial-summaries/',                FinancialSummaryListView.as_view()),

    # ── SHIPPING ───────────────────────────────────────────
    path('shipping-carriers/',                  ShippingCarrierListCreateView.as_view()),
    path('shipping-carriers/<int:pk>/',         ShippingCarrierDetailView.as_view()),

    path('shipments/',                          ShipmentRecordListCreateView.as_view()),
    path('shipments/<int:pk>/',                 ShipmentRecordDetailView.as_view()),
    path('shipments/<int:shipment_pk>/events/', ShipmentEventListCreateView.as_view()),

    # ── CRM ────────────────────────────────────────────────
    path('customer-tags/',                      CustomerTagListCreateView.as_view()),
    path('customer-tags/<int:pk>/',             CustomerTagDetailView.as_view()),

    path('customers/',                          CustomerProfileListCreateView.as_view()),
    path('customers/<int:pk>/',                 CustomerProfileDetailView.as_view()),
    path('customers/<int:customer_pk>/notes/',  CustomerNoteListCreateView.as_view()),

    path('customer-segments/',                  CustomerSegmentListCreateView.as_view()),
    path('customer-segments/<int:pk>/',         CustomerSegmentDetailView.as_view()),

    # ── REPORTS ────────────────────────────────────────────
    path('reports/',                            ReportSnapshotListCreateView.as_view()),
    path('reports/<int:pk>/',                   ReportSnapshotDetailView.as_view()),

    # ── HR ─────────────────────────────────────────────────
    path('departments/',                        DepartmentListCreateView.as_view()),
    path('departments/<int:pk>/',               DepartmentDetailView.as_view()),

    path('employees/',                          EmployeeListCreateView.as_view()),
    path('employees/<int:pk>/',                 EmployeeDetailView.as_view()),

    path('attendance/',                         AttendanceListCreateView.as_view()),
    path('attendance/<int:pk>/',                AttendanceDetailView.as_view()),

    path('leave-requests/',                     LeaveRequestListCreateView.as_view()),
    path('leave-requests/<int:pk>/',            LeaveRequestDetailView.as_view()),

    path('sales-targets/',                      SalesTargetListCreateView.as_view()),
    path('sales-targets/<int:pk>/',             SalesTargetDetailView.as_view()),
]