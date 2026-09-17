from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PTMEvent, PTMSlot, PTMBooking
from .serializers import PTMEventSerializer, PTMSlotSerializer, PTMBookingSerializer
from tenants.views import TenantAwareModelViewSet
from .signals import ptm_booking_confirmed

class PTMEventViewSet(TenantAwareModelViewSet):
    queryset = PTMEvent.objects.all()
    serializer_class = PTMEventSerializer

class PTMSlotViewSet(TenantAwareModelViewSet):
    queryset = PTMSlot.objects.all()
    serializer_class = PTMSlotSerializer

class PTMBookingViewSet(TenantAwareModelViewSet):
    queryset = PTMBooking.objects.all()
    serializer_class = PTMBookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save()
        # Emit signal when booking is created
        ptm_booking_confirmed.send(sender=self.__class__, booking=booking)
