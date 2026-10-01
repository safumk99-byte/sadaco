import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from accounts.decorators import api_role_required
from sales.models import Customer, Enquiry
from .models import Campaign, MarketingContent, MarketingLead
manager_required=api_role_required('super_admin','institution_admin','manager')
def _date(v): return v.isoformat() if v else ''
def campaign(x): return {'id':x.id,'name':x.name,'channel':x.channel,'target_segment':x.target_segment,'start_date':_date(x.start_date),'end_date':_date(x.end_date),'budget':str(x.budget),'status':x.status,'notes':x.notes}
def content(x): return {'id':x.id,'title':x.title,'channel':x.channel,'campaign_id':x.campaign_id,'campaign':x.campaign.name if x.campaign else '','content_date':_date(x.content_date),'status':x.status,'content_url':x.content_url,'notes':x.notes}
def lead(x): return {'id':x.id,'source':x.source,'customer_id':x.customer_id,'customer':x.customer.name if x.customer else '','enquiry_id':x.enquiry_id,'campaign_id':x.campaign_id,'campaign':x.campaign.name if x.campaign else '','captured_on':_date(x.captured_on),'status':x.status,'notes':x.notes}
@manager_required
@require_GET
def dashboard(request):
    q=request.GET.get('q','').strip(); cs=Campaign.objects.all(); ls=MarketingLead.objects.select_related('customer','campaign')
    if q: cs=cs.filter(Q(name__icontains=q)|Q(channel__icontains=q)); ls=ls.filter(Q(customer__name__icontains=q)|Q(source__icontains=q)|Q(campaign__name__icontains=q))
    return JsonResponse({'stats':{'active_campaigns':Campaign.objects.filter(status='active').count(),'published':MarketingContent.objects.filter(status='published').count(),'leads':MarketingLead.objects.count(),'converted':MarketingLead.objects.filter(status='converted').count()},'campaigns':[campaign(x) for x in cs[:50]],'contents':[content(x) for x in MarketingContent.objects.select_related('campaign')[:50]],'leads':[lead(x) for x in ls[:50]],'options':{'customers':list(Customer.objects.values('id','name')[:300]),'enquiries':list(Enquiry.objects.values('id','enquiry_no')[:300]),'campaigns':list(Campaign.objects.values('id','name')[:100])}})
@manager_required
@require_POST
def campaign_create(request):
    d=json.loads(request.body or '{}'); x=Campaign.objects.create(created_by=request.user,**{k:d.get(k) for k in ['name','channel','target_segment','start_date','end_date','budget','status','notes'] if k in d}); return JsonResponse(campaign(x))
@manager_required
@require_POST
def content_create(request):
    d=json.loads(request.body or '{}'); x=MarketingContent.objects.create(created_by=request.user, title=d.get('title',''),channel=d.get('channel',''),campaign_id=d.get('campaign_id') or None,content_date=d.get('content_date') or None,status=d.get('status','idea'),content_url=d.get('content_url',''),notes=d.get('notes','')); return JsonResponse(content(x))
@manager_required
@require_POST
def lead_create(request):
    d=json.loads(request.body or '{}'); x=MarketingLead.objects.create(created_by=request.user,source=d.get('source',''),customer_id=d.get('customer_id') or None,enquiry_id=d.get('enquiry_id') or None,campaign_id=d.get('campaign_id') or None,captured_on=d.get('captured_on') or None,status=d.get('status','new'),notes=d.get('notes','')); return JsonResponse(lead(x))
