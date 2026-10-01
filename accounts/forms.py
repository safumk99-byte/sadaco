from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile
from .services import available_roles

INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-slate-500"

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Mobile Number",
        widget=forms.TextInput(
            attrs={
                "class": INPUT,
                "autocomplete": "username",
                "placeholder": "Username or mobile number",
                "inputmode": "text",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": INPUT, "autocomplete": "current-password", "placeholder": "Password"}
        )
    )

    def clean(self):
        """Authenticate both internal users and SADACO customers from one login form."""
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not username or not password:
            return super().clean()

        # First preserve the existing internal username/password login.
        user = authenticate(self.request, username=username, password=password)
        if user is not None:
            self.confirm_login_allowed(user)
            self.user_cache = user
            return self.cleaned_data

        # If the identifier is a customer mobile number, authenticate the
        # linked Django user without changing the customer's stored phone.
        try:
            import re
            from sales.models import Customer
            entered_digits = re.sub(r"\D", "", username)
            customer = None
            if entered_digits:
                for candidate in Customer.objects.filter(user__isnull=False).select_related("user"):
                    saved_digits = re.sub(r"\D", "", candidate.phone or "")
                    if saved_digits == entered_digits:
                        customer = candidate
                        break

            if customer is not None:
                customer_user = customer.user
                if not customer_user.is_active:
                    raise forms.ValidationError("This customer account is inactive. Please contact SADACO.")
                if customer_user.check_password(password):
                    self.confirm_login_allowed(customer_user)
                    self.user_cache = customer_user
                    return self.cleaned_data
        except forms.ValidationError:
            raise
        except Exception:
            # Do not expose internal lookup/database details to the user.
            pass

        raise forms.ValidationError("Please enter a correct username/mobile number and password.")

class UserCreateForm(UserCreationForm):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": INPUT}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    role = forms.ChoiceField(choices=(), widget=forms.Select(attrs={"class": INPUT}))
    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = available_roles(actor) if actor else []

    class Meta:
        model = User
        fields = ("username","first_name","last_name","email","role","password1","password2")
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            UserProfile.objects.create(user=user, role=self.cleaned_data["role"], phone=self.cleaned_data["phone"])
        return user

class UserEditForm(forms.Form):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": INPUT}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    role = forms.ChoiceField(choices=(), widget=forms.Select(attrs={"class": INPUT}))
    is_active = forms.BooleanField(required=False)

    def __init__(self, *args, actor=None, current_role=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.current_role = current_role
        self.fields["role"].choices = available_roles(actor) if actor else []

class AdminPasswordChangeForm(forms.Form):
    new_password = forms.CharField(min_length=8, widget=forms.PasswordInput(attrs={"class": INPUT}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": INPUT}))
    def clean(self):
        data = super().clean()
        if data.get("new_password") != data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return data
