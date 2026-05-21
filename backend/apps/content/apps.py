from django.apps import AppConfig


class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.content"
    verbose_name = "Content"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from .models import Review
        from .signals import on_review_deleted, on_review_saved

        post_save.connect(
            on_review_saved,
            sender=Review,
            dispatch_uid="content.on_review_saved",
        )
        post_delete.connect(
            on_review_deleted,
            sender=Review,
            dispatch_uid="content.on_review_deleted",
        )
