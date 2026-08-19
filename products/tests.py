from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from .forms import ProductForm
from .models import Product, ProductCategory, StockTransaction


class ProductModuleTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER)
        self.staff = User.objects.create_user(username="staff", password="StrongPass123!")
        UserProfile.objects.create(user=self.staff, role=UserProfile.Role.STAFF)
        self.category = ProductCategory.objects.create(name="General")

    def test_product_list_requires_login(self):
        response = self.client.get(reverse("products:list"))
        self.assertEqual(response.status_code, 302)

    def test_manager_can_view_products(self):
        self.client.login(username="manager", password="StrongPass123!")
        response = self.client.get(reverse("products:list"))
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_create_product(self):
        self.client.login(username="staff", password="StrongPass123!")
        response = self.client.get(reverse("products:create"))
        self.assertEqual(response.status_code, 403)

    def test_sku_is_normalized(self):
        form = ProductForm(data={
            "name": "Test Product", "sku": " ab-001 ",
            "category": self.category.pk, "description": "",
            "unit": "Piece", "selling_price": "100",
            "cost_price": "60", "stock_quantity": "10",
            "low_stock_threshold": "2", "status": "active",
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["sku"], "AB-001")

    def test_editing_product_with_inactive_category_remains_valid(self):
        category = ProductCategory.objects.create(name="Old Category", is_active=False)
        product = Product.objects.create(
            name="Existing Product", sku="OLD-001", category=category,
            selling_price=Decimal("100"), stock_quantity=Decimal("10"),
            low_stock_threshold=Decimal("2"),
        )
        form = ProductForm(instance=product, data={
            "name": "Existing Product", "sku": "OLD-001",
            "category": category.pk, "description": "",
            "unit": "Piece", "selling_price": "100",
            "cost_price": "60", "stock_quantity": "10",
            "low_stock_threshold": "2", "status": "active",
        })
        self.assertTrue(form.is_valid())

    def test_low_stock_property(self):
        product = Product.objects.create(
            name="Low Stock", sku="LOW-001", category=self.category,
            selling_price=Decimal("100"), stock_quantity=Decimal("2"),
            low_stock_threshold=Decimal("2"),
        )
        self.assertTrue(product.is_low_stock)


class InventoryModuleTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.manager = User.objects.create_user(username="inventory_manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER)
        self.category = ProductCategory.objects.create(name="Inventory")
        self.product = Product.objects.create(
            name="Inventory Product", sku="INV-001", category=self.category,
            selling_price=Decimal("100"), cost_price=Decimal("50"),
            stock_quantity=Decimal("10"), low_stock_threshold=Decimal("2"),
        )

    def test_stock_in_updates_balance_and_creates_ledger(self):
        from .inventory import record_stock_transaction
        record = record_stock_transaction(
            product_id=self.product.pk,
            transaction_type=StockTransaction.TransactionType.IN,
            quantity=Decimal("5"),
            user=self.manager,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("15"))
        self.assertEqual(record.balance_after, Decimal("15"))

    def test_stock_out_cannot_make_balance_negative(self):
        from .inventory import record_stock_transaction
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            record_stock_transaction(
                product_id=self.product.pk,
                transaction_type=StockTransaction.TransactionType.OUT,
                quantity=Decimal("11"),
                user=self.manager,
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("10"))

    def test_adjustment_sets_exact_balance(self):
        from .inventory import record_stock_transaction
        record_stock_transaction(
            product_id=self.product.pk,
            transaction_type=StockTransaction.TransactionType.ADJUSTMENT,
            quantity=Decimal("7"),
            user=self.manager,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("7"))

    def test_stock_page_requires_login(self):
        response = self.client.get(reverse("products:stock"))
        self.assertEqual(response.status_code, 302)
