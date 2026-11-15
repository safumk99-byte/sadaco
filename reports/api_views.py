from datetime import date,timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from accounts.models import UserProfile
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
def _global_admin(user):
    profile = getattr(user, "profile", None)
    return user.is_superuser or bool(
        profile and profile.is_active and profile.role in (UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN)
    )


def _department_id(user):
    profile = getattr(user, "profile", None)
    return profile.department_id if profile and profile.role == UserProfile.Role.MANAGER else None


def _department_leads(user):
    qs = MarketingLead.objects.all()
    if _global_admin(user):
        return qs
    department_id = _department_id(user)
    if not department_id:
        return qs.none()
    return qs.filter(
        Q(created_by__profile__department_id=department_id)
        | Q(customer__department_id=department_id)
        | Q(enquiry__customer__department_id=department_id)
    ).filter(
        Q(customer__isnull=True) | Q(customer__department_id=department_id)
    ).filter(
        Q(enquiry__isnull=True) | Q(enquiry__customer__department_id=department_id)
    ).filter(
        Q(campaign__isnull=True)
        | Q(campaign__created_by__profile__department_id=department_id)
    ).distinct()


def rng(request):
    today=timezone.localdate(); s=request.GET.get('start'); e=request.GET.get('end')
    try: s=date.fromisoformat(s) if s else today-timedelta(days=29)
    except: s=today-timedelta(days=29)
    try: e=date.fromisoformat(e) if e else today
    except: e=today
    return (e,s) if s>e else (s,e)
@login_required
@role_required('super_admin','institution_admin','manager')
@require_GET
def dashboard(request):
    start,end=rng(request)
    all_orders=SalesOrder.objects.all()
    orders=all_orders.filter(created_at__date__range=(start,end))
    enquiries=Enquiry.objects.filter(created_at__date__range=(start,end))
    quotations=Quotation.objects.filter(created_at__date__range=(start,end))
    customers=Customer.objects.filter(created_at__date__range=(start,end))
    staff=StaffProfile.objects.all()
    attendance=StaffAttendance.objects.filter(date__range=(start,end))
    tasks=StaffTask.objects.all()
    purchase_orders=PurchaseOrder.objects.all()
    expenses=Expense.objects.all()
    campaigns=Campaign.objects.all()
    leads=_department_leads(request.user)
    stock=StockTransaction.objects.filter(created_at__date__range=(start,end))
    if not _global_admin(request.user):
        department_id=_department_id(request.user)
        if not department_id:
            all_orders=all_orders.none(); orders=orders.none(); enquiries=enquiries.none(); quotations=quotations.none(); customers=customers.none()
            staff=staff.none(); attendance=attendance.none(); tasks=tasks.none(); purchase_orders=purchase_orders.none()
            expenses=expenses.none(); campaigns=campaigns.none(); leads=leads.none(); stock=stock.none()
        else:
            all_orders=all_orders.filter(customer__department_id=department_id)
            orders=orders.filter(customer__department_id=department_id)
            enquiries=enquiries.filter(customer__department_id=department_id)
            quotations=quotations.filter(customer__department_id=department_id)
            customers=customers.filter(department_id=department_id)
            staff=staff.filter(department_id=department_id)
            attendance=attendance.filter(staff__department_id=department_id)
            tasks=tasks.filter(assigned_to__department_id=department_id)
            purchase_orders=purchase_orders.filter(created_by__profile__department_id=department_id)
            expenses=expenses.filter(created_by__profile__department_id=department_id)
            campaigns=campaigns.filter(created_by__profile__department_id=department_id)
            stock=stock.filter(created_by__profile__department_id=department_id)

    payments=PaymentRecord.objects.filter(created_at__date__range=(start,end),status__in=['received','verified'],order__in=all_orders)
    stats={
        'orders':orders.exclude(status='cancelled').count(),
        'order_revenue':str(money(orders.exclude(status='cancelled').aggregate(x=Sum('confirmed_price'))['x'])),
        'payments':str(money(payments.aggregate(x=Sum('amount'))['x'])),
        'enquiries':enquiries.count(),
        'quotations':quotations.count(),
        'customers':customers.count(),
        'stock_in':str(money(stock.filter(transaction_type='in').aggregate(x=Sum('quantity'))['x'])),
        'stock_out':str(money(stock.filter(transaction_type='out').aggregate(x=Sum('quantity'))['x'])),
        'active_staff':staff.filter(status='active').count(),
        'present':attendance.filter(status='present').count(),
        'absent':attendance.filter(status='absent').count(),
        'leave':attendance.filter(status='leave').count(),
        'overdue':tasks.filter(due_date__lt=end).exclude(status__in=['completed','cancelled']).count(),
        'low_stock':Product.objects.filter(status='active',stock_quantity__lte=F('low_stock_threshold')).count(),
        'purchase_open':purchase_orders.filter(status__in=['sent','partial']).count(),
        'purchase_value':str(money(purchase_orders.exclude(status='cancelled').aggregate(x=Sum('total'))['x'])),
        'paid_expenses':str(money(expenses.filter(status='paid',expense_date__range=(start,end)).aggregate(x=Sum('amount'))['x'])),
        'delivery_pending':DeliveryRecord.objects.filter(order__in=all_orders,status__in=['pending','scheduled','ready','out']).count(),
        'active_campaigns':campaigns.filter(status='active').count(),
        'open_leads':leads.filter(status__in=['new','contacted']).count(),
    }
    return JsonResponse({
        'start':str(start),'end':str(end),'stats':stats,
        'order_status':list(orders.values('status').annotate(total=Count('id')).order_by('-total')),
        'enquiry_status':list(enquiries.values('status').annotate(total=Count('id')).order_by('-total')),
        'top_products':list(Product.objects.filter(status='active').order_by('-stock_quantity')[:5].values('name','sku','stock_quantity','selling_price')),
        'inventory_scope':'shared_catalog',
    })
