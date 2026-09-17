import uuid
from django.db import models

class TenantAwareModel(models.Model):
    tenant_id = models.CharField(max_length=100, db_index=True, help_text="ID of the school/ERP tenant")

    class Meta:
        abstract = True

class PTMEvent(TenantAwareModel):
    MODE_CHOICES = [
        ('IN_PERSON', 'In Person'),
        ('VIRTUAL', 'Virtual'),
        ('HYBRID', 'Hybrid'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.PositiveIntegerField(default=15)
    gap_duration_minutes = models.PositiveIntegerField(default=5)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='IN_PERSON')
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.date})"

class PTMSlot(TenantAwareModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(PTMEvent, on_delete=models.CASCADE, related_name='slots')
    teacher_id = models.CharField(max_length=100, db_index=True, help_text="External ID of the teacher")
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=50, blank=True, null=True)
    meeting_link = models.URLField(blank=True, null=True)
    dyte_meeting_id = models.CharField(max_length=255, blank=True, null=True)
    is_booked = models.BooleanField(default=False)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"Slot: {self.teacher_id} | {self.start_time}-{self.end_time}"

class PTMBooking(TenantAwareModel):
    STATUS_CHOICES = [
        ('BOOKED', 'Booked'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('NO_SHOW', 'No Show'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slot = models.OneToOneField(PTMSlot, on_delete=models.CASCADE, related_name='booking')
    student_id = models.CharField(max_length=100, db_index=True, help_text="External ID of the student")
    parent_id = models.CharField(max_length=100, db_index=True, help_text="External ID of the parent")
    
    parent_pre_query = models.TextField(blank=True, null=True, help_text="Pre-meeting query submitted by parent")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BOOKED')
    
    teacher_remarks = models.TextField(blank=True, null=True, help_text="Shared feedback visible to parent")
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Booking: {self.student_id} with {self.slot.teacher_id}"
