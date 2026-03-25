"""
============================================================
  ERP APPLICATION — views.py
  Class-Based Views | JWT Auth | Staff/Admin Only
============================================================
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    Quotation, QuotationItem, SalesOrder, SalesOrderItem,
    Warehouse, WarehouseStock, StockMovement, StockAlert,
    Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceipt,
    ReturnRequest, ReturnItem,
    ExpenseCategory, Expense, Revenue, FinancialSummary,
    ShippingCarrier, ShipmentRecord, ShipmentEvent,
    CustomerTag, CustomerProfile, CustomerNote, CustomerSegment,
    ReportSnapshot,
    Department, Employee, Attendance, LeaveRequest, SalesTarget,
)
from .serializers import (
    QuotationSerializer, QuotationWriteSerializer, QuotationItemSerializer,
    SalesOrderSerializer, SalesOrderWriteSerializer, SalesOrderItemSerializer,
    WarehouseSerializer, WarehouseStockSerializer, StockMovementSerializer, StockAlertSerializer,
    SupplierSerializer, PurchaseOrderSerializer, PurchaseOrderWriteSerializer,
    PurchaseOrderItemSerializer, GoodsReceiptSerializer,
    ReturnRequestSerializer, ReturnRequestWriteSerializer, ReturnItemSerializer,
    ExpenseCategorySerializer, ExpenseSerializer, RevenueSerializer, FinancialSummarySerializer,
    ShippingCarrierSerializer, ShipmentRecordSerializer, ShipmentRecordWriteSerializer, ShipmentEventSerializer,
    CustomerTagSerializer, CustomerProfileSerializer, CustomerProfileWriteSerializer,
    CustomerNoteSerializer, CustomerSegmentSerializer,
    ReportSnapshotSerializer,
    DepartmentSerializer, EmployeeSerializer, EmployeeWriteSerializer,
    AttendanceSerializer, LeaveRequestSerializer, SalesTargetSerializer,
)


# ─────────────────────────────────────────────
#  Permission: Staff or Admin only
# ─────────────────────────────────────────────
class IsStaffOrAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.role in ('admin', 'staff')
        )


# ─────────────────────────────────────────────
#  Base Mixin للـ List + Create
# ─────────────────────────────────────────────
class ListCreateMixin:
    permission_classes = [IsStaffOrAdmin]
    read_serializer  = None
    write_serializer = None
    queryset_model   = None

    def get_queryset(self):
        return self.queryset_model.objects.all()

    def get(self, request):
        qs = self.get_queryset()
        serializer = self.read_serializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        ser_class = self.write_serializer or self.read_serializer
        serializer = ser_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────
#  Base Mixin للـ Retrieve + Update + Delete
# ─────────────────────────────────────────────
class RetrieveUpdateDestroyMixin:
    permission_classes = [IsStaffOrAdmin]
    read_serializer  = None
    write_serializer = None
    queryset_model   = None

    def get_object(self, pk):
        return get_object_or_404(self.queryset_model, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        serializer = self.read_serializer(obj)
        return Response(serializer.data)

    def put(self, request, pk):
        obj = self.get_object(pk)
        ser_class = self.write_serializer or self.read_serializer
        serializer = ser_class(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        ser_class = self.write_serializer or self.read_serializer
        serializer = ser_class(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
#  MODULE 1 — SALES
# ============================================================

class QuotationListCreateView(ListCreateMixin, APIView):
    read_serializer  = QuotationSerializer
    write_serializer = QuotationWriteSerializer
    queryset_model   = Quotation

    def get_queryset(self):
        qs = Quotation.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class QuotationDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer  = QuotationSerializer
    write_serializer = QuotationWriteSerializer
    queryset_model   = Quotation


class QuotationItemListCreateView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request, quotation_pk):
        items = QuotationItem.objects.filter(quotation_id=quotation_pk)
        serializer = QuotationItemSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, quotation_pk):
        get_object_or_404(Quotation, pk=quotation_pk)
        serializer = QuotationItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(quotation_id=quotation_pk)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SalesOrderListCreateView(ListCreateMixin, APIView):
    read_serializer  = SalesOrderSerializer
    write_serializer = SalesOrderWriteSerializer
    queryset_model   = SalesOrder

    def get_queryset(self):
        qs = SalesOrder.objects.all()
        params = self.request.query_params
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('source'):
            qs = qs.filter(source=params['source'])
        if params.get('payment_status'):
            qs = qs.filter(payment_status=params['payment_status'])
        if params.get('customer'):
            qs = qs.filter(customer_id=params['customer'])
        return qs


class SalesOrderDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer  = SalesOrderSerializer
    write_serializer = SalesOrderWriteSerializer
    queryset_model   = SalesOrder


class SalesOrderItemListCreateView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request, order_pk):
        items = SalesOrderItem.objects.filter(sales_order_id=order_pk)
        serializer = SalesOrderItemSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, order_pk):
        order = get_object_or_404(SalesOrder, pk=order_pk)
        serializer = SalesOrderItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(sales_order_id=order_pk)
            order.calculate_totals()  # ← السطر ده بس اللي اتضاف
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
#  MODULE 2 — INVENTORY
# ============================================================

class WarehouseListCreateView(ListCreateMixin, APIView):
    read_serializer = WarehouseSerializer
    queryset_model  = Warehouse


class WarehouseDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = WarehouseSerializer
    queryset_model  = Warehouse


class WarehouseStockListView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request):
        qs = WarehouseStock.objects.select_related('warehouse', 'variant').all()
        warehouse = request.query_params.get('warehouse')
        if warehouse:
            qs = qs.filter(warehouse_id=warehouse)
        serializer = WarehouseStockSerializer(qs, many=True)
        return Response(serializer.data)


class WarehouseStockDetailView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request, pk):
        obj = get_object_or_404(WarehouseStock, pk=pk)
        return Response(WarehouseStockSerializer(obj).data)

    def patch(self, request, pk):
        """تعديل يدوي للمخزون — بيسجل StockMovement تلقائياً."""
        obj = get_object_or_404(WarehouseStock, pk=pk)
        new_quantity = request.data.get('quantity')
        reason       = request.data.get('reason', 'Manual Adjustment')

        if new_quantity is None:
            return Response({'error': 'quantity is required'}, status=status.HTTP_400_BAD_REQUEST)

        new_quantity = int(new_quantity)
        stock_before = obj.quantity
        obj.quantity = new_quantity
        obj.save()

        StockMovement.objects.create(
            variant=obj.variant,
            warehouse=obj.warehouse,
            type=StockMovement.Type.ADJUST,
            quantity=new_quantity - stock_before,
            stock_before=stock_before,
            stock_after=new_quantity,
            reason=reason,
            created_by=request.user,
        )

        return Response(WarehouseStockSerializer(obj).data)


class StockMovementListView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request):
        qs = StockMovement.objects.all()
        params = self.request.query_params
        if params.get('variant'):
            qs = qs.filter(variant_id=params['variant'])
        if params.get('warehouse'):
            qs = qs.filter(warehouse_id=params['warehouse'])
        if params.get('type'):
            qs = qs.filter(type=params['type'])
        serializer = StockMovementSerializer(qs, many=True)
        return Response(serializer.data)


class StockAlertListCreateView(ListCreateMixin, APIView):
    read_serializer = StockAlertSerializer
    queryset_model  = StockAlert


class StockAlertDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = StockAlertSerializer
    queryset_model  = StockAlert


# ============================================================
#  MODULE 3 — PURCHASING
# ============================================================

class SupplierListCreateView(ListCreateMixin, APIView):
    read_serializer = SupplierSerializer
    queryset_model  = Supplier

    def get_queryset(self):
        qs = Supplier.objects.all()
        if self.request.query_params.get('active'):
            qs = qs.filter(is_active=True)
        return qs


class SupplierDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = SupplierSerializer
    queryset_model  = Supplier


class PurchaseOrderListCreateView(ListCreateMixin, APIView):
    read_serializer  = PurchaseOrderSerializer
    write_serializer = PurchaseOrderWriteSerializer
    queryset_model   = PurchaseOrder

    def get_queryset(self):
        qs = PurchaseOrder.objects.all()
        if self.request.query_params.get('status'):
            qs = qs.filter(status=self.request.query_params['status'])
        if self.request.query_params.get('supplier'):
            qs = qs.filter(supplier_id=self.request.query_params['supplier'])
        return qs


class PurchaseOrderDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer  = PurchaseOrderSerializer
    write_serializer = PurchaseOrderWriteSerializer
    queryset_model   = PurchaseOrder


class PurchaseOrderItemListCreateView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request, po_pk):
        items = PurchaseOrderItem.objects.filter(purchase_order_id=po_pk)
        serializer = PurchaseOrderItemSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, po_pk):
        get_object_or_404(PurchaseOrder, pk=po_pk)
        serializer = PurchaseOrderItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(purchase_order_id=po_pk)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoodsReceiptListCreateView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request):
        qs = GoodsReceipt.objects.all()
        if request.query_params.get('purchase_order'):
            qs = qs.filter(purchase_order_id=request.query_params['purchase_order'])
        serializer = GoodsReceiptSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = GoodsReceiptSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(received_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
#  MODULE 4 — RETURNS
# ============================================================

class ReturnRequestListCreateView(ListCreateMixin, APIView):
    read_serializer  = ReturnRequestSerializer
    write_serializer = ReturnRequestWriteSerializer
    queryset_model   = ReturnRequest

    def get_queryset(self):
        qs = ReturnRequest.objects.all()
        if self.request.query_params.get('status'):
            qs = qs.filter(status=self.request.query_params['status'])
        return qs


class ReturnRequestDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer  = ReturnRequestSerializer
    write_serializer = ReturnRequestWriteSerializer
    queryset_model   = ReturnRequest


class ReturnItemListCreateView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request, return_pk):
        items = ReturnItem.objects.filter(return_request_id=return_pk)
        serializer = ReturnItemSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, return_pk):
        get_object_or_404(ReturnRequest, pk=return_pk)
        serializer = ReturnItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(return_request_id=return_pk)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
#  MODULE 5 — FINANCE
# ============================================================

class ExpenseCategoryListCreateView(ListCreateMixin, APIView):
    read_serializer = ExpenseCategorySerializer
    queryset_model  = ExpenseCategory


class ExpenseCategoryDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = ExpenseCategorySerializer
    queryset_model  = ExpenseCategory


class ExpenseListCreateView(ListCreateMixin, APIView):
    read_serializer = ExpenseSerializer
    queryset_model  = Expense
    parser_classes  = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = Expense.objects.all()
        params = self.request.query_params
        if params.get('category'):
            qs = qs.filter(category_id=params['category'])
        if params.get('from'):
            qs = qs.filter(date__gte=params['from'])
        if params.get('to'):
            qs = qs.filter(date__lte=params['to'])
        return qs

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExpenseDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = ExpenseSerializer
    queryset_model  = Expense


class RevenueListCreateView(ListCreateMixin, APIView):
    read_serializer = RevenueSerializer
    queryset_model  = Revenue

    def get_queryset(self):
        qs = Revenue.objects.all()
        params = self.request.query_params
        if params.get('from'):
            qs = qs.filter(date__gte=params['from'])
        if params.get('to'):
            qs = qs.filter(date__lte=params['to'])
        if params.get('source'):
            qs = qs.filter(source=params['source'])
        return qs


class RevenueDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = RevenueSerializer
    queryset_model  = Revenue


class FinancialSummaryListView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request):
        qs = FinancialSummary.objects.all()
        if request.query_params.get('from'):
            qs = qs.filter(date__gte=request.query_params['from'])
        if request.query_params.get('to'):
            qs = qs.filter(date__lte=request.query_params['to'])
        serializer = FinancialSummarySerializer(qs, many=True)
        return Response(serializer.data)


# ============================================================
#  MODULE 6 — SHIPPING
# ============================================================

class ShippingCarrierListCreateView(ListCreateMixin, APIView):
    read_serializer = ShippingCarrierSerializer
    queryset_model  = ShippingCarrier


class ShippingCarrierDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = ShippingCarrierSerializer
    queryset_model  = ShippingCarrier


class ShipmentRecordListCreateView(ListCreateMixin, APIView):
    read_serializer  = ShipmentRecordSerializer
    write_serializer = ShipmentRecordWriteSerializer
    queryset_model   = ShipmentRecord

    def get_queryset(self):
        qs = ShipmentRecord.objects.all()
        if self.request.query_params.get('status'):
            qs = qs.filter(status=self.request.query_params['status'])
        if self.request.query_params.get('carrier'):
            qs = qs.filter(carrier_id=self.request.query_params['carrier'])
        return qs


class ShipmentRecordDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer  = ShipmentRecordSerializer
    write_serializer = ShipmentRecordWriteSerializer
    queryset_model   = ShipmentRecord


class ShipmentEventListCreateView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request, shipment_pk):
        events = ShipmentEvent.objects.filter(shipment_id=shipment_pk)
        serializer = ShipmentEventSerializer(events, many=True)
        return Response(serializer.data)

    def post(self, request, shipment_pk):
        get_object_or_404(ShipmentRecord, pk=shipment_pk)
        serializer = ShipmentEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(shipment_id=shipment_pk)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
#  MODULE 7 — CRM
# ============================================================

class CustomerTagListCreateView(ListCreateMixin, APIView):
    read_serializer = CustomerTagSerializer
    queryset_model  = CustomerTag


class CustomerTagDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = CustomerTagSerializer
    queryset_model  = CustomerTag


class CustomerProfileListCreateView(ListCreateMixin, APIView):
    read_serializer  = CustomerProfileSerializer
    write_serializer = CustomerProfileWriteSerializer
    queryset_model   = CustomerProfile

    def get_queryset(self):
        qs = CustomerProfile.objects.all()
        params = self.request.query_params
        if params.get('source'):
            qs = qs.filter(source=params['source'])
        if params.get('blocked'):
            qs = qs.filter(is_blocked=params['blocked'] == 'true')
        if params.get('search'):
            qs = qs.filter(name__icontains=params['search'])
        return qs


class CustomerProfileDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer  = CustomerProfileSerializer
    write_serializer = CustomerProfileWriteSerializer
    queryset_model   = CustomerProfile


class CustomerNoteListCreateView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request, customer_pk):
        notes = CustomerNote.objects.filter(customer_id=customer_pk)
        serializer = CustomerNoteSerializer(notes, many=True)
        return Response(serializer.data)

    def post(self, request, customer_pk):
        get_object_or_404(CustomerProfile, pk=customer_pk)
        serializer = CustomerNoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(customer_id=customer_pk, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerSegmentListCreateView(ListCreateMixin, APIView):
    read_serializer = CustomerSegmentSerializer
    queryset_model  = CustomerSegment


class CustomerSegmentDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = CustomerSegmentSerializer
    queryset_model  = CustomerSegment


# ============================================================
#  MODULE 8 — REPORTS
# ============================================================

class ReportSnapshotListCreateView(ListCreateMixin, APIView):
    read_serializer = ReportSnapshotSerializer
    queryset_model  = ReportSnapshot

    def get_queryset(self):
        qs = ReportSnapshot.objects.all()
        if self.request.query_params.get('type'):
            qs = qs.filter(report_type=self.request.query_params['type'])
        return qs

    def post(self, request):
        serializer = ReportSnapshotSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(generated_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReportSnapshotDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = ReportSnapshotSerializer
    queryset_model  = ReportSnapshot


# ============================================================
#  MODULE 9 — HR
# ============================================================

class DepartmentListCreateView(ListCreateMixin, APIView):
    read_serializer = DepartmentSerializer
    queryset_model  = Department


class DepartmentDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = DepartmentSerializer
    queryset_model  = Department


class EmployeeListCreateView(ListCreateMixin, APIView):
    read_serializer  = EmployeeSerializer
    write_serializer = EmployeeWriteSerializer
    queryset_model   = Employee

    def get_queryset(self):
        qs = Employee.objects.all()
        params = self.request.query_params
        if params.get('department'):
            qs = qs.filter(department_id=params['department'])
        if params.get('active'):
            qs = qs.filter(is_active=params['active'] == 'true')
        return qs


class EmployeeDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer  = EmployeeSerializer
    write_serializer = EmployeeWriteSerializer
    queryset_model   = Employee


class AttendanceListCreateView(ListCreateMixin, APIView):
    read_serializer = AttendanceSerializer
    queryset_model  = Attendance

    def get_queryset(self):
        qs = Attendance.objects.all()
        params = self.request.query_params
        if params.get('employee'):
            qs = qs.filter(employee_id=params['employee'])
        if params.get('date'):
            qs = qs.filter(date=params['date'])
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        return qs


class AttendanceDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = AttendanceSerializer
    queryset_model  = Attendance


class LeaveRequestListCreateView(ListCreateMixin, APIView):
    read_serializer = LeaveRequestSerializer
    queryset_model  = LeaveRequest

    def get_queryset(self):
        qs = LeaveRequest.objects.all()
        params = self.request.query_params
        if params.get('employee'):
            qs = qs.filter(employee_id=params['employee'])
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        return qs


class LeaveRequestDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = LeaveRequestSerializer
    queryset_model  = LeaveRequest


class SalesTargetListCreateView(ListCreateMixin, APIView):
    read_serializer = SalesTargetSerializer
    queryset_model  = SalesTarget

    def get_queryset(self):
        qs = SalesTarget.objects.all()
        if self.request.query_params.get('employee'):
            qs = qs.filter(employee_id=self.request.query_params['employee'])
        return qs


class SalesTargetDetailView(RetrieveUpdateDestroyMixin, APIView):
    read_serializer = SalesTargetSerializer
    queryset_model  = SalesTarget