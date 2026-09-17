# PTM Reusable Django App

This repository contains the `ptm` Django application, designed to be dropped directly into the `aicos-backend` monolith.

## Handoff Instructions for AICOS Team

This app relies on your existing `TenantAwareModel`, authentication middleware, and `profiles` app.

### 1. Installation
1. Copy the `backend/ptm` folder from this repository directly into your `aicos-backend` repository.
2. Add `'ptm'` to your `INSTALLED_APPS` in `settings.py`.

### 2. Routing
In your main `urls.py`, mount the PTM endpoints:
```python
path('api/ptm/', include('ptm.urls')),
```

### 3. Database Migrations
Since we have added Foreign Keys to your existing `TeacherProfile`, `StudentProfile`, and `ParentProfile`, you must generate the migrations in your monolith:
```bash
python manage.py makemigrations ptm
python manage.py migrate
```

### 4. Post-Booking Signals
When a parent successfully books a slot, the `ptm` app emits a Django signal called `ptm_booking_confirmed`. 
You should catch this signal in your monolith to trigger emails or SMS:

```python
# In your monolith (e.g., communications/signals.py)
from django.dispatch import receiver
from ptm.signals import ptm_booking_confirmed

@receiver(ptm_booking_confirmed)
def send_ptm_communications(sender, booking, **kwargs):
    print(f"Booking {booking.id} confirmed! Sending email to {booking.parent.email}...")
    # call your internal email_service here
```
