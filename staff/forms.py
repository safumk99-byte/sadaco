from django import forms
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.db import transaction
from django.db import models

from .models import (
    Designation,
    PerformanceRecord,
    StaffAttendance,
    StaffProfile,
    StaffTask,
    WorkArea,
)

INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-400"


class StaffCreateForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": INPUT}))
    password = forms.CharField(min_length=8, widget=forms.PasswordInput(attrs={"class": INPUT}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": INPUT}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": INPUT}))
    staff_id = forms.CharField(max_length=30, widget=forms.TextInput(attrs={"class": INPUT}))
    designation = forms.ModelChoiceField(queryset=Designation.objects.filter(is_active=True), required=False, widget=forms.Select(attrs={"class": INPUT}))
    work_area = forms.ModelChoiceField(queryset=WorkArea.objects.filter(is_active=True), required=False, widget=forms.Select(attrs={"class": INPUT}))
    phone = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    joining_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": INPUT, "type": "date"}))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": INPUT, "rows": 3}))
    status = forms.ChoiceField(choices=StaffProfile.Status.choices, widget=forms.Select(attrs={"class": INPUT}))
    photo = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={"class": INPUT}))

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already in use.")
        return username

    def clean_staff_id(self):
        value = self.cleaned_data["staff_id"]
        if StaffProfile.objects.filter(staff_id=value).exists():
            raise forms.ValidationError("This Staff ID already exists.")
        return value

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
        )
        UserProfile.objects.create(user=user, role=UserProfile.Role.STAFF)
        profile = StaffProfile.objects.create(
            user=user,
            staff_id=data["staff_id"],
            designation=data["designation"],
            work_area=data["work_area"],
            phone=data["phone"],
            joining_date=data["joining_date"],
            address=data["address"],
            status=data["status"],
            photo=data["photo"],
        )
        return profile


class StaffEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": INPUT}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": INPUT}))

    class Meta:
        model = StaffProfile
        fields = ["staff_id", "designation", "work_area", "phone", "joining_date", "address", "status", "photo", "notes"]
        widgets = {
            "staff_id": forms.TextInput(attrs={"class": INPUT}),
            "designation": forms.Select(attrs={"class": INPUT}),
            "work_area": forms.Select(attrs={"class": INPUT}),
            "phone": forms.TextInput(attrs={"class": INPUT}),
            "joining_date": forms.DateInput(attrs={"class": INPUT, "type": "date"}),
            "address": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
            "status": forms.Select(attrs={"class": INPUT}),
            "photo": forms.ClearableFileInput(attrs={"class": INPUT}),
            "notes": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        designation_qs = Designation.objects.filter(is_active=True)
        if self.instance and self.instance.designation_id:
            designation_qs = Designation.objects.filter(
                models.Q(is_active=True) | models.Q(pk=self.instance.designation_id)
            )
        work_area_qs = WorkArea.objects.filter(is_active=True)
        if self.instance and self.instance.work_area_id:
            work_area_qs = WorkArea.objects.filter(
                models.Q(is_active=True) | models.Q(pk=self.instance.work_area_id)
            )
        self.fields["designation"].queryset = designation_qs
        self.fields["work_area"].queryset = work_area_qs
        if self.instance and self.instance.user_id:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

    @transaction.atomic
    def save(self, commit=True):
        profile = super().save(commit=commit)
        if commit:
            user = profile.user
            user.first_name = self.cleaned_data["first_name"]
            user.last_name = self.cleaned_data["last_name"]
            user.email = self.cleaned_data["email"]
            user.save(update_fields=["first_name", "last_name", "email"])
        return profile


class DesignationForm(forms.ModelForm):
    class Meta:
        model = Designation
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT}),
            "description": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
            "is_active": forms.CheckboxInput(),
        }


class WorkAreaForm(forms.ModelForm):
    class Meta:
        model = WorkArea
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT}),
            "description": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
            "is_active": forms.CheckboxInput(),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = StaffTask
        fields = ["title", "description", "assigned_to", "due_date", "priority", "status", "remarks"]
        widgets = {
            "title": forms.TextInput(attrs={"class": INPUT}),
            "description": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
            "assigned_to": forms.Select(attrs={"class": INPUT}),
            "due_date": forms.DateInput(attrs={"class": INPUT, "type": "date"}),
            "priority": forms.Select(attrs={"class": INPUT}),
            "status": forms.Select(attrs={"class": INPUT}),
            "remarks": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = StaffProfile.objects.filter(
            status=StaffProfile.Status.ACTIVE
        ).select_related("user")


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = StaffAttendance
        fields = ["staff", "date", "status", "remarks"]
        widgets = {
            "staff": forms.Select(attrs={"class": INPUT}),
            "date": forms.DateInput(attrs={"class": INPUT, "type": "date"}),
            "status": forms.Select(attrs={"class": INPUT}),
            "remarks": forms.TextInput(attrs={"class": INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["staff"].queryset = StaffProfile.objects.filter(status=StaffProfile.Status.ACTIVE)

    def clean(self):
        cleaned = super().clean()
        staff = cleaned.get("staff")
        day = cleaned.get("date")
        if staff and day:
            qs = StaffAttendance.objects.filter(staff=staff, date=day)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Attendance for this staff member already exists for this date.")
        return cleaned


class PerformanceForm(forms.ModelForm):
    class Meta:
        model = PerformanceRecord
        fields = ["staff", "review_date", "score", "strengths", "improvements", "remarks"]
        widgets = {
            "staff": forms.Select(attrs={"class": INPUT}),
            "review_date": forms.DateInput(attrs={"class": INPUT, "type": "date"}),
            "score": forms.NumberInput(attrs={"class": INPUT, "min": 0, "max": 100}),
            "strengths": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
            "improvements": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
            "remarks": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["staff"].queryset = StaffProfile.objects.select_related("user")
