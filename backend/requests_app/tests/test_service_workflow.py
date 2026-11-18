
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from ..models import Category, ServiceRequest, WorkOrder
from ..services import service_request_create


User = get_user_model()


class ServiceWorkflowTests(TestCase):

    def setUp(self):
        self.requester = User.objects.create_user(
            username="requester_test",
            password="TestPass123!"
        )

        self.technician = User.objects.create_user(
            username="technician_test",
            password="TestPass123!",
            is_staff=True
        )

        self.staff = User.objects.create_user(
            username="staff_test",
            password="TestPass123!",
            is_staff=True
        )

        self.category = Category.objects.create(
            name="ICT Support",
            description="Technical support",
            is_active=True
        )

        self.item = service_request_create(
            requester=self.requester,
            category=self.category,
            title="Laptop is not starting",
            description="My laptop will not start.",
            location="Computer Lab",
            priority=3
        )

    def test_non_staff_cannot_assign_technician(self):
        self.client.login(
            username="requester_test",
            password="TestPass123!"
        )

        response = self.client.post(
            reverse(
                "requests:assign",
                kwargs={"request_id": self.item.id}
            ),
            {"technician": self.technician.id}
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            WorkOrder.objects.filter(
                service_request=self.item
            ).exists()
        )

    def test_staff_can_assign_technician(self):
        self.client.login(
            username="staff_test",
            password="TestPass123!"
        )

        response = self.client.post(
            reverse(
                "requests:assign",
                kwargs={"request_id": self.item.id}
            ),
            {"technician": self.technician.id}
        )

        self.assertRedirects(
            response,
            reverse(
                "requests:detail",
                kwargs={"request_id": self.item.id}
            )
        )

        self.item.refresh_from_db()

        self.assertEqual(
            self.item.status,
            ServiceRequest.Status.ASSIGNED
        )

        self.assertTrue(
            WorkOrder.objects.filter(
                service_request=self.item,
                technician=self.technician
            ).exists()
        )

    def test_request_cannot_be_resolved_without_assignment(self):
        self.client.login(
            username="staff_test",
            password="TestPass123!"
        )

        response = self.client.post(
            reverse(
                "requests:resolve",
                kwargs={"request_id": self.item.id}
            ),
            {"work_notes": "Problem fixed successfully"}
        )

        self.assertRedirects(
            response,
            reverse(
                "requests:detail",
                kwargs={"request_id": self.item.id}
            )
        )

        self.item.refresh_from_db()

        self.assertEqual(
            self.item.status,
            ServiceRequest.Status.OPEN
        )
        self.assertIsNone(self.item.resolved_at)
        self.assertFalse(
            WorkOrder.objects.filter(
                service_request=self.item
            ).exists()
        )

    def test_assigned_technician_can_resolve_request(self):
        WorkOrder.objects.create(
            service_request=self.item,
            technician=self.technician
        )

        self.item.status = ServiceRequest.Status.ASSIGNED
        self.item.save()

        self.client.login(
            username="technician_test",
            password="TestPass123!"
        )

        response = self.client.post(
            reverse(
                "requests:resolve",
                kwargs={"request_id": self.item.id}
            ),
            {"work_notes": "Laptop repaired successfully"}
        )

        self.assertRedirects(
            response,
            reverse(
                "requests:detail",
                kwargs={"request_id": self.item.id}
            )
        )

        self.item.refresh_from_db()
        work_order = WorkOrder.objects.get(
            service_request=self.item
        )

        self.assertEqual(
            self.item.status,
            ServiceRequest.Status.RESOLVED
        )
        self.assertIsNotNone(self.item.resolved_at)
        self.assertEqual(
            self.item.resolution_summary,
            "Laptop repaired successfully"
        )
        self.assertIsNotNone(work_order.completed_at)
        self.assertEqual(
            work_order.work_notes,
            "Laptop repaired successfully"
        )

    def test_pagination_preserves_search_and_status_filters(self):
        for number in range(11):
            service_request_create(
                requester=self.requester,
                category=self.category,
                title=f"Laptop issue number {number}",
                description="Laptop needs attention.",
                location="Computer Lab",
                priority=3
            )

        self.client.login(
            username="requester_test",
            password="TestPass123!"
        )

        response = self.client.get(
            reverse("requests:list"),
            {
                "q": "Laptop",
                "status": ServiceRequest.Status.OPEN,
                "page": 1
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
    'href="?q=Laptop&status=open&page=2"',
    response.content.decode()
)
