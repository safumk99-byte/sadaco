from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
import uuid


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.name


class Expense(models.Model):
    class Status(models.TextChoices):
        DRAFT="draft","Draft"
        PAID="paid","Paid"
        CANCELLED="cancelled","Cancelled"

    expense_no=models.CharField(max_length=30,unique=True,editable=False)
    category=models.ForeignKey(ExpenseCategory,on_delete=models.PROTECT,related_name="expenses")
    amount=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    expense_date=models.DateField(default=timezone.localdate)
    payment_method=models.CharField(max_length=30,default="cash")
    reference=models.CharField(max_length=120,blank=True)
    description=models.TextField(blank=True)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.PAID)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="created_expenses")
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=["-expense_date","-created_at"]
        indexes=[models.Index(fields=["status","expense_date"]),models.Index(fields=["category","expense_date"])]

    def save(self,*args,**kwargs):
        if not self.expense_no:
            self.expense_no=f"EXP-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args,**kwargs)


class FinanceTransaction(models.Model):
    class Type(models.TextChoices):
        INCOME="income","Income"
        EXPENSE="expense","Expense"

    class Status(models.TextChoices):
        POSTED="posted","Posted"
        VOID="void","Void"

    transaction_no=models.CharField(max_length=30,unique=True,editable=False)
    transaction_type=models.CharField(max_length=20,choices=Type.choices)
    amount=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    transaction_date=models.DateField(default=timezone.localdate)
    payment_method=models.CharField(max_length=30,default="cash")
    reference=models.CharField(max_length=120,blank=True)
    description=models.TextField(blank=True)
    sales_payment=models.ForeignKey("sales.PaymentRecord",on_delete=models.SET_NULL,null=True,blank=True,related_name="finance_transactions")
    expense=models.ForeignKey(Expense,on_delete=models.SET_NULL,null=True,blank=True,related_name="finance_transactions")
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.POSTED)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="finance_transactions")
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=["-transaction_date","-created_at"]
        indexes=[models.Index(fields=["transaction_type","transaction_date"]),models.Index(fields=["status","transaction_date"])]

    def save(self,*args,**kwargs):
        if not self.transaction_no:
            self.transaction_no=f"TXN-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args,**kwargs)


class SupplierPayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        BANK = "bank", "Bank Transfer"
        CARD = "card", "Card"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    payment_no = models.CharField(max_length=30, unique=True, editable=False)
    purchase_order = models.ForeignKey("purchase.PurchaseOrder", on_delete=models.PROTECT, related_name="supplier_payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    payment_date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PAID)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_supplier_payments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-created_at"]
        indexes = [
            models.Index(fields=["purchase_order", "status"]),
            models.Index(fields=["payment_date", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.payment_no:
            self.payment_no = f"SP-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
