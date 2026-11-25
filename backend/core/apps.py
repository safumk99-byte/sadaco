from django.apps import AppConfig
from django.db.models.signals import m2m_changed


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from .models import DesignRevision, protect_locked_revision_file_attachments

        m2m_changed.connect(
            protect_locked_revision_file_attachments,
            sender=DesignRevision.files.through,
            dispatch_uid="core.protect_locked_revision_file_attachments",
        )
