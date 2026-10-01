from datetime import date,timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import F,Sum,Count
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from accounts.decorators import role_required
from products.models import Product,StockTransaction
from sales.models import Customer,Enquiry,Quotation,SalesOrder,PaymentRecord,DeliveryRecord
from staff.models import StaffProfile,StaffAttendance,StaffTask
from purchase.models import PurchaseOrder
from finance.models import Expense
from marketing.models import Campaign,MarketingLead

def money(v): return v or Decimal('0')
def rng(request):
    today=date.today(); s=request.GET.get('start'); e=request.GET.get('end')
    try: s=date.fromisoformat(s) if s else today-timedelta(days=29)
    except: s=today-timedelta(days=29)
    try: e=date.fromisoformat(e) if e else today
    except: e=today
    return (e,s) if s>e else (s,e)
@login_required
@role_required('super_admin','institution_admin','manager')
@require_GET
def dashboard(request):
    start,end=rng(request); orders=SalesOrder.objects.filter(created_at__date__range=(start,end)); payments=PaymentRecord.objects.filter(created_at__date__range=(start,end),status__in=['received','verified']); stock=StockTransaction.objects.filter(created_at__date__range=(start,end));
    stats={'orders':orders.exclude(status='cancelled').count(),'order_revenue':str(money(orders.exclude(status='cancelled').aggregate(x=Sum('confirmed_price'))['x'])),'payments':str(money(payments.aggregate(x=Sum('amount'))['x'])),'enquiries':Enquiry.objects.filter(created_at__date__range=(start,end)).count(),'quotations':Quotation.objects.filter(created_at__date__range=(start,end)).count(),'customers':Customer.objects.filter(created_at__date__range=(start,end)).count(),'stock_in':str(money(stock.filter(transaction_type='in').aggregate(x=Sum('quantity'))['x'])),'stock_out':str(money(stock.filter(transaction_type='out').aggregate(x=Sum('quantity'))['x'])),'active_staff':StaffProfile.objects.filter(status='active').count(),'present':StaffAttendance.objects.filter(date__range=(start,end),status='present').count(),'absent':StaffAttendance.objects.filter(date__range=(start,end),status='absent').count(),'leave':StaffAttendance.objects.filter(date__range=(start,end),status='leave').count(),'overdue':StaffTask.objects.filter(due_date__lt=end).exclude(status__in=['completed','cancelled']).count(),'low_stock':Product.objects.filter(status='active',stock_quantity__lte=F('low_stock_threshold')).count(),'purchase_open':PurchaseOrder.objects.filter(status__in=['sent','partial']).count(),'purchase_value':str(money(PurchaseOrder.objects.exclude(status='cancelled').aggregate(x=Sum('total'))['x'])),'paid_expenses':str(money(Expense.objects.filter(status='paid',expense_date__range=(start,end)).aggregate(x=Sum('amount'))['x'])),'delivery_pending':DeliveryRecord.objects.filter(status__in=['pending','scheduled','ready','out']).count(),'active_campaigns':Campaign.objects.filter(status='active').count(),'open_leads':MarketingLead.objects.filter(status__in=['new','contacted']).count()}
    return JsonResponse({'start':str(start),'end':str(end),'stats':stats,'order_status':list(orders.values('status').annotate(total=Count('id')).order_by('-total')),'enquiry_status':list(Enquiry.objects.filter(created_at__date__range=(start,end)).values('status').annotate(total=Count('id')).order_by('-total')),'top_products':list(Product.objects.filter(status='active').order_by('-stock_quantity')[:5].values('name','sku','stock_quantity','selling_price'))})
