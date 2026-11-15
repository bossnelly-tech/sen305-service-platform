from django.contrib import admin
from django.db.models import Q
from django.utils import timezone

from .models import Category, ServiceRequest, WorkOrder, Comment


class OverdueFilter(admin.SimpleListFilter):
    title = "overdue"
    parameter_name = "overdue"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Overdue"),
            ("no", "Not overdue"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()

        active_requests = queryset.exclude(
            status__in=[
                ServiceRequest.Status.RESOLVED,
                ServiceRequest.Status.CLOSED,
            ]
        )

        if self.value() == "yes":
            return active_requests.filter(due_at__lt=now)

        if self.value() == "no":
            return active_requests.filter(
                Q(due_at__gte=now) | Q(due_at__isnull=True)
            )

        return queryset


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "requester",
        "category",
        "priority",
        "status",
        "due_at",
        "resolution_summary",
        "created_at",
    )
    search_fields = (
        "title",
        "description",
        "location",
        "resolution_summary",
    )
    list_filter = ("status", "priority", "category", OverdueFilter)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("service_request", "technician", "started_at", "completed_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("service_request", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)
    search_fields = ("body",)