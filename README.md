# PTM Engine (Plugin)

This repository contains the core, headless backend API engine for the Parent-Teacher Meeting (PTM) platform. It is designed to be easily plugged into existing ERP systems as a microservice.

## Architecture & Integration

*   **Framework:** Django & Django Ninja
*   **Multi-tenancy:** All models use a `tenant_id` to strictly separate data per school/ERP.
*   **Authentication:** Accepts JWT tokens signed by the parent ERP (simulated via `/auth/mock-sso`).
*   **Data Sync:** Dispatches Webhooks to the parent ERP whenever a booking status is updated by a teacher.

## Core Capabilities

1.  **Event Generation:** Rapidly generate in-person, virtual, or hybrid meeting slots for teachers based on customizable durations and gap times.
2.  **Booking Engine:** Handles concurrent parent bookings and tracks slot statuses to prevent double-booking.
3.  **Video Conferencing:** Deep integration with **Dyte API** to automatically provision secure WebRTC video rooms for virtual/hybrid meetings.
4.  **Asynchronous Workflows:** Uses Celery/Redis to queue SMS and Email notifications without blocking the API.

## Getting Started

### Prerequisites
*   Python 3.9+
*   Redis (for Celery background tasks)

### Setup Instructions
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run migrations and start the server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
4. In a separate terminal, start Celery to process webhooks and notifications:
   ```bash
   celery -A ptm_core worker -l INFO
   ```

## API Documentation
Once the server is running, the interactive Swagger API documentation provided by Django Ninja can be accessed at:
`http://localhost:8000/api/docs`
