import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptm_core.settings')
django.setup()

from ptm.models import PTMEvent, PTMSlot, PTMBooking

def run():
    print("Seeding database...")
    
    # Clear existing
    PTMBooking.objects.all().delete()
    PTMSlot.objects.all().delete()
    PTMEvent.objects.all().delete()

    tenant = "school_A"

    # Create Event
    event = PTMEvent.objects.create(
        title="Mid-Term Academic Review 2026",
        date=datetime.date(2026, 10, 15),
        start_time=datetime.time(9, 0),
        end_time=datetime.time(12, 0),
        slot_duration_minutes=15,
        gap_duration_minutes=5,
        mode='VIRTUAL',
        is_published=True,
        tenant_id=tenant
    )
    print(f"Created Event: {event.title}")

    # Create Slots for Teacher 1
    t1_slots = [
        (datetime.time(9, 0), datetime.time(9, 15)),
        (datetime.time(9, 20), datetime.time(9, 35)),
        (datetime.time(9, 40), datetime.time(9, 55)),
    ]
    for start, end in t1_slots:
        PTMSlot.objects.create(
            event=event,
            teacher_id="Mrs. Davis (Math)",
            start_time=start,
            end_time=end,
            tenant_id=tenant
        )

    # Create Slots for Teacher 2
    t2_slots = [
        (datetime.time(9, 0), datetime.time(9, 15)),
        (datetime.time(9, 20), datetime.time(9, 35)),
        (datetime.time(9, 40), datetime.time(9, 55)),
    ]
    for start, end in t2_slots:
        slot = PTMSlot.objects.create(
            event=event,
            teacher_id="Mr. Smith (Science)",
            start_time=start,
            end_time=end,
            tenant_id=tenant
        )
        # Pre-book the second slot for Mr. Smith
        if start == datetime.time(9, 20):
            slot.is_booked = True
            slot.save()
            PTMBooking.objects.create(
                slot=slot,
                student_id="student_xyz",
                parent_id="parent_xyz",
                tenant_id=tenant
            )

    print("Seeding completed successfully!")

if __name__ == '__main__':
    run()
