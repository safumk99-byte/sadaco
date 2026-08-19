from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .notification_service import notify_roles


@receiver(post_save, sender="sales.OrderRequest")
def order_request_notification(sender, instance, created, **kwargs):
    if not created:
        return
    notify_roles(
        "New customer request",
        f"{instance.request_no} from {instance.customer.name}.",
        notification_type="order",
        priority="high",
        url=reverse("sales:manager_requests"),
    )


@receiver(post_save, sender="sales.Enquiry")
def enquiry_notification(sender, instance, created, **kwargs):
    if not created:
        return
    notify_roles(
        "New customer enquiry",
        f"{instance.enquiry_no} from {instance.customer.name}.",
        notification_type="enquiry",
        priority="normal",
        url=reverse("sales:enquiries"),
    )


@receiver(post_save, sender="sales.PaymentRecord")
def payment_notification(sender, instance, created, **kwargs):
    if not created:
        return
    notify_roles(
        "Payment recorded",
        f"{instance.order.order_no}: payment of Rs. {instance.amount}.",
        notification_type="payment",
        priority="normal",
        url=reverse("sales:orders"),
    )


@receiver(post_save, sender="products.StockTransaction")
def stock_notification(sender, instance, created, **kwargs):
    if not created:
        return
    product = instance.product
    if product.stock_quantity <= product.low_stock_threshold:
        notify_roles(
            "Low stock alert",
            f"{product.name} has {product.stock_quantity} {product.unit} remaining.",
            notification_type="stock",
            priority="high",
            url=reverse("products:stock"),
        )
