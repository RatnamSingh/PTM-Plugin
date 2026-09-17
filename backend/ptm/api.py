from typing import List
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.security import HttpBearer
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import PTMEvent, PTMSlot, PTMBooking, Client
from .tasks import send_booking_confirmation_sms, send_booking_confirmation_email, dispatch_webhook
import datetime
import jwt
import uuid
from uuid import UUID
import os
import requests
from django.core.cache import cache

api = NinjaAPI()

DYTE_ORG_ID = os.environ.get('DYTE_ORG_ID', '')
DYTE_API_KEY = os.environ.get('DYTE_API_KEY', '')

# --- Dyte Helpers ---
def create_dyte_meeting(title):
    url = "https://api.cluster.dyte.in/v2/meetings"
    payload = {"title": title, "record_on_start": False}
    response = requests.post(url, json=payload, auth=(DYTE_ORG_ID, DYTE_API_KEY))
    if response.status_code == 201:
        return response.json()['data']['id']
    return None

def add_dyte_participant(meeting_id, name, preset_name):
    url = f"https://api.cluster.dyte.in/v2/meetings/{meeting_id}/participants"
    payload = {
        "name": name,
        "preset_name": preset_name,
        "custom_participant_id": str(uuid.uuid4())
    }
    response = requests.post(url, json=payload, auth=(DYTE_ORG_ID, DYTE_API_KEY))
    if response.status_code == 201:
        return response.json()['data']['token']
    return None

# --- API Key & JWT Authentication Setup ---
class APIKeyAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            client = Client.objects.get(api_key=token)
            return {"tenant_id": client.tenant_id, "role": "ADMIN", "client": client}
        except Client.DoesNotExist:
            return None

class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            tenant_id = unverified_payload.get('tenant_id')
            if not tenant_id:
                return None
            client = Client.objects.get(tenant_id=tenant_id)
            payload = jwt.decode(token, client.api_key, algorithms=['HS256'])
            payload['client'] = client
            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Client.DoesNotExist):
            return None

# --- Schemas ---
class EventSchema(Schema):
    id: UUID
    title: str
    date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    mode: str
    slot_duration_minutes: int = 15
    gap_duration_minutes: int = 5

class EventCreateSchema(Schema):
    title: str
    date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    slot_duration_minutes: int
    gap_duration_minutes: int
    mode: str

class SlotSchema(Schema):
    id: UUID
    teacher_id: str
    start_time: datetime.time
    end_time: datetime.time
    is_booked: bool

class BookingInSchema(Schema):
    slot_id: UUID
    parent_pre_query: str = None

class BookingOutSchema(Schema):
    id: UUID
    status: str
    message: str = "Booking successful"

from typing import List, Optional

class TeacherScheduleSchema(Schema):
    id: UUID
    start_time: datetime.time
    end_time: datetime.time
    is_booked: bool
    meeting_link: Optional[str] = None
    student_id: Optional[str] = None
    parent_pre_query: Optional[str] = None
    booking_id: Optional[UUID] = None
    status: Optional[str] = None
    teacher_remarks: Optional[str] = None

class BookingUpdateSchema(Schema):
    status: Optional[str] = None
    teacher_remarks: Optional[str] = None

class ParentBookingSchema(Schema):
    id: UUID
    slot_id: UUID
    teacher_id: str
    event_title: str
    start_time: datetime.time
    end_time: datetime.time
    date: datetime.date
    mode: str
    status: str
    meeting_link: Optional[str] = None
    teacher_remarks: Optional[str] = None
    parent_pre_query: Optional[str] = None

class MockLoginSchema(Schema):
    role: str # e.g. "PARENT", "TEACHER", "ADMIN"
    user_id: str # The ERP user ID
    tenant_id: str # The school ID

# --- Protected API Endpoints ---
@api.get("/events", response=List[EventSchema], auth=JWTAuth())
def list_events(request):
    auth_payload = request.auth
    tenant_id = auth_payload['tenant_id']
    
    cache_key = f"events_{tenant_id}"
    cached_events = cache.get(cache_key)
    if cached_events is not None:
        return cached_events
        
    events = list(PTMEvent.objects.filter(is_published=True, tenant_id=tenant_id))
    cache.set(cache_key, events, 60) # Cache for 60 seconds
    return events

@api.post("/events", response=EventSchema, auth=APIKeyAuth())
def create_event(request, payload: EventCreateSchema):
    auth_payload = request.auth
    if auth_payload['role'] != 'ADMIN':
        raise HttpError(403, "Only admins can create events")
        
    tenant_id = auth_payload['tenant_id']
    
    event = PTMEvent.objects.create(
        title=payload.title,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        slot_duration_minutes=payload.slot_duration_minutes,
        gap_duration_minutes=payload.gap_duration_minutes,
        mode=payload.mode,
        is_published=True,
        tenant_id=tenant_id
    )
    
    # Generate Slots for all teachers (Mocked list of teachers for the school)
    teachers = ["Mrs. Davis (Math)", "Mr. Smith (Science)", "Ms. Johnson (English)", "Mr. Brown (History)"]
    
    dt_start = datetime.datetime.combine(payload.date, payload.start_time)
    dt_end = datetime.datetime.combine(payload.date, payload.end_time)
    
    slots_to_create = []
    
    current_time = dt_start
    while current_time + datetime.timedelta(minutes=payload.slot_duration_minutes) <= dt_end:
        slot_end = current_time + datetime.timedelta(minutes=payload.slot_duration_minutes)
        
        for teacher in teachers:
            slots_to_create.append(PTMSlot(
                event=event,
                teacher_id=teacher,
                start_time=current_time.time(),
                end_time=slot_end.time(),
                tenant_id=tenant_id
            ))
            
        current_time = slot_end + datetime.timedelta(minutes=payload.gap_duration_minutes)
        
    PTMSlot.objects.bulk_create(slots_to_create)
    
    # Invalidate cache
    cache.delete(f"events_{tenant_id}")
    
    return event

@api.get("/events/{event_id}/slots", response=List[SlotSchema], auth=JWTAuth())
def list_slots(request, event_id: UUID, teacher_id: str = None):
    auth_payload = request.auth
    # Ensure they can only see slots for their tenant
    slots = PTMSlot.objects.filter(event_id=event_id, tenant_id=auth_payload['tenant_id'])
    if teacher_id:
        slots = slots.filter(teacher_id=teacher_id)
    return slots

@api.post("/bookings", response=BookingOutSchema, auth=JWTAuth())
def create_booking(request, payload: BookingInSchema):
    auth_payload = request.auth
    
    if auth_payload['role'] != 'PARENT':
        raise HttpError(403, "Only parents can book slots")
        
    slot = get_object_or_404(PTMSlot, id=payload.slot_id, tenant_id=auth_payload['tenant_id'])
    
    if slot.is_booked:
        raise HttpError(400, "Slot is already booked")
        
    booking = PTMBooking.objects.create(
        slot=slot,
        student_id=auth_payload['user_id'], # We assume user_id is the student_id for simplicity here
        parent_id=auth_payload['user_id'], 
        parent_pre_query=payload.parent_pre_query,
        tenant_id=auth_payload['tenant_id']
    )
    
    # Generate Dyte WebRTC Meeting if event is not purely in-person
    if slot.event.mode in ['VIRTUAL', 'HYBRID']:
        if DYTE_ORG_ID and DYTE_API_KEY:
            dyte_meeting_id = create_dyte_meeting(f"PTM with {slot.teacher_id}")
            if dyte_meeting_id:
                slot.dyte_meeting_id = dyte_meeting_id
        else:
            # Fallback to Jitsi if Dyte keys aren't provided
            room_name = f"PTM-{payload.slot_id}-{uuid.uuid4().hex[:8]}"
            slot.meeting_link = f"https://meet.jit.si/{room_name}"
        
    slot.is_booked = True
    slot.save()
    
    # --- Trigger Asynchronous Notifications ---
    # We pass the strings instead of object instances because Celery workers 
    # need primitive data types that can be serialized to JSON.
    time_str = f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"
    
    # In a real scenario, we would pull the phone/email from the parent's profile
    dummy_phone = "+1234567890"
    dummy_email = "parent@example.com"
    
    send_booking_confirmation_sms.delay(
        dummy_phone, "Parent", booking.student_id, time_str, slot.teacher_id
    )
    
    send_booking_confirmation_email.delay(
        dummy_email, "Parent", booking.student_id, time_str, slot.teacher_id
    )
    
    
    return {"id": booking.id, "status": booking.status}

@api.get("/bookings", response=List[ParentBookingSchema], auth=JWTAuth())
def get_parent_bookings(request):
    auth_payload = request.auth
    
    if auth_payload['role'] != 'PARENT':
        raise HttpError(403, "Only parents can view their bookings")
        
    bookings = PTMBooking.objects.filter(
        tenant_id=auth_payload['tenant_id'],
        parent_id=auth_payload['user_id']
    ).select_related('slot', 'slot__event').order_by('slot__start_time')
    
    result = []
    for b in bookings:
        result.append({
            "id": b.id,
            "slot_id": b.slot.id,
            "teacher_id": b.slot.teacher_id,
            "event_title": b.slot.event.title,
            "start_time": b.slot.start_time,
            "end_time": b.slot.end_time,
            "date": b.slot.event.date,
            "mode": b.slot.event.mode,
            "status": b.status,
            "meeting_link": b.slot.meeting_link,
            "teacher_remarks": b.teacher_remarks,
            "parent_pre_query": b.parent_pre_query
        })
        
    return result

@api.patch("/bookings/{booking_id}", response=BookingOutSchema, auth=JWTAuth())
def update_booking(request, booking_id: UUID, payload: BookingUpdateSchema):
    auth_payload = request.auth
    
    if auth_payload['role'] != 'TEACHER':
        raise HttpError(403, "Only teachers can update bookings")
        
    booking = get_object_or_404(PTMBooking, id=booking_id, tenant_id=auth_payload['tenant_id'])
    
    # Ensure this teacher owns the slot
    if booking.slot.teacher_id != auth_payload['user_id']:
        raise HttpError(403, "Not authorized to update this booking")
        
    if payload.status is not None:
        booking.status = payload.status
    if payload.teacher_remarks is not None:
        booking.teacher_remarks = payload.teacher_remarks
        
    booking.save()
    
    # Trigger Webhook back to ERP
    payload = {
        "booking_id": str(booking.id),
        "student_id": booking.student_id,
        "status": booking.status,
        "teacher_remarks": booking.teacher_remarks
    }
    dispatch_webhook.delay(auth_payload['tenant_id'], "booking.updated", payload)
    
    return {"id": booking.id, "status": booking.status, "message": "Booking updated successfully"}

class DyteTokenSchema(Schema):
    token: str

@api.get("/bookings/{booking_id}/dyte-token", response=DyteTokenSchema, auth=JWTAuth())
def get_dyte_token(request, booking_id: UUID):
    auth_payload = request.auth
    booking = get_object_or_404(PTMBooking, id=booking_id, tenant_id=auth_payload['tenant_id'])
    
    if not booking.slot.dyte_meeting_id:
        raise HttpError(400, "No Dyte meeting associated with this booking.")
        
    participant_name = f"{auth_payload['role']} - {auth_payload['user_id']}"
    preset = "group_call_host" if auth_payload['role'] == "TEACHER" else "group_call_participant"
    
    token = add_dyte_participant(booking.slot.dyte_meeting_id, participant_name, preset)
    if token:
        return {"token": token}
        
    raise HttpError(500, "Failed to generate Dyte token")


class WebhookUpdateSchema(Schema):
    webhook_url: str

@api.patch("/webhooks", auth=APIKeyAuth())
def update_webhook(request, payload: WebhookUpdateSchema):
    client = request.auth['client']
    client.webhook_url = payload.webhook_url
    client.save()
    return {"message": "Webhook URL updated successfully", "webhook_url": client.webhook_url}


# --- Analytics Endpoints ---
class AnalyticsSchema(Schema):
    total_events: int
    total_slots: int
    booked_slots: int
    utilization_percentage: float

@api.get("/analytics", response=AnalyticsSchema, auth=JWTAuth())
def get_analytics(request):
    auth_payload = request.auth
    tenant_id = auth_payload['tenant_id']
    
    total_events = PTMEvent.objects.filter(tenant_id=tenant_id).count()
    total_slots = PTMSlot.objects.filter(tenant_id=tenant_id).count()
    booked_slots = PTMSlot.objects.filter(tenant_id=tenant_id, is_booked=True).count()
    
    utilization = 0.0
    if total_slots > 0:
        utilization = (booked_slots / total_slots) * 100
        
    return {
        "total_events": total_events,
        "total_slots": total_slots,
        "booked_slots": booked_slots,
        "utilization_percentage": round(utilization, 2)
    }

@api.get("/teacher/schedule", response=List[TeacherScheduleSchema], auth=JWTAuth())
def get_teacher_schedule(request):
    auth_payload = request.auth
    
    if auth_payload['role'] != 'TEACHER':
        raise HttpError(403, "Only teachers can view their schedule")
        
    tenant_id = auth_payload['tenant_id']
    teacher_id = auth_payload['user_id']
    
    cache_key = f"schedule_{tenant_id}_{teacher_id}"
    cached_schedule = cache.get(cache_key)
    if cached_schedule is not None:
        return cached_schedule
        
    slots = PTMSlot.objects.filter(
        tenant_id=tenant_id,
        teacher_id=teacher_id
    ).prefetch_related('booking').order_by('start_time')
    
    result = []
    for slot in slots:
        data = {
            "id": slot.id,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "is_booked": slot.is_booked,
            "meeting_link": slot.meeting_link,
            "student_id": None,
            "parent_pre_query": None,
            "booking_id": None,
            "status": None,
            "teacher_remarks": None
        }
        if hasattr(slot, 'booking'):
            data["student_id"] = slot.booking.student_id
            data["parent_pre_query"] = slot.booking.parent_pre_query
            data["booking_id"] = slot.booking.id
            data["status"] = slot.booking.status
            data["teacher_remarks"] = slot.booking.teacher_remarks
        result.append(data)
        
    cache.set(cache_key, result, 60)
    return result


