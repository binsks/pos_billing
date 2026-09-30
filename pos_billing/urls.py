from django.urls import path
from . import views


urlpatterns = [

   
    path(
        "",
        views.login_view,
        name="home"
    ),

    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),



    path(
        "admin/",
        views.admin_dashboard,
        name="admin_home"
    ),

    path(
        "admin-dashboard/",
        views.admin_dashboard,
        name="admin_dashboard"
    ),

    path(
        "admin/mobile/",
        views.mobile_admin,
        name="mobile_admin"
    ),


  
    path(
        "admin/products/",
        views.product_list,
        name="admin_products"
    ),

    path(
        "admin/products/",
        views.product_list,
        name="product_list"
    ),

    path(
        "admin/products/add/",
        views.add_product,
        name="add_product"
    ),

    path(
        "admin/products/edit/<int:id>/",
        views.edit_product,
        name="edit_product"
    ),

    path(
        "admin/products/delete/<int:id>/",
        views.delete_product,
        name="delete_product"
    ),




    path(
        "admin/categories/",
        views.category_list,
        name="admin_categories"
    ),

    path(
        "admin/categories/",
        views.category_list,
        name="category_list"
    ),

    path(
        "admin/categories/add/",
        views.add_category,
        name="add_category"
    ),
    path(
            "admin/categories_form",
            views.add_category,
            name="category_form"
        ),
    




    path(
        "admin/staff/",
        views.staff_list,
        name="admin_staff"
    ),

    path(
        "admin/staff/",
        views.staff_list,
        name="staff_list"
    ),

    path(
        "admin/staff/add/",
        views.add_staff,
        name="add_staff"
    ),

    path(
        "admin/staff/toggle/<int:id>/",
        views.toggle_staff,
        name="toggle_staff"
    ),


  
    path(
        "admin/suppliers/",
        views.supplier_list,
        name="admin_suppliers"
    ),

    path(
        "admin/suppliers/",
        views.supplier_list,
        name="supplier_list"
    ),

    path(
        "admin/suppliers/add/",
        views.add_supplier,
        name="add_supplier"
    ),




    path(
        "customers/",
        views.customer_list,
        name="customers"
    ),

    path(
        "customers/",
        views.customer_list,
        name="customer_list"
    ),

    path(
        "customers/add/",
        views.add_customer,
        name="add_customer"
    ),


    path(
        "billing/",
        views.billing,
        name="billing"
    ),

    path(
        "billing/create/",
        views.create_sale,
        name="create_sale"
    ),

    path(
        "billing/transactions/",
        views.transactions,
        name="transactions"
    ),

    path(
        "billing/invoice/<int:sale_id>/",
        views.invoice,
        name="invoice"
    ),


 

    path(
        "admin/returns/",
        views.return_list,
        name="admin_returns"
    ),

    path(
        "admin/returns/",
        views.return_list,
        name="return_list"
    ),

    path(
        "admin/returns/process/<int:sale_item_id>/",
        views.process_return,
        name="process_return"
    ),



    path(
        "admin/ledger/",
        views.ledger,
        name="admin_ledger"
    ),

    path(
        "admin/ledger/",
        views.ledger,
        name="ledger"
    ),



    path(
        "admin/reports/",
        views.reports,
        name="admin_reports"
    ),

    path(
        "admin/reports/",
        views.reports,
        name="reports"
    ),




    path(
        "profile/",
        views.profile,
        name="profile"
    ),

 

    path(
        "admin/purchases/",
        views.purchase_list,
        name="purchase_list"
    ),

    path(
        "admin/purchases/add/",
        views.add_purchase,
        name="add_purchase"
    ),

]
