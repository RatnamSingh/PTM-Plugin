from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PTMEventViewSet, PTMSlotViewSet, PTMBookingViewSet

router = DefaultRouter()
router.register(r"events", PTMEventViewSet)
router.register(r"slots", PTMSlotViewSet)
router.register(r"bookings", PTMBookingViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
