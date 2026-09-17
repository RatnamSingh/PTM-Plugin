from django.db import models
from tenants.models import TenantAwareModel
from profiles.models import TeacherProfile, StudentProfile, ParentProfile

class PTMEvent(TenantAwareModel):
    title = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    slot_duration_minutes = models.IntegerField(default=15)
    gap_duration_minutes = models.IntegerField(default=5)
    
    is_published = models.BooleanField(default=False)
    
    MODE_CHOICES = (
        ("VIRTUAL", "Virtual Meeting (Dyte/Jitsi)"),
        ("IN_PERSON", "In-Person at School"),
    )
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="VIRTUAL")

    def __str__(self):
        return f"{self.title} - {self.date}"

class PTMSlot(TenantAwareModel):
    event = models.ForeignKey(PTMEvent, on_delete=models.CASCADE, related_name="slots")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="ptm_slots")
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    meeting_link = models.URLField(blank=True, null=True)
    dyte_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    
    @property
    def is_booked(self):
        return hasattr(self, "booking")

    def __str__(self):
        return f"{self.teacher} at {self.start_time}"

class PTMBooking(TenantAwareModel):
    slot = models.OneToOneField(PTMSlot, on_delete=models.CASCADE, related_name="booking")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="ptm_bookings")
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name="ptm_bookings")
    
    STATUS_CHOICES = (
        ("SCHEDULED", "Scheduled"),
        ("COMPLETED", "Completed"),
        ("NO_SHOW", "No Show"),
        ("CANCELLED", "Cancelled"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SCHEDULED")
    
    teacher_remarks = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Booking for {self.student} at {self.slot.start_time}"
