import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from accounts.decorators import api_role_required
from sales.models import Customer, Enquiry
from .models import Campaign, MarketingContent, MarketingLead

manager_required=api_role_required('super_admin','institution_admin','manager')


def _global_admin(user):
    role = getattr(getattr(user, "profile", None), "role", None)
    return user.is_superuser or role in ("super_admin", "institution_admin")


def _department_id(user):
    profile = getattr(user, "profile", None)
    return profile.department_id if profile and profile.role == "manager" else None


def _require_department(user):
    if not _global_admin(user) and not _department_id(user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Assign your manager account to a department first.")


def _campaigns(user):
    qs = Campaign.objects.all()
    if _global_admin(user): return qs
    department_id = _department_id(user)
    return qs.filter(created_by__profile__department_id=department_id) if department_id else qs.none()


def _contents(user):
    qs = MarketingContent.objects.all()
    if _global_admin(user): return qs
    department_id = _department_id(user)
    return (
        qs.filter(created_by__profile__department_id=department_id)
        .filter(Q(campaign__isnull=True) | Q(campaign__in=_campaigns(user)))
        if department_id else qs.none()
    )


def _leads(user):
    qs = MarketingLead.objects.all()
    if _global_admin(user): return qs
    department_id = _department_id(user)
    if not department_id:
        return qs.none()
    # Keep every related record within the manager's department, including legacy rows.
    return qs.filter(
        Q(created_by__profile__department_id=department_id)
        | Q(customer__department_id=department_id)
        | Q(enquiry__customer__department_id=department_id)
    ).filter(
        Q(customer__isnull=True) | Q(customer__department_id=department_id)
    ).filter(
        Q(enquiry__isnull=True) | Q(enquiry__customer__department_id=department_id)
    ).filter(
        Q(campaign__isnull=True) | Q(campaign__in=_campaigns(user))
    ).distinct()


def _customers(user):
    qs = Customer.objects.all()
    if _global_admin(user): return qs
    department_id = _department_id(user)
    return qs.filter(department_id=department_id) if department_id else qs.none()


def _enquiries(user):
    qs = Enquiry.objects.all()
    if _global_admin(user): return qs
    department_id = _department_id(user)
    return qs.filter(customer__department_id=department_id) if department_id else qs.none()

def _date(v): return v.isoformat() if v else ''
def campaign(x): return {'id':x.id,'name':x.name,'channel':x.channel,'target_segment':x.target_segment,'start_date':_date(x.start_date),'end_date':_date(x.end_date),'budget':str(x.budget),'status':x.status,'notes':x.notes}
def content(x): return {'id':x.id,'title':x.title,'channel':x.channel,'campaign_id':x.campaign_id,'campaign':x.campaign.name if x.campaign else '','content_date':_date(x.content_date),'status':x.status,'content_url':x.content_url,'notes':x.notes}
def lead(x): return {'id':x.id,'source':x.source,'customer_id':x.customer_id,'customer':x.customer.name if x.customer else '','enquiry_id':x.enquiry_id,'campaign_id':x.campaign_id,'campaign':x.campaign.name if x.campaign else '','captured_on':_date(x.captured_on),'status':x.status,'notes':x.notes}
@manager_required
@require_GET
def dashboard(request):
    q=request.GET.get('q','').strip()
    cs=_campaigns(request.user)
    ls=_leads(request.user).select_related('customer','campaign')
    contents=_contents(request.user).select_related('campaign')
    if q:
        cs=cs.filter(Q(name__icontains=q)|Q(channel__icontains=q))
        ls=ls.filter(Q(customer__name__icontains=q)|Q(source__icontains=q)|Q(campaign__name__icontains=q))
    return JsonResponse({
        'stats':{
            'active_campaigns':cs.filter(status='active').count(),
            'published':contents.filter(status='published').count(),
            'leads':ls.count(),
            'converted':ls.filter(status='converted').count(),
        },
        'campaigns':[campaign(x) for x in cs[:50]],
        'contents':[content(x) for x in contents[:50]],
        'leads':[lead(x) for x in ls[:50]],
        'options':{
            'customers':list(_customers(request.user).values('id','name')[:300]),
            'enquiries':list(_enquiries(request.user).values('id','enquiry_no')[:300]),
            'campaigns':list(_campaigns(request.user).values('id','name')[:100]),
        }
    })

@manager_required
@require_POST
def campaign_create(request):
    _require_department(request.user)
    d=json.loads(request.body or '{}'); x=Campaign.objects.create(created_by=request.user,**{k:d.get(k) for k in ['name','channel','target_segment','start_date','end_date','budget','status','notes'] if k in d}); return JsonResponse(campaign(x))
@manager_required
@require_POST
def content_create(request):
    _require_department(request.user)
    d=json.loads(request.body or '{}'); campaign_obj=None
    if d.get('campaign_id'):
        campaign_obj=get_object_or_404(_campaigns(request.user),pk=d['campaign_id'])
    x=MarketingContent.objects.create(created_by=request.user, title=d.get('title',''),channel=d.get('channel',''),campaign=campaign_obj,content_date=d.get('content_date') or None,status=d.get('status','idea'),content_url=d.get('content_url',''),notes=d.get('notes','')); return JsonResponse(content(x))
@manager_required
@require_POST
def lead_create(request):
    _require_department(request.user)
    d=json.loads(request.body or '{}')
    customer=get_object_or_404(_customers(request.user),pk=d['customer_id']) if d.get('customer_id') else None
    enquiry=get_object_or_404(_enquiries(request.user),pk=d['enquiry_id']) if d.get('enquiry_id') else None
    campaign_obj=get_object_or_404(_campaigns(request.user),pk=d['campaign_id']) if d.get('campaign_id') else None
    if customer and enquiry and enquiry.customer_id != customer.pk:
        return JsonResponse({'detail':'Selected enquiry belongs to a different customer.'},status=400)
    x=MarketingLead.objects.create(created_by=request.user,source=d.get('source',''),customer=customer,enquiry=enquiry,campaign=campaign_obj,captured_on=d.get('captured_on') or None,status=d.get('status','new'),notes=d.get('notes','')); return JsonResponse(lead(x))
