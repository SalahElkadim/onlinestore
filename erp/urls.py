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
    FinancialSummaryListView,RevenueBulkDeleteView,
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
    path('revenues/bulk-delete/', RevenueBulkDeleteView.as_view()),
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