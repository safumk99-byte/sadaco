from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import AuditEvent, DesignApproval, DesignRevision, Enquiry, FollowUp
from .permissions import has_active_role, is_founder


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


@transaction.atomic
def record_design_approval(*, revision_id, reviewer_type, decision, actor, comments=""):
    """Record customer approval or Manager confirmation for a design revision.

    A staff Manager records the customer's externally obtained decision; the
    Manager's own confirmation is a separate, subsequent approval record.
    """
    revision = DesignRevision.objects.select_for_update().select_related(
        "design_record__sales_order"
    ).get(pk=revision_id)
    division_id = revision.design_record.sales_order.division_id
    if not actor or actor.employment_status != "active":
        raise ValidationError("An active staff member is required to record design approval.")
    if not (is_founder(actor) or has_active_role(actor, "manager", division_id=division_id)):
        raise ValidationError("Only the Manager or Founder can record design approval.")
    if revision.locked_at is not None:
        raise ValidationError("This design revision is already approved and locked.")
    if reviewer_type not in {"customer", "manager"}:
        raise ValidationError({"reviewer_type": "Reviewer type must be customer or manager."})
    if decision not in {"approved", "revision_required"}:
        raise ValidationError({"decision": "Decision must be approved or revision_required."})

    latest_customer_approval = revision.approvals.filter(
        reviewer_type="customer"
    ).order_by("-reviewed_at", "-id").first()
    if reviewer_type == "manager" and decision == "approved":
        if not latest_customer_approval or latest_customer_approval.decision != "approved":
            raise ValidationError(
                "Manager confirmation requires the customer's approval first."
            )

    before = {"status": revision.status, "locked_at": None}
    approval = DesignApproval.objects.create(
        design_revision=revision,
        reviewer_type=reviewer_type,
        decision=decision,
        reviewed_by=actor,
        reviewed_at=timezone.now(),
        comments=comments,
    )
    if decision == "revision_required":
        revision.status = "revision_required"
        revision.save(update_fields=["status", "locked_at", "updated_at"])
    elif reviewer_type == "manager":
        revision.lock_after_approval(approval)
    _audit(
        actor, approval, "design_approval_recorded", {},
        {
            "design_revision_id": str(revision.pk),
            "reviewer_type": reviewer_type,
            "decision": decision,
            "comments": comments,
        },
    )
    _audit(
        actor, revision, "design_revision_status_changed", before,
        {"status": revision.status, "locked_at": revision.locked_at.isoformat() if revision.locked_at else None},
        reason=f"{reviewer_type} decision: {decision}",
    )
    return approval
