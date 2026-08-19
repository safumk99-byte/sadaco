from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Notification, UserProfile
from sales.models import CustomerFeedback, DeliveryRecord, SalesOrder
from .forms import DeliveryForm, FeedbackForm

manager_required=role_required("super_admin","institution_admin","manager")


def _notify(title,message,url):
    for profile in UserProfile.objects.filter(
        role__in=[UserProfile.Role.SUPER_ADMIN,UserProfile.Role.INSTITUTION_ADMIN,UserProfile.Role.MANAGER],
        is_active=True,
    ):
        Notification.objects.create(
            user=profile.user,
            notification_type=Notification.Type.ORDER,
            priority=Notification.Priority.NORMAL,
            title=title,message=message,url=url,
        )


@login_required
@manager_required
def dashboard(request):
    q=request.GET.get("q","").strip()
    deliveries=DeliveryRecord.objects.select_related("order__customer").all()
    if q:
        deliveries=deliveries.filter(
            Q(order__order_no__icontains=q)|Q(order__customer__name__icontains=q)
        )
    return render(request,"delivery/dashboard.html",{
        "title":"Delivery & Installation",
        "deliveries":deliveries[:80],
        "pending":DeliveryRecord.objects.filter(status=DeliveryRecord.Status.PENDING).count(),
        "scheduled":DeliveryRecord.objects.filter(status=DeliveryRecord.Status.SCHEDULED).count(),
        "out":DeliveryRecord.objects.filter(status=DeliveryRecord.Status.OUT).count(),
        "delivered":DeliveryRecord.objects.filter(status__in=[DeliveryRecord.Status.DELIVERED,DeliveryRecord.Status.INSTALLED]).count(),
        "installations":DeliveryRecord.objects.filter(installation_required=True,status__in=[DeliveryRecord.Status.SCHEDULED,DeliveryRecord.Status.OUT]).count(),
        "query":q,
    })


@login_required
@manager_required
def delivery_detail(request,pk):
    order=get_object_or_404(SalesOrder.objects.select_related("customer"),pk=pk)
    delivery,created=DeliveryRecord.objects.get_or_create(order=order)
    feedback=CustomerFeedback.objects.filter(order=order).first()
    return render(request,"delivery/detail.html",{
        "title":f"Delivery · {order.order_no}",
        "order":order,"delivery":delivery,"feedback":feedback,
    })


@login_required
@manager_required
def delivery_update(request,pk):
    order=get_object_or_404(SalesOrder,pk=pk)
    delivery,_=DeliveryRecord.objects.get_or_create(order=order)
    old=delivery.status
    form=DeliveryForm(request.POST or None,instance=delivery)
    if request.method=="POST" and form.is_valid():
        delivery=form.save()
        if delivery.status in [DeliveryRecord.Status.DELIVERED,DeliveryRecord.Status.INSTALLED]:
            order.status=SalesOrder.Status.DELIVERED
            order.save(update_fields=["status","updated_at"])
        _notify(
            "Delivery status updated",
            f"{order.order_no}: {delivery.get_status_display()}",
            f"/delivery/orders/{order.pk}/",
        )
        messages.success(request,"Delivery details updated.")
        return redirect("delivery:detail",pk=order.pk)
    return render(request,"delivery/form.html",{"title":f"Delivery · {order.order_no}","form":form,"order":order,"delivery":delivery})


@login_required
@manager_required
def feedback_create(request,pk):
    order=get_object_or_404(SalesOrder,pk=pk)
    feedback=CustomerFeedback.objects.filter(order=order).first()
    form=FeedbackForm(request.POST or None,instance=feedback)
    if request.method=="POST" and form.is_valid():
        obj=form.save(commit=False)
        obj.order=order
        obj.save()
        messages.success(request,"Customer feedback saved.")
        return redirect("delivery:detail",pk=order.pk)
    return render(request,"delivery/feedback.html",{"title":f"Feedback · {order.order_no}","form":form,"order":order})
