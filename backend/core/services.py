from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import AuditEvent, Enquiry, FollowUp


ENQUIRY_TRANSITIONS = {
    Enquiry.Status.NEW: {Enquiry.Status.CONTACTED, Enquiry.Status.LOST},
    Enquiry.Status.CONTACTED: {
        Enquiry.Status.QUOTATION_SENT, Enquiry.Status.FOLLOW_UP,
        Enquiry.Status.CONFIRMED, Enquiry.Status.LOST,
    },
    Enquiry.Status.QUOTATION_SENT: {
        Enquiry.Status.FOLLOW_UP, Enquiry.Status.CONFIRMED, Enquiry.Status.LOST,
    },
    Enquiry.Status.FOLLOW_UP: {
        Enquiry.Status.CONTACTED, Enquiry.Status.QUOTATION_SENT,
        Enquiry.Status.CONFIRMED, Enquiry.Status.LOST,
    },
    Enquiry.Status.CONFIRMED: set(),
    Enquiry.Status.LOST: set(),
}


def _audit(actor, entity, action, before, after, reason=""):
    AuditEvent.objects.create(
        actor=actor,
        entity_type=entity.__class__.__name__,
        entity_id=entity.pk,
        action=action,
        before_data=before,
        after_data=after,
        reason=reason,
    )


@transaction.atomic
def transition_enquiry(*, enquiry_id, target_status, actor, reason=""):
    enquiry = Enquiry.objects.select_for_update().get(pk=enquiry_id)
    if target_status not in Enquiry.Status.values:
        raise ValidationError({"status": "Unknown enquiry status."})
    allowed = ENQUIRY_TRANSITIONS.get(enquiry.status, set())
    if target_status not in allowed:
        raise ValidationError({
            "status": f"Transition from '{enquiry.status}' to '{target_status}' is not allowed."
        })
    before = {"status": enquiry.status}
    enquiry.status = target_status
    enquiry.save(update_fields=["status", "updated_at"])
    _audit(actor, enquiry, "status_changed", before, {"status": target_status}, reason)
    return enquiry


@transaction.atomic
def complete_follow_up(*, follow_up_id, actor, note=None):
    follow_up = FollowUp.objects.select_for_update().get(pk=follow_up_id)
    if follow_up.status != FollowUp.Status.OPEN:
        raise ValidationError({"status": "Only open follow-ups can be completed."})
    before = {"status": follow_up.status, "completed_at": None}
    follow_up.status = FollowUp.Status.COMPLETED
    follow_up.completed_at = timezone.now()
    if note is not None:
        follow_up.note = note
    follow_up.save(update_fields=["status", "completed_at", "note", "updated_at"])
    _audit(
        actor, follow_up, "completed", before,
        {"status": follow_up.status, "completed_at": follow_up.completed_at.isoformat()},
    )
    return follow_up
