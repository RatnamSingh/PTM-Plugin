from django.test import TestCase
from unittest.mock import patch, MagicMock
from ninja.testing import TestClient
from .models import Client, PTMEvent, PTMSlot, PTMBooking
from .api import api
import jwt
import datetime
from django.core.cache import cache

class PTMPluginTestCase(TestCase):
    def setUp(self):
        self.client_model = Client.objects.create(
            tenant_id="test_tenant",
            name="Test ERP",
            api_key="test_api_key_123"
        )
        # We must clear cache since some endpoints cache responses
        cache.clear()
        # Create an APIKeyAuth mock role for server endpoints
        self.server_headers = {"Authorization": f"Bearer {self.client_model.api_key}"}

    def generate_jwt(self, role="PARENT", user_id="parent_1"):
        payload = {
            "tenant_id": self.client_model.tenant_id,
            "role": role,
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        return jwt.encode(payload, self.client_model.api_key, algorithm="HS256")

    def test_api_key_auth(self):
        # Without API Key
        response = TestClient(api).patch("/webhooks", json={"webhook_url": "https://test.com"})
        self.assertEqual(response.status_code, 401)
        
        # With valid API Key
        response = TestClient(api).patch("/webhooks", json={"webhook_url": "https://test.com"}, headers=self.server_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["webhook_url"], "https://test.com")
        
    def test_jwt_auth_failure(self):
        # Fake JWT with wrong key
        payload = {"tenant_id": self.client_model.tenant_id, "role": "PARENT"}
        fake_token = jwt.encode(payload, "wrong_key", algorithm="HS256")
        
        PTMEvent.objects.create(
            title="Test", date="2026-10-10", start_time="09:00", end_time="10:00",
            slot_duration_minutes=15, gap_duration_minutes=5, mode="IN_PERSON",
            is_published=True, tenant_id=self.client_model.tenant_id
        )
        
        headers = {"Authorization": f"Bearer {fake_token}"}
        response = TestClient(api).get("/events", headers=headers)
        self.assertEqual(response.status_code, 401)
        
    def test_event_and_slot_generation(self):
        payload = {
            "title": "Fall PTM",
            "date": "2026-11-01",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "slot_duration_minutes": 15,
            "gap_duration_minutes": 5,
            "mode": "VIRTUAL"
        }
        
        response = TestClient(api).post("/events", json=payload, headers=self.server_headers)
        self.assertEqual(response.status_code, 200)
        
        # Should generate slots. 09:00-09:15, 09:20-09:35, 09:40-09:55
        # 3 slots per teacher. 4 mock teachers = 12 slots.
        self.assertEqual(PTMSlot.objects.count(), 12)
        
    @patch('ptm.api.DYTE_ORG_ID', 'mock_org')
    @patch('ptm.api.DYTE_API_KEY', 'mock_key')
    @patch('ptm.api.create_dyte_meeting')
    @patch('ptm.api.send_booking_confirmation_sms.delay')
    @patch('ptm.api.send_booking_confirmation_email.delay')
    def test_booking_logic(self, mock_email, mock_sms, mock_dyte):
        mock_dyte.return_value = "mock_dyte_id_123"
        
        event = PTMEvent.objects.create(
            title="Test", date="2026-10-10", start_time="09:00", end_time="10:00",
            slot_duration_minutes=15, gap_duration_minutes=5, mode="VIRTUAL",
            is_published=True, tenant_id=self.client_model.tenant_id
        )
        slot = PTMSlot.objects.create(
            event=event, teacher_id="Teacher A", start_time="09:00", end_time="09:15",
            tenant_id=self.client_model.tenant_id
        )
        
        token = self.generate_jwt(role="PARENT", user_id="parent_1")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = TestClient(api).post("/bookings", json={"slot_id": str(slot.id)}, headers=headers)
        self.assertEqual(response.status_code, 200)
        
        slot.refresh_from_db()
        self.assertTrue(slot.is_booked)
        self.assertEqual(slot.dyte_meeting_id, "mock_dyte_id_123")
        
        mock_sms.assert_called_once()
        mock_email.assert_called_once()
        
        # Prevent double booking
        token2 = self.generate_jwt(role="PARENT", user_id="parent_2")
        headers2 = {"Authorization": f"Bearer {token2}"}
        response2 = TestClient(api).post("/bookings", json={"slot_id": str(slot.id)}, headers=headers2)
        self.assertEqual(response2.status_code, 400)
        
    @patch('ptm.api.dispatch_webhook.delay')
    def test_webhook_dispatch_on_update(self, mock_webhook):
        event = PTMEvent.objects.create(
            title="Test", date="2026-10-10", start_time="09:00", end_time="10:00",
            slot_duration_minutes=15, gap_duration_minutes=5, mode="IN_PERSON",
            is_published=True, tenant_id=self.client_model.tenant_id
        )
        slot = PTMSlot.objects.create(
            event=event, teacher_id="Teacher A", start_time="09:00", end_time="09:15",
            tenant_id=self.client_model.tenant_id
        )
        booking = PTMBooking.objects.create(
            slot=slot, student_id="student_1", parent_id="parent_1", tenant_id=self.client_model.tenant_id
        )
        
        token = self.generate_jwt(role="TEACHER", user_id="Teacher A")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = TestClient(api).patch(f"/bookings/{booking.id}", json={"status": "COMPLETED"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, "COMPLETED")
        
        mock_webhook.assert_called_once()

    @patch('requests.post')
    def test_webhook_task_signature(self, mock_post):
        from .tasks import dispatch_webhook
        self.client_model.webhook_url = "https://mock.com"
        self.client_model.save()
        
        dispatch_webhook("test_tenant", "test.event", {"hello": "world"})
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://mock.com")
        self.assertIn("X-PTM-Signature", kwargs["headers"])
        self.assertEqual(kwargs["json"]["event_type"], "test.event")
