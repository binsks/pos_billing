from decimal import Decimal
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Count, F
from django.shortcuts import get_object_or_404, redirect, render
from .models import Product, Category
from .models import (
    Category,
    Customer,
    Product,
    Supplier,
    Sale,
    SaleItem,
    Return,
    ReturnItem,
    Ledger,
    StaffProfile,
    Purchase,
    PurchaseItem,
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or
        getattr(user, "staffprofile", None) and
        user.staffprofile.role == "admin"
    )


def is_staff_member(user):
    return user.is_authenticated and (
        user.is_superuser or
        (
            hasattr(user, "staffprofile")
            and user.staffprofile.role in ["admin", "staff"]
        )
    )


# =========================================================
# AUTHENTICATION
# =========================================================

def login_view(request):

    if request.user.is_authenticated:
        if is_admin(request.user):
            return redirect("admin_dashboard")
        return redirect("billing")

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            if hasattr(user, "staffprofile"):
                if not user.staffprofile.is_active:
                    messages.error(
                        request,
                        "Your staff account is inactive."
                    )
                    return redirect("login")

            login(request, user)

            if is_admin(user):
                return redirect("admin_dashboard")

            return redirect("billing")

        messages.error(
            request,
            "Invalid username or password."
        )

    return render(request, "accounts/login.html")


@login_required
def logout_view(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect("login")


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):

    total_products = Product.objects.filter(
        is_active=True
    ).count()

    total_staff = StaffProfile.objects.filter(
        role="staff"
    ).count()

    total_suppliers = Supplier.objects.count()

    total_customers = Customer.objects.count()

    total_sales = Sale.objects.count()

    today_sales = Sale.objects.filter(
        created_at__date=__import__("datetime").date.today()
    ).aggregate(
        total=Sum("total")
    )["total"] or Decimal("0.00")

    low_stock_products = Product.objects.filter(
        stock__lte=5,
        is_active=True
    ).order_by("stock")

    recent_sales = Sale.objects.select_related(
        "staff",
        "customer"
    ).order_by("-id")[:10]

    context = {
        "total_products": total_products,
        "total_staff": total_staff,
        "total_suppliers": total_suppliers,
        "total_customers": total_customers,
        "total_sales": total_sales,
        "today_sales": today_sales,
        "low_stock_products": low_stock_products,
        "recent_sales": recent_sales,
    }

    return render(
        request,
        "admin_portal/dashboard.html",
        context
    )


# =========================================================
# PRODUCT MANAGEMENT
# =========================================================

@login_required
@user_passes_test(is_admin)

def product_list(request):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    products = Product.objects.select_related(
        "category"
    ).order_by("-id")

    search = request.GET.get("search", "").strip()
    category_id = request.GET.get("category", "").strip()
    stock_filter = request.GET.get("stock", "").strip()

    # Search
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(category__name__icontains=search)
        )

    # Category filter
    if category_id:
        products = products.filter(
            category_id=category_id
        )

    # Stock filter
    if stock_filter == "low":
        products = products.filter(
            stock__gt=0,
            stock__lte=5
        )

    elif stock_filter == "out":
        products = products.filter(
            stock=0
        )

    categories = Category.objects.order_by("name")

    context = {
        "products": products,
        "categories": categories,
        "search": search,
        "selected_category": category_id,
        "stock_filter": stock_filter,
    }

    return render(
        request,
        "admin_portal/products.html",
        context
    )


@login_required
def add_product(request):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    categories = Category.objects.order_by("name")

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        category_id = request.POST.get("category")
        purchase_price = request.POST.get("purchase_price", "0")
        selling_price = request.POST.get("selling_price", "0")
        stock = request.POST.get("stock", "0")
        size = request.POST.get("size", "").strip()
        color = request.POST.get("color", "").strip()
        description = request.POST.get("description", "").strip()
        image = request.FILES.get("image")

        if not name or not code or not category_id:
            messages.error(
                request,
                "Name, product code and category are required."
            )

            return render(
                request,
                "admin_portal/product_form.html",
                {
                    "categories": categories,
                    "form_data": request.POST,
                }
            )

        if Product.objects.filter(code=code).exists():
            messages.error(
                request,
                "A product with this code already exists."
            )

            return render(
                request,
                "admin_portal/product_form.html",
                {
                    "categories": categories,
                    "form_data": request.POST,
                }
            )

        product = Product.objects.create(
            name=name,
            code=code,
            category_id=category_id,
            purchase_price=purchase_price,
            selling_price=selling_price,
            stock=stock,
            size=size,
            color=color,
            description=description,
            image=image,
        )

        messages.success(
            request,
            f"{product.name} added successfully."
        )

        return redirect("product_list")

    return render(
        request,
        "admin_portal/product_form.html",
        {
            "categories": categories,
        }
    )


@login_required
def edit_product(request, id):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    product = get_object_or_404(Product, id=id)
    categories = Category.objects.order_by("name")

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        category_id = request.POST.get("category")

        if not name or not code or not category_id:
            messages.error(
                request,
                "Name, product code and category are required."
            )

            return render(
                request,
                "admin_portal/product_form.html",
                {
                    "product": product,
                    "categories": categories,
                }
            )

        code_exists = Product.objects.filter(
            code=code
        ).exclude(
            id=product.id
        ).exists()

        if code_exists:
            messages.error(
                request,
                "Another product already uses this code."
            )

            return render(
                request,
                "admin_portal/product_form.html",
                {
                    "product": product,
                    "categories": categories,
                }
            )

        product.name = name
        product.code = code
        product.category_id = category_id
        product.purchase_price = request.POST.get(
            "purchase_price",
            "0"
        )
        product.selling_price = request.POST.get(
            "selling_price",
            "0"
        )
        product.stock = request.POST.get(
            "stock",
            "0"
        )
        product.size = request.POST.get(
            "size",
            ""
        ).strip()
        product.color = request.POST.get(
            "color",
            ""
        ).strip()
        product.description = request.POST.get(
            "description",
            ""
        ).strip()

        if request.FILES.get("image"):
            product.image = request.FILES["image"]

        product.save()

        messages.success(
            request,
            f"{product.name} updated successfully."
        )

        return redirect("product_list")

    return render(
        request,
        "admin_portal/product_form.html",
        {
            "product": product,
            "categories": categories,
        }
    )


@login_required
def delete_product(request, id):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    product = get_object_or_404(Product, id=id)

    if request.method == "POST":

        product_name = product.name

        product.is_active = False
        product.save(update_fields=["is_active"])

        messages.success(
            request,
            f"{product_name} removed successfully."
        )

    return redirect("product_list")



@login_required
@user_passes_test(is_admin)
def add_product(request):

    categories = Category.objects.all().order_by("name")

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        category_id = request.POST.get("category")
        purchase_price = request.POST.get("purchase_price")
        selling_price = request.POST.get("selling_price")
        stock = request.POST.get("stock", 0)
        size = request.POST.get("size", "").strip()
        color = request.POST.get("color", "").strip()
        description = request.POST.get(
            "description",
            ""
        ).strip()

        if not name or not code:
            messages.error(
                request,
                "Product name and code are required."
            )
            return redirect("add_product")

        if Product.objects.filter(code=code).exists():
            messages.error(
                request,
                "Product code already exists."
            )
            return redirect("add_product")

        product = Product.objects.create(
            name=name,
            code=code,
            category_id=category_id,
            purchase_price=purchase_price,
            selling_price=selling_price,
            stock=stock,
            size=size,
            color=color,
            description=description,
            image=request.FILES.get("image"),
        )

        messages.success(
            request,
            f"{product.name} added successfully."
        )

        return redirect("admin_products")

    return render(
        request,
        "admin_portal/product_form.html",
        {
            "categories": categories,
        }
    )


@login_required
@user_passes_test(is_admin)
def edit_product(request, id):

    product = get_object_or_404(
        Product,
        id=id
    )

    categories = Category.objects.all().order_by("name")

    if request.method == "POST":

        product.name = request.POST.get(
            "name",
            ""
        ).strip()

        product.code = request.POST.get(
            "code",
            ""
        ).strip()

        product.category_id = request.POST.get(
            "category"
        )

        product.purchase_price = request.POST.get(
            "purchase_price"
        )

        product.selling_price = request.POST.get(
            "selling_price"
        )

        product.stock = request.POST.get(
            "stock",
            0
        )

        product.size = request.POST.get(
            "size",
            ""
        ).strip()

        product.color = request.POST.get(
            "color",
            ""
        ).strip()

        product.description = request.POST.get(
            "description",
            ""
        ).strip()

        if request.FILES.get("image"):
            product.image = request.FILES["image"]

        product.save()

        messages.success(
            request,
            "Product updated successfully."
        )

        return redirect("admin_products")

    return render(
        request,
        "admin_portal/product_form.html",
        {
            "product": product,
            "categories": categories,
            "edit_mode": True,
        }
    )


@login_required
@user_passes_test(is_admin)
def delete_product(request, id):

    product = get_object_or_404(
        Product,
        id=id
    )

    if request.method == "POST":

        product.is_active = False
        product.save()

        messages.success(
            request,
            "Product removed successfully."
        )

    return redirect("admin_products")



# =========================================
# CATEGORY MANAGEMENT
# =========================================

@login_required
def category_list(request):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    categories = Category.objects.order_by("-id")

    return render(
        request,
        "admin_portal/categories.html",
        {
            "categories": categories,
        }
    )


@login_required
def add_category(request):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        description = request.POST.get(
            "description",
            ""
        ).strip()

        if not name:
            messages.error(
                request,
                "Category name is required."
            )

            return render(
                request,
                "admin_portal/category_form.html"
            )

        if Category.objects.filter(
            name__iexact=name
        ).exists():

            messages.error(
                request,
                "This category already exists."
            )

            return render(
                request,
                "admin_portal/category_form.html"
            )

        Category.objects.create(
            name=name,
            description=description
        )

        messages.success(
            request,
            "Category added successfully."
        )

        return redirect("category_list")

    return render(
        request,
        "admin_portal/category_form.html"
    )


# =========================================
# STAFF MANAGEMENT
# =========================================

@login_required
def staff_list(request):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    staff_members = StaffProfile.objects.select_related(
        "user"
    ).order_by("-id")

    return render(
        request,
        "admin_portal/staff.html",
        {
            "staff_members": staff_members,
        }
    )


@login_required
def add_staff(request):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        role = request.POST.get(
            "role",
            "staff"
        )

        if not name or not username or not password:
            messages.error(
                request,
                "Name, username and password are required."
            )

            return render(
                request,
                "admin_portal/staff_form.html"
            )

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "This username is already in use."
            )

            return render(
                request,
                "admin_portal/staff_form.html"
            )

        if role not in ["admin", "staff"]:
            role = "staff"

        # Split name into first/last name
        name_parts = name.split()

        first_name = name_parts[0]

        last_name = " ".join(
            name_parts[1:]
        )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        StaffProfile.objects.create(
            user=user,
            phone=phone,
            role=role,
            is_active=True
        )

        messages.success(
            request,
            f"Staff account '{username}' created successfully."
        )

        return redirect("staff_list")

    return render(
        request,
        "admin_portal/staff_form.html"
    )


@login_required
def toggle_staff(request, id):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    staff = get_object_or_404(
        StaffProfile,
        id=id
    )

    # Prevent admin from disabling themselves
    if staff.user == request.user:

        messages.error(
            request,
            "You cannot deactivate your own account."
        )

        return redirect("staff_list")

    staff.is_active = not staff.is_active
    staff.user.is_active = staff.is_active

    staff.save(
        update_fields=["is_active"]
    )

    staff.user.save(
        update_fields=["is_active"]
    )

    if staff.is_active:

        messages.success(
            request,
            f"{staff.user.username} has been activated."
        )

    else:

        messages.warning(
            request,
            f"{staff.user.username} has been deactivated."
        )

    return redirect("staff_list")



@login_required
@user_passes_test(is_admin)
def toggle_staff(request, id):

    staff = get_object_or_404(
        StaffProfile,
        id=id
    )

    staff.is_active = not staff.is_active
    staff.save()

    messages.success(
        request,
        "Staff status updated."
    )

    return redirect("admin_staff")


# =========================================================
# SUPPLIER MANAGEMENT
# =========================================================

@login_required
@user_passes_test(is_admin)
def supplier_list(request):

    suppliers = Supplier.objects.all().order_by(
        "-id"
    )

    return render(
        request,
        "admin_portal/suppliers.html",
        {
            "suppliers": suppliers
        }
    )


@login_required
@user_passes_test(is_admin)
def add_supplier(request):

    if request.method == "POST":

        Supplier.objects.create(
            name=request.POST.get(
                "name",
                ""
            ).strip(),

            company=request.POST.get(
                "company",
                ""
            ).strip(),

            phone=request.POST.get(
                "phone",
                ""
            ).strip(),

            email=request.POST.get(
                "email",
                ""
            ).strip(),

            address=request.POST.get(
                "address",
                ""
            ).strip(),
        )

        messages.success(
            request,
            "Supplier added successfully."
        )

        return redirect("admin_suppliers")

    return render(
        request,
        "admin_portal/supplier_form.html"
    )


# =========================================================
# CUSTOMER MANAGEMENT
# =========================================================

@login_required
@user_passes_test(is_staff_member)
def customer_list(request):

    customers = Customer.objects.all().order_by(
        "-id"
    )

    return render(
        request,
        "billing/customers.html",
        {
            "customers": customers
        }
    )


@login_required
@user_passes_test(is_staff_member)
def add_customer(request):

    if request.method == "POST":

        Customer.objects.create(
            name=request.POST.get(
                "name",
                ""
            ).strip(),

            phone=request.POST.get(
                "phone",
                ""
            ).strip(),

            email=request.POST.get(
                "email",
                ""
            ).strip(),

            address=request.POST.get(
                "address",
                ""
            ).strip(),
        )

        messages.success(
            request,
            "Customer added successfully."
        )

        return redirect("customers")

    return render(
        request,
        "billing/customer_form.html"
    )


# =========================================================
# BILLING PORTAL
# =========================================================

@login_required
@user_passes_test(is_staff_member)
def billing(request):

    products = Product.objects.filter(
        is_active=True,
        stock__gt=0
    ).order_by("name")

    customers = Customer.objects.all().order_by(
        "name"
    )

    return render(
        request,
        "billing/billing.html",
        {
            "products": products,
            "customers": customers,
        }
    )


# =========================================================
# CREATE SALE
# =========================================================

@login_required
@user_passes_test(is_staff_member)
@transaction.atomic
def create_sale(request):

    if request.method != "POST":
        return redirect("billing")

    product_ids = request.POST.getlist(
        "product_id"
    )

    quantities = request.POST.getlist(
        "quantity"
    )

    customer_id = request.POST.get(
        "customer"
    )

    payment_method = request.POST.get(
        "payment_method"
    )

    discount = Decimal(
        request.POST.get(
            "discount",
            "0"
        )
    )

    if not product_ids:
        messages.error(
            request,
            "Cart is empty."
        )
        return redirect("billing")

    subtotal = Decimal("0.00")

    cart_items = []

    for product_id, quantity in zip(
        product_ids,
        quantities
    ):

        product = get_object_or_404(
            Product.objects.select_for_update(),
            id=product_id,
            is_active=True
        )

        quantity = int(quantity)

        if quantity <= 0:
            continue

        if product.stock < quantity:
            messages.error(
                request,
                f"Only {product.stock} units of "
                f"{product.name} are available."
            )
            return redirect("billing")

        item_total = (
            product.selling_price *
            quantity
        )

        subtotal += item_total

        cart_items.append(
            {
                "product": product,
                "quantity": quantity,
                "price": product.selling_price,
                "total": item_total,
            }
        )

    taxable_amount = max(
        subtotal - discount,
        Decimal("0.00")
    )

    tax = taxable_amount * Decimal("0.05")

    total = taxable_amount + tax

    sale = Sale.objects.create(
        invoice_number=generate_invoice_number(),
        staff=request.user,
        customer_id=customer_id or None,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        payment_method=payment_method,
    )

    for item in cart_items:

        SaleItem.objects.create(
            sale=sale,
            product=item["product"],
            quantity=item["quantity"],
            price=item["price"],
            total=item["total"],
        )

        item["product"].stock -= item["quantity"]
        item["product"].save(
            update_fields=["stock"]
        )

    Ledger.objects.create(
        transaction_type="sale",
        reference=sale.invoice_number,
        amount=total,
        description=f"Sale - {sale.invoice_number}",
    )

    messages.success(
        request,
        "Sale completed successfully."
    )

    return redirect(
        "invoice",
        sale_id=sale.id
    )


def generate_invoice_number():

    last_sale = Sale.objects.order_by(
        "-id"
    ).first()

    if not last_sale:
        number = 1
    else:
        number = last_sale.id + 1

    return f"INV-{number:05d}"


# =========================================================
# INVOICE
# =========================================================

@login_required
@user_passes_test(is_staff_member)
def invoice(request, sale_id):

    sale = get_object_or_404(
        Sale.objects.select_related(
            "staff",
            "customer"
        ).prefetch_related(
            "items__product"
        ),
        id=sale_id
    )

    return render(
        request,
        "billing/invoice.html",
        {
            "sale": sale
        }
    )


# =========================================================
# TRANSACTIONS
# =========================================================

@login_required
@user_passes_test(is_staff_member)
def transactions(request):

    sales = Sale.objects.select_related(
        "staff",
        "customer"
    ).order_by("-id")

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        sales = sales.filter(
            invoice_number__icontains=search
        )

    return render(
        request,
        "billing/transactions.html",
        {
            "sales": sales,
            "search": search,
        }
    )


# =========================================================
# PRODUCT RETURNS
# =========================================================

@login_required
@user_passes_test(is_admin)
@transaction.atomic
def process_return(request, sale_item_id):

    sale_item = get_object_or_404(
        SaleItem.objects.select_related(
            "sale",
            "product"
        ),
        id=sale_item_id
    )

    if request.method == "POST":

        quantity = int(
            request.POST.get(
                "quantity",
                1
            )
        )

        if quantity <= 0:
            messages.error(
                request,
                "Invalid return quantity."
            )
            return redirect("admin_returns")

        already_returned = ReturnItem.objects.filter(
            sale_item=sale_item
        ).aggregate(
            total=Sum("quantity")
        )["total"] or 0

        remaining = (
            sale_item.quantity -
            already_returned
        )

        if quantity > remaining:
            messages.error(
                request,
                "Return quantity exceeds sold quantity."
            )
            return redirect("admin_returns")

        return_record = Return.objects.create(
            sale=sale_item.sale,
            processed_by=request.user,
            reason=request.POST.get(
                "reason",
                ""
            ).strip(),
        )

        ReturnItem.objects.create(
            return_record=return_record,
            sale_item=sale_item,
            quantity=quantity,
        )

        sale_item.product.stock += quantity
        sale_item.product.save(
            update_fields=["stock"]
        )

        refund = (
            sale_item.price *
            quantity
        )

        Ledger.objects.create(
            transaction_type="return",
            reference=f"RET-{return_record.id:05d}",
            amount=-refund,
            description=(
                f"Return for "
                f"{sale_item.sale.invoice_number}"
            ),
        )

        messages.success(
            request,
            "Product return processed successfully."
        )

    return redirect("admin_returns")


@login_required
@user_passes_test(is_admin)
def return_list(request):

    returns = Return.objects.select_related(
        "sale",
        "processed_by"
    ).prefetch_related(
        "items__sale_item__product"
    ).order_by("-id")

    return render(
        request,
        "admin_portal/returns.html",
        {
            "returns": returns
        }
    )


# =========================================================
# LEDGER
# =========================================================

@login_required
def ledger(request):
    """
    Display all financial ledger transactions.
    """

    if not is_admin(request.user):
        messages.error(
            request,
            "Only administrators can access the ledger."
        )
        return redirect("login")

    entries = Ledger.objects.order_by("-id")

    transaction_type = request.GET.get(
        "transaction_type",
        ""
    ).strip()

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if transaction_type in [
        "sale",
        "return",
        "purchase",
        "expense",
        "adjustment",
    ]:
        entries = entries.filter(
            transaction_type=transaction_type
        )

    if search:
        entries = entries.filter(
            models.Q(reference__icontains=search) |
            models.Q(description__icontains=search)
        )

    # Summary values
    sales_total = (
        Ledger.objects
        .filter(transaction_type="sale")
        .aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0")
    )

    returns_total = (
        Ledger.objects
        .filter(transaction_type="return")
        .aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0")
    )

    purchases_total = (
        Ledger.objects
        .filter(transaction_type="purchase")
        .aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0")
    )

    expenses_total = (
        Ledger.objects
        .filter(transaction_type="expense")
        .aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0")
    )

    net_amount = (
        sales_total
        - returns_total
        - purchases_total
        - expenses_total
    )

    context = {
        "entries": entries,
        "transaction_type": transaction_type,
        "search": search,
        "sales_total": sales_total,
        "returns_total": returns_total,
        "purchases_total": purchases_total,
        "expenses_total": expenses_total,
        "net_amount": net_amount,
    }

    return render(
        request,
        "admin_portal/ledger.html",
        context
    )



# =========================================================
# REPORTS
# =========================================================
@login_required
def reports(request):
    """ Admin business reports. """ 
    if not is_admin(request.user):
         messages.error( request, "Only administrators can access reports." ) 
         return redirect("login") 
    today = timezone.localdate()
    total_sales = ( Sale.objects.aggregate( total=models.Sum("total") )["total"] or Decimal("0") ) 
    today_sales = ( Sale.objects.filter( created_at__date=today ).aggregate( total=models.Sum("total") )["total"] or Decimal("0") ) 
    total_bills = Sale.objects.count() 
    today_bills = Sale.objects.filter( created_at__date=today ).count() 

    total_purchases = ( Purchase.objects.aggregate( total=models.Sum("subtotal") )["total"] or Decimal("0") ) # ----------------------------- # Returns # ----------------------------- 
    total_returns = ( Ledger.objects.filter( transaction_type="return" ).aggregate( total=models.Sum("amount") )["total"] or Decimal("0") ) # ----------------------------- # Products # ----------------------------- 
    total_products = Product.objects.filter( is_active=True ).count() 
    low_stock_products = Product.objects.filter( is_active=True, stock__lte=5 ).order_by("stock") # ----------------------------- # Customers # ----------------------------- 
    total_customers = Customer.objects.count() # ----------------------------- # Staff # ----------------------------- 
    total_staff = StaffProfile.objects.filter( is_active=True ).count() # ----------------------------- # Payment breakdown # ----------------------------- 
    cash_sales = ( Sale.objects.filter( payment_method="cash" ).aggregate( total=models.Sum("total") )["total"] or Decimal("0") ) 
    card_sales = ( Sale.objects.filter( payment_method="card" ).aggregate( total=models.Sum("total") )["total"] or Decimal("0") ) 
    upi_sales = ( Sale.objects.filter( payment_method="upi" ).aggregate( total=models.Sum("total") )["total"] or Decimal("0") ) # ----------------------------- # Recent sales # ----------------------------- 
    recent_sales = Sale.objects.select_related( "customer", "staff" ).order_by("-id")[:10] 
    context = { "today": today, "total_sales": total_sales, "today_sales": today_sales, "total_bills": total_bills, "today_bills": today_bills, "total_purchases": total_purchases, "total_returns": total_returns, "total_products": total_products, "low_stock_products": low_stock_products, "total_customers": total_customers, "total_staff": total_staff, "cash_sales": cash_sales, "card_sales": card_sales, "upi_sales": upi_sales, "recent_sales": recent_sales, } 
    return render( request, "admin_portal/reports.html", context )
# =========================================================
# MOBILE ADMIN UI
# =========================================================

@login_required
@user_passes_test(is_admin)
def mobile_admin(request):

    total_products = Product.objects.filter(
        is_active=True
    ).count()

    total_staff = StaffProfile.objects.filter(
        role="staff"
    ).count()

    total_sales = Sale.objects.count()

    today_sales = Sale.objects.filter(
        created_at__date=__import__("datetime").date.today()
    ).aggregate(
        total=Sum("total")
    )["total"] or Decimal("0.00")

    low_stock = Product.objects.filter(
        stock__lte=5,
        is_active=True
    ).order_by("stock")[:5]

    context = {
        "total_products": total_products,
        "total_staff": total_staff,
        "total_sales": total_sales,
        "today_sales": today_sales,
        "low_stock": low_stock,
    }

    return render(
        request,
        "admin_portal/mobile/dashboard.html",
        context
    )


# =========================================================
# PROFILE
# =========================================================

@login_required
def profile(request):

    return render(
        request,
        "accounts/profile.html",
        {
            "user": request.user
        }
    )


# =========================================
# SUPPLIER MANAGEMENT
# =========================================

@login_required
def supplier_list(request):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    suppliers = Supplier.objects.order_by("-id")

    return render(
        request,
        "admin_portal/suppliers.html",
        {
            "suppliers": suppliers,
        }
    )


@login_required
def add_supplier(request):

    if not is_admin(request.user):
        messages.error(request, "Admin access required.")
        return redirect("billing")

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        company = request.POST.get("company", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()

        if not name:
            messages.error(
                request,
                "Supplier name is required."
            )

            return render(
                request,
                "admin_portal/supplier_form.html"
            )

        Supplier.objects.create(
            name=name,
            company=company,
            phone=phone,
            email=email,
            address=address
        )

        messages.success(
            request,
            f"Supplier '{name}' added successfully."
        )

        return redirect("supplier_list")

    return render(
        request,
        "admin_portal/supplier_form.html"
    )


# =========================================
# CUSTOMER MANAGEMENT
# =========================================

@login_required
def customer_list(request):

    if not is_staff_member(request.user):
        messages.error(request, "Access denied.")
        return redirect("login")

    customers = Customer.objects.order_by("-id")

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        customers = customers.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )

    return render(
        request,
        "billing/customers.html",
        {
            "customers": customers,
            "search": search,
        }
    )


@login_required
def add_customer(request):

    if not is_staff_member(request.user):
        messages.error(request, "Access denied.")
        return redirect("login")

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()

        if not name or not phone:

            messages.error(
                request,
                "Customer name and phone are required."
            )

            return render(
                request,
                "billing/customer_form.html"
            )

        customer = Customer.objects.create(
            name=name,
            phone=phone,
            email=email,
            address=address
        )

        messages.success(
            request,
            f"Customer '{customer.name}' added successfully."
        )

        return redirect("customer_list")

    return render(
        request,
        "billing/customer_form.html"
    )


from django.db import models


from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

# Make sure these imports are already present
from .models import Product, Customer, Sale, SaleItem, Ledger


@login_required
def billing(request):
    """
    Main POS billing screen.
    Staff can search products and add them to the cart.
    """

    if not is_staff_member(request.user):
        messages.error(request, "You do not have permission to access billing.")
        return redirect("login")

    products = Product.objects.filter(
        is_active=True,
        stock__gt=0
    ).select_related("category").order_by("name")

    customers = Customer.objects.order_by("-id")

    search = request.GET.get("search", "").strip()

    if search:
        products = products.filter(
            models.Q(name__icontains=search) |
            models.Q(code__icontains=search)
        )

    categories = Category.objects.filter(
        products__is_active=True,
        products__stock__gt=0,
    ).distinct().order_by("name")

    context = {
        "products": products,
        "customers": customers,
        "categories": categories,
        "search": search,
    }

    return render(request, "billing/billing.html", context)


@login_required
@transaction.atomic
def create_sale(request):
    """
    Create a sale from the POS cart.
    """

    if not is_staff_member(request.user):
        messages.error(request, "You do not have permission to create a bill.")
        return redirect("login")

    if request.method != "POST":
        return redirect("billing")

    product_ids = request.POST.getlist("product_id")
    quantities = request.POST.getlist("quantity")

    if not product_ids:
        messages.error(request, "Please add at least one product.")
        return redirect("billing")

    customer_id = request.POST.get("customer")
    payment_method = request.POST.get("payment_method", "cash")

    try:
        discount = Decimal(request.POST.get("discount", "0") or "0")
    except:
        discount = Decimal("0")

    if discount < 0:
        discount = Decimal("0")

    if payment_method not in ["cash", "card", "upi"]:
        payment_method = "cash"

    # Generate invoice number
    invoice_number = (
        f"INV-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        f"-{request.user.id}"
    )

    customer = None

    if customer_id:
        customer = get_object_or_404(Customer, id=customer_id)

    subtotal = Decimal("0")
    cart_items = []

    for product_id, quantity in zip(product_ids, quantities):

        try:
            quantity = int(quantity)
        except:
            continue

        if quantity <= 0:
            continue

        product = get_object_or_404(
            Product.objects.select_for_update(),
            id=product_id,
            is_active=True
        )

        if quantity > product.stock:
            messages.error(
                request,
                f"Only {product.stock} units of {product.name} are available."
            )
            return redirect("billing")

        item_total = product.selling_price * quantity
        subtotal += item_total

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "price": product.selling_price,
            "total": item_total,
        })

    if not cart_items:
        messages.error(request, "No valid products were selected.")
        return redirect("billing")

    # Prevent discount from exceeding subtotal
    if discount > subtotal:
        discount = subtotal

    # Currently no tax is applied
    tax = Decimal("0")

    total = subtotal - discount + tax

    sale = Sale.objects.create(
        invoice_number=invoice_number,
        staff=request.user,
        customer=customer,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        payment_method=payment_method,
    )

    # Create sale items and reduce stock
    for item in cart_items:

        SaleItem.objects.create(
            sale=sale,
            product=item["product"],
            quantity=item["quantity"],
            price=item["price"],
            total=item["total"],
        )

        item["product"].stock -= item["quantity"]
        item["product"].save(update_fields=["stock"])

    # Add transaction to ledger
    Ledger.objects.create(
        transaction_type="sale",
        reference=sale.invoice_number,
        amount=total,
        description=f"Sale generated by {request.user.username}",
    )

    messages.success(
        request,
        f"Bill {sale.invoice_number} created successfully."
    )

    return redirect("invoice", sale_id=sale.id)


@login_required
def invoice(request, sale_id):
    """
    Display a completed invoice.
    """

    if not is_staff_member(request.user):
        messages.error(request, "You do not have permission to view invoices.")
        return redirect("login")

    sale = get_object_or_404(
        Sale.objects.select_related(
            "staff",
            "customer"
        ).prefetch_related(
            "items__product"
        ),
        id=sale_id
    )

    return render(
        request,
        "billing/invoice.html",
        {
            "sale": sale,
        }
    )


@login_required
def transactions(request):
    """
    Display billing transaction history.
    """

    if not is_staff_member(request.user):
        messages.error(
            request,
            "You do not have permission to view transactions."
        )
        return redirect("login")

    sales = Sale.objects.select_related(
        "staff",
        "customer"
    ).order_by("-id")

    search = request.GET.get("search", "").strip()
    payment_method = request.GET.get("payment_method", "").strip()

    if search:
        sales = sales.filter(
            models.Q(invoice_number__icontains=search) |
            models.Q(customer__name__icontains=search) |
            models.Q(customer__phone__icontains=search) |
            models.Q(staff__username__icontains=search)
        )

    if payment_method in ["cash", "card", "upi"]:
        sales = sales.filter(
            payment_method=payment_method
        )

    total_sales = sum(
        sale.total for sale in sales
    )

    context = {
        "sales": sales,
        "search": search,
        "payment_method": payment_method,
        "total_sales": total_sales,
    }

    return render(
        request,
        "billing/transactions.html",
        context
    )


@login_required
def return_list(request):
    """
    Display completed product returns.
    """

    if not is_admin(request.user):
        messages.error(
            request,
            "Only administrators can manage product returns."
        )
        return redirect("login")

    returns = Return.objects.select_related(
        "sale",
        "processed_by"
    ).prefetch_related(
        "items__sale_item__product"
    ).order_by("-id")

    search = request.GET.get("search", "").strip()

    if search:
        returns = returns.filter(
            models.Q(sale__invoice_number__icontains=search) |
            models.Q(processed_by__username__icontains=search)
        )

    context = {
        "returns": returns,
        "search": search,
    }

    return render(
        request,
        "admin_portal/returns.html",
        context
    )


@login_required
@transaction.atomic
def process_return(request, sale_item_id):
    """
    Process a return for a particular sale item.
    """

    if not is_admin(request.user):
        messages.error(
            request,
            "Only administrators can process returns."
        )
        return redirect("login")

    sale_item = get_object_or_404(
        SaleItem.objects.select_related(
            "sale",
            "product"
        ),
        id=sale_item_id
    )

    # Already returned quantity
    returned_quantity = ReturnItem.objects.filter(
        sale_item=sale_item
    ).aggregate(
        total=models.Sum("quantity")
    )["total"] or 0

    available_return_quantity = (
        sale_item.quantity - returned_quantity
    )

    if request.method == "POST":

        try:
            quantity = int(
                request.POST.get("quantity", "0")
            )
        except (TypeError, ValueError):
            quantity = 0

        reason = request.POST.get("reason", "").strip()

        if quantity <= 0:
            messages.error(
                request,
                "Return quantity must be greater than zero."
            )
            return redirect(
                "process_return",
                sale_item_id=sale_item.id
            )

        if quantity > available_return_quantity:
            messages.error(
                request,
                f"Only {available_return_quantity} item(s) "
                f"are available for return."
            )
            return redirect(
                "process_return",
                sale_item_id=sale_item.id
            )

        return_record = Return.objects.create(
            sale=sale_item.sale,
            processed_by=request.user,
            reason=reason,
        )

        ReturnItem.objects.create(
            return_record=return_record,
            sale_item=sale_item,
            quantity=quantity,
        )

        # Restore returned quantity to stock
        product = Product.objects.select_for_update().get(
            id=sale_item.product.id
        )

        product.stock += quantity
        product.save(update_fields=["stock"])

        # Calculate returned amount
        return_amount = (
            sale_item.price * quantity
        )

        # Record return in ledger
        Ledger.objects.create(
            transaction_type="return",
            reference=sale_item.sale.invoice_number,
            amount=return_amount,
            description=(
                f"Return of {quantity} x "
                f"{sale_item.product.name}. "
                f"Reason: {reason or 'Not specified'}"
            ),
        )

        messages.success(
            request,
            f"{quantity} x {sale_item.product.name} "
            f"returned successfully."
        )

        return redirect("return_list")

    context = {
        "sale_item": sale_item,
        "available_quantity": available_return_quantity,
    }

    return render(
        request,
        "admin_portal/process_return.html",
        context
    )


@login_required
def purchase_list(request):
    """
    Display supplier purchase history.
    """

    if not is_admin(request.user):
        messages.error(
            request,
            "Only administrators can manage purchases."
        )
        return redirect("login")

    purchases = Purchase.objects.select_related(
        "supplier",
        "created_by"
    ).prefetch_related(
        "items__product"
    ).order_by("-id")

    search = request.GET.get("search", "").strip()

    if search:
        purchases = purchases.filter(
            models.Q(invoice_number__icontains=search) |
            models.Q(supplier__name__icontains=search) |
            models.Q(supplier__company__icontains=search)
        )

    context = {
        "purchases": purchases,
        "search": search,
    }

    return render(
        request,
        "admin_portal/purchases.html",
        context
    )


@login_required
@transaction.atomic
def add_purchase(request):
    """
    Record stock received from a supplier.
    """

    if not is_admin(request.user):
        messages.error(
            request,
            "Only administrators can add purchases."
        )
        return redirect("login")

    suppliers = Supplier.objects.order_by("name")

    products = Product.objects.filter(
        is_active=True
    ).order_by("name")

    if request.method == "POST":

        supplier_id = request.POST.get("supplier")
        invoice_number = request.POST.get(
            "invoice_number"
        ).strip()

        notes = request.POST.get(
            "notes",
            ""
        ).strip()

        product_ids = request.POST.getlist(
            "product_id"
        )

        quantities = request.POST.getlist(
            "quantity"
        )

        prices = request.POST.getlist(
            "purchase_price"
        )

        # -----------------------------
        # Basic validation
        # -----------------------------

        if not supplier_id:
            messages.error(
                request,
                "Please select a supplier."
            )
            return redirect("add_purchase")

        if not invoice_number:
            messages.error(
                request,
                "Please enter the supplier invoice number."
            )
            return redirect("add_purchase")

        if Purchase.objects.filter(
            invoice_number=invoice_number
        ).exists():

            messages.error(
                request,
                "This invoice number already exists."
            )

            return redirect("add_purchase")

        supplier = get_object_or_404(
            Supplier,
            id=supplier_id
        )

        purchase_items = []
        subtotal = Decimal("0")

        # -----------------------------
        # Validate products
        # -----------------------------

        for product_id, quantity, price in zip(
            product_ids,
            quantities,
            prices
        ):

            try:
                quantity = int(quantity)
                price = Decimal(price)
            except (ValueError, TypeError, ArithmeticError):
                continue

            if quantity <= 0 or price < 0:
                continue

            product = get_object_or_404(
                Product.objects.select_for_update(),
                id=product_id,
                is_active=True
            )

            item_total = price * quantity

            subtotal += item_total

            purchase_items.append({
                "product": product,
                "quantity": quantity,
                "purchase_price": price,
                "total": item_total,
            })

        if not purchase_items:

            messages.error(
                request,
                "Please add at least one valid product."
            )

            return redirect("add_purchase")

        # -----------------------------
        # Create purchase
        # -----------------------------

        purchase = Purchase.objects.create(
            supplier=supplier,
            invoice_number=invoice_number,
            subtotal=subtotal,
            notes=notes,
            created_by=request.user,
        )

        # -----------------------------
        # Create items + update stock
        # -----------------------------

        for item in purchase_items:

            PurchaseItem.objects.create(
                purchase=purchase,
                product=item["product"],
                quantity=item["quantity"],
                purchase_price=item["purchase_price"],
                total=item["total"],
            )

            product = item["product"]

            product.stock += item["quantity"]

            # Update purchase price with
            # latest supplier purchase price
            product.purchase_price = item["purchase_price"]

            product.save(
                update_fields=[
                    "stock",
                    "purchase_price"
                ]
            )

        # -----------------------------
        # Ledger
        # -----------------------------

        Ledger.objects.create(
            transaction_type="purchase",
            reference=purchase.invoice_number,
            amount=subtotal,
            description=(
                f"Purchase from {supplier.name}"
            ),
        )

        messages.success(
            request,
            f"Purchase {purchase.invoice_number} "
            f"recorded successfully."
        )

        return redirect("purchase_list")

    context = {
        "suppliers": suppliers,
        "products": products,
    }

    return render(
        request,
        "admin_portal/purchase_form.html",
        context
    )

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone

@login_required
def mobile_admin(request):
    if not is_admin(request.user):
        return redirect("login")

    today = timezone.localdate()

    total_products = Product.objects.filter(is_active=True).count()
    total_staff = StaffProfile.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.count()
    total_customers = Customer.objects.count()
    total_purchases = Purchase.objects.count()
    total_sales = Sale.objects.count()

    low_stock_products = Product.objects.filter(
        is_active=True,
        stock__lte=5
    ).order_by("stock")[:5]

    today_sales = Sale.objects.filter(
        created_at__date=today
    ).aggregate(
        total=Sum("total")
    )["total"] or 0

    recent_sales = Sale.objects.select_related(
        "staff",
        "customer"
    ).order_by("-id")[:5]

    context = {
        "total_products": total_products,
        "total_staff": total_staff,
        "total_suppliers": total_suppliers,
        "total_customers": total_customers,
        "total_purchases": total_purchases,
        "total_sales": total_sales,
        "today_sales": today_sales,
        "low_stock_products": low_stock_products,
        "recent_sales": recent_sales,
    }

    return render(
        request,
        "admin_portal/mobile/dashboard.html",
        context
    )

