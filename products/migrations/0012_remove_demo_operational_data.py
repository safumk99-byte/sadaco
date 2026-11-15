from django.db import migrations


def remove_demo_operational_data(apps, schema_editor):
    # The founder confirmed that pre-existing business records are demo data.
    # Preserve authentication users, user profiles, staff profiles, departments,
    # and the newly seeded material/machine master data.
    def clear(app, model):
        apps.get_model(app, model).objects.all().delete()

    # Remove protected dependants before production jobs and sales orders.
    clear("inventory", "MaterialIssue")
    clear("quality", "ReworkRecord")
    clear("quality", "PackingRecord")
    clear("quality", "QualityCheck")
    clear("production", "ProductionProgress")
    clear("production", "ProductionIssue")
    clear("production", "ProductionMaterial")
    clear("production", "ProductionJob")

    clear("sales", "DeliveryRecord")
    clear("sales", "CustomerFeedback")
    clear("sales", "PaymentRecord")
    clear("sales", "DesignApproval")
    clear("sales", "SalesOrder")
    clear("sales", "Quotation")
    clear("sales", "OrderRequest")
    clear("sales", "Enquiry")
    clear("sales", "CustomerInteraction")
    clear("sales", "CustomerNotification")

    # Finance links are SET_NULL, but clear the demo ledgers and supplier payments
    # before removing their purchase-order parents.
    clear("finance", "FinanceTransaction")
    clear("finance", "SupplierPayment")
    clear("finance", "Expense")
    clear("finance", "ExpenseCategory")

    clear("purchase", "GoodsReceipt")
    clear("purchase", "PurchaseItem")
    clear("purchase", "PurchaseOrder")
    clear("purchase", "Supplier")

    clear("marketing", "MarketingLead")
    clear("marketing", "MarketingContent")
    clear("marketing", "Campaign")

    clear("inventory", "StockCount")
    clear("inventory", "ReorderAlert")
    clear("products", "StockTransaction")
    clear("products", "Product")

    # ProductCategory uses PROTECT for its parent relation; remove leaf nodes first.
    Category = apps.get_model("products", "ProductCategory")
    while Category.objects.exists():
        leaf_ids = list(
            Category.objects.exclude(
                pk__in=Category.objects.exclude(parent__isnull=True).values_list("parent_id", flat=True)
            ).values_list("pk", flat=True)
        )
        if not leaf_ids:
            # Defensive fallback for malformed cyclic demo hierarchies.
            Category.objects.all().delete()
            break
        Category.objects.filter(pk__in=leaf_ids).delete()

    # Demo customer profiles are removed; their linked login accounts remain.
    clear("sales", "Customer")

    # Remove demo staff activity while retaining the staff accounts and profiles.
    clear("staff", "StaffTask")
    clear("staff", "StaffAttendance")
    clear("staff", "PerformanceRecord")


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0011_seed_staff_compensation"),
        ("sales", "0007_customer_department"),
        ("purchase", "0001_initial"),
        ("production", "0001_initial"),
        ("quality", "0001_initial"),
        ("inventory", "0001_initial"),
        ("finance", "0003_financetransaction_supplier_payment"),
        ("marketing", "0001_initial"),
        ("staff", "0002_staffprofile_department"),
    ]

    operations = [
        migrations.RunPython(remove_demo_operational_data, migrations.RunPython.noop),
    ]
