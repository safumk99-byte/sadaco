from django import forms
from django.contrib.auth.models import User

from products.models import Product
from staff.models import StaffProfile

from .models import CustomerInteraction, Customer, CustomerNotification, DesignApproval, Enquiry, OrderRequest, Quotation, SalesOrder

INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-400"


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "alternate_phone", "email", "address", "status", "notes"]
        widgets = {f: forms.TextInput(attrs={"class": INPUT}) for f in ["name", "phone", "alternate_phone", "email"]}
        widgets.update({"address": forms.Textarea(attrs={"class": INPUT, "rows": 3}), "status": forms.Select(attrs={"class": INPUT}), "notes": forms.Textarea(attrs={"class": INPUT, "rows": 3})})


class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ["customer", "channel", "product_type", "quantity", "design_reference", "deadline", "budget_range", "expected_delivery_date", "status", "requirement", "response_time_note", "assigned_to"]
        widgets = {
            "customer": forms.Select(attrs={"class": INPUT}), "channel": forms.Select(attrs={"class": INPUT}), "product_type": forms.TextInput(attrs={"class": INPUT}),
            "quantity": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "design_reference": forms.TextInput(attrs={"class": INPUT}),
            "deadline": forms.DateInput(attrs={"class": INPUT, "type": "date"}), "budget_range": forms.TextInput(attrs={"class": INPUT}),
            "expected_delivery_date": forms.DateInput(attrs={"class": INPUT, "type": "date"}), "status": forms.Select(attrs={"class": INPUT}),
            "requirement": forms.Textarea(attrs={"class": INPUT, "rows": 4}), "response_time_note": forms.Textarea(attrs={"class": INPUT, "rows": 3}), "assigned_to": forms.Select(attrs={"class": INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.filter(status=Customer.Status.ACTIVE)
        self.fields["assigned_to"].queryset = User.objects.filter(is_active=True).order_by("first_name", "username")
        self.fields["assigned_to"].required = False


class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ["customer", "enquiry", "order_request", "item_description", "quantity", "material_cost", "labour_cost", "machine_cost", "finishing_cost", "packaging_cost", "delivery_cost", "quoted_price", "delivery_timeline", "advance_required", "valid_until", "status", "notes"]
        widgets = {"customer": forms.Select(attrs={"class": INPUT}), "enquiry": forms.Select(attrs={"class": INPUT}), "order_request": forms.Select(attrs={"class": INPUT}), "item_description": forms.TextInput(attrs={"class": INPUT}), "quantity": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "material_cost": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "labour_cost": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "machine_cost": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "finishing_cost": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "packaging_cost": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "delivery_cost": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "quoted_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "delivery_timeline": forms.TextInput(attrs={"class": INPUT}), "advance_required": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "valid_until": forms.DateInput(attrs={"class": INPUT, "type": "date"}), "status": forms.Select(attrs={"class": INPUT}), "notes": forms.Textarea(attrs={"class": INPUT, "rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.filter(status=Customer.Status.ACTIVE)
        self.fields["enquiry"].queryset = Enquiry.objects.select_related("customer").order_by("-created_at")
        self.fields["enquiry"].required = False
        self.fields["order_request"].queryset = OrderRequest.objects.select_related("customer").order_by("-created_at")
        self.fields["order_request"].required = False

    def clean(self):
        cleaned = super().clean()
        customer = cleaned.get("customer")
        enquiry = cleaned.get("enquiry")
        order_request = cleaned.get("order_request")
        if customer and enquiry and enquiry.customer_id != customer.id:
            self.add_error("enquiry", "Selected enquiry belongs to a different customer.")
        if customer and order_request and order_request.customer_id != customer.id:
            self.add_error("order_request", "Selected request belongs to a different customer.")
        return cleaned


class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ["customer", "quotation", "item_description", "quantity", "confirmed_price", "design_reference", "delivery_date", "deadline", "responsible_staff", "advance_required", "status", "notes"]
        widgets = {"customer": forms.Select(attrs={"class": INPUT}), "quotation": forms.Select(attrs={"class": INPUT}), "item_description": forms.TextInput(attrs={"class": INPUT}), "quantity": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "confirmed_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "design_reference": forms.TextInput(attrs={"class": INPUT}), "delivery_date": forms.DateInput(attrs={"class": INPUT, "type": "date"}), "deadline": forms.DateInput(attrs={"class": INPUT, "type": "date"}), "responsible_staff": forms.Select(attrs={"class": INPUT}), "advance_required": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}), "status": forms.Select(attrs={"class": INPUT}), "notes": forms.Textarea(attrs={"class": INPUT, "rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.filter(status=Customer.Status.ACTIVE)
        self.fields["quotation"].queryset = Quotation.objects.select_related("customer").order_by("-created_at")
        self.fields["quotation"].required = False
        self.fields["responsible_staff"].queryset = StaffProfile.objects.filter(status=StaffProfile.Status.ACTIVE).select_related("user")
        self.fields["responsible_staff"].required = False

    def clean(self):
        cleaned = super().clean()
        customer = cleaned.get("customer")
        quotation = cleaned.get("quotation")
        if customer and quotation and quotation.customer_id != customer.id:
            self.add_error("quotation", "Selected quotation belongs to a different customer.")
        delivery = cleaned.get("delivery_date")
        deadline = cleaned.get("deadline")
        if delivery and deadline and delivery < deadline:
            self.add_error("delivery_date", "Delivery date cannot be before the order deadline.")
        return cleaned


class CustomerRegistrationForm(forms.Form):
    name = forms.CharField(max_length=180, widget=forms.TextInput(attrs={"class": INPUT}))
    phone = forms.CharField(max_length=30, widget=forms.TextInput(attrs={"class": INPUT, "autocomplete": "tel"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": INPUT, "autocomplete": "email"}))
    password = forms.CharField(min_length=8, widget=forms.PasswordInput(attrs={"class": INPUT, "autocomplete": "new-password"}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": INPUT, "autocomplete": "new-password"}))

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if Customer.objects.filter(phone=phone, user__isnull=False).exists():
            raise forms.ValidationError("An account already exists for this phone number.")
        return phone

    def clean(self):
        data = super().clean()
        if data.get("password") and data.get("confirm_password") and data["password"] != data["confirm_password"]:
            raise forms.ValidationError("Passwords do not match.")
        return data


class CustomerRequestForm(forms.ModelForm):
    class Meta:
        model = OrderRequest
        fields = [
            "request_type", "product", "product_name", "quantity", "size",
            "material_preference", "requirement", "budget", "requested_date",
            "design_requirement", "reference_file",
        ]
        widgets = {
            "request_type": forms.Select(attrs={"class": INPUT}),
            "product": forms.Select(attrs={"class": INPUT}),
            "product_name": forms.TextInput(attrs={"class": INPUT}),
            "quantity": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0.01"}),
            "size": forms.TextInput(attrs={"class": INPUT}),
            "material_preference": forms.TextInput(attrs={"class": INPUT}),
            "requirement": forms.Textarea(attrs={"class": INPUT, "rows": 5}),
            "budget": forms.TextInput(attrs={"class": INPUT}),
            "requested_date": forms.DateInput(attrs={"class": INPUT, "type": "date"}),
            "design_requirement": forms.Textarea(attrs={"class": INPUT, "rows": 4}),
            "reference_file": forms.ClearableFileInput(attrs={"class": INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(
            status=Product.Status.ACTIVE
        ).order_by("name")
        self.fields["product"].required = False

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        product_name = (cleaned.get("product_name") or "").strip()
        if not product and not product_name:
            self.add_error("product_name", "Select a product or enter the required work/product.")
        if cleaned.get("quantity") is not None and cleaned["quantity"] <= 0:
            self.add_error("quantity", "Quantity must be greater than zero.")
        return cleaned


class DesignApprovalForm(forms.ModelForm):
    class Meta:
        model = DesignApproval
        fields = ["file", "notes"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": INPUT, "accept": ".pdf,.png,.jpg,.jpeg,.webp"}),
            "notes": forms.Textarea(attrs={"class": INPUT, "rows": 5, "placeholder": "Explain the design, revision notes or customer instructions..."}),
        }

    def clean_file(self):
        uploaded = self.cleaned_data.get("file")
        if uploaded:
            allowed = {"pdf", "png", "jpg", "jpeg", "webp"}
            ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
            if ext not in allowed:
                raise forms.ValidationError("Only PDF, PNG, JPG, JPEG and WEBP design files are allowed.")
            if uploaded.size > 15 * 1024 * 1024:
                raise forms.ValidationError("Design file must be 15 MB or smaller.")
        return uploaded


class CustomerInteractionForm(forms.ModelForm):
    class Meta:
        model = CustomerInteraction
        fields = ["interaction_type", "subject", "notes", "next_follow_up", "completed"]
        widgets = {
            "next_follow_up": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
