from rest_framework import serializers
from .models import PTMEvent, PTMSlot, PTMBooking

class PTMEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PTMEvent
        fields = "__all__"

class PTMSlotSerializer(serializers.ModelSerializer):
    is_booked = serializers.ReadOnlyField()

    class Meta:
        model = PTMSlot
        fields = "__all__"

class PTMBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PTMBooking
        fields = "__all__"
