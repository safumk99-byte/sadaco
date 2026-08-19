from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from .forms import CampaignForm, ContentForm, LeadForm
from .models import Campaign, MarketingContent, MarketingLead

manager_required=role_required("super_admin","institution_admin","manager")


@login_required
@manager_required
def dashboard(request):
    return render(request,"marketing/dashboard.html",{
        "title":"Marketing & Business Development",
        "campaigns":Campaign.objects.all()[:30],
        "contents":MarketingContent.objects.select_related("campaign")[:30],
        "lead_rows":MarketingLead.objects.select_related("customer","campaign","enquiry")[:30],
        "active_campaigns":Campaign.objects.filter(status=Campaign.Status.ACTIVE).count(),
        "published":MarketingContent.objects.filter(status=MarketingContent.Status.PUBLISHED).count(),
        "lead_rows":MarketingLead.objects.select_related("customer","campaign","enquiry")[:30],
        "lead_count":MarketingLead.objects.count(),
        "converted":MarketingLead.objects.filter(status=MarketingLead.Status.CONVERTED).count(),
    })


@login_required
@manager_required
def campaign_create(request):
    form=CampaignForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        obj=form.save(commit=False); obj.created_by=request.user; obj.save()
        messages.success(request,"Campaign created.")
        return redirect("marketing:dashboard")
    return render(request,"marketing/form.html",{"title":"Create Campaign","form":form,"back":"marketing:dashboard"})


@login_required
@manager_required
def content_create(request):
    form=ContentForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        obj=form.save(commit=False); obj.created_by=request.user; obj.save()
        messages.success(request,"Marketing content saved.")
        return redirect("marketing:dashboard")
    return render(request,"marketing/form.html",{"title":"Plan Content","form":form,"back":"marketing:dashboard"})


@login_required
@manager_required
def lead_create(request):
    form=LeadForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        obj=form.save(commit=False); obj.created_by=request.user; obj.save()
        messages.success(request,"Marketing lead recorded.")
        return redirect("marketing:dashboard")
    return render(request,"marketing/form.html",{"title":"Record Lead","form":form,"back":"marketing:dashboard"})
