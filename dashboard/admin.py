from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, AdminRole, StaffProfile,
    Category, Product, ProductImage,
    Attribute, AttributeValue, ProductVariant,
    Coupon, Order, OrderItem, Payment,
    Notification, ActivityLog,ProductVideo,
)


# ============================================================
# 1. USER
# ============================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'get_full_name', 'role', 'is_blocked', 'is_active', 'created_at')
    list_filter = ('role', 'is_blocked', 'is_active')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-created_at',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('phone', 'avatar', 'role', 'is_blocked')}),
    )


# ============================================================
# 2. ADMIN ROLE & STAFF PROFILE
# ============================================================

@admin.register(AdminRole)
class AdminRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'admin_role')
    search_fields = ('user__email',)
    list_select_related = ('user', 'admin_role')


# ============================================================
# 3. CATEGORY
# ============================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


# ============================================================
# 4. PRODUCT
# ============================================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'discount_price', 'status', 'total_stock', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('name', 'sku')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVideoInline, ProductVariantInline]  # ← ضيف ProductVideoInline
# ============================================================
# 5. ATTRIBUTES & VARIANTS
# ============================================================

class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [AttributeValueInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'sku', 'stock', 'price_override', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('sku', 'product__name')


# ============================================================
# 6. COUPON
# ============================================================

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'value', 'used_count', 'max_uses', 'is_active', 'expiry_date')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)


# ============================================================
# 7. ORDER
# ============================================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'variant_name', 'unit_price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'payment_status', 'total_price', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method')
    search_fields = ('order_number', 'user__email', 'shipping_name')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    inlines = [OrderItemInline]


# ============================================================
# 8. PAYMENT
# ============================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'order', 'amount', 'method', 'status', 'created_at')
    list_filter = ('status', 'method')
    search_fields = ('transaction_id', 'order__order_number')
    readonly_fields = ('created_at',)


# ============================================================
# 9. NOTIFICATION
# ============================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')
    search_fields = ('title',)


# ============================================================
# 10. ACTIVITY LOG
# ============================================================

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'model_name', 'object_id', 'ip_address', 'created_at')
    list_filter = ('action', 'model_name')
    search_fields = ('admin__email', 'object_repr')
    readonly_fields = ('admin', 'action', 'model_name', 'object_id', 'object_repr', 'changes', 'ip_address', 'created_at')