from django.core.exceptions import ValidationError
from enumchoicefield import EnumChoiceField
from rest_framework import serializers
from reservations.api.models import CurrentAndUpcomingReservation, Guest, Reservation, ReservationState, Room


class GuestSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Guest
        fields = ('id', 'url', 'first_name', 'last_name',)


class RoomSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Room
        fields = ('id', 'url', 'number',)


class ReservationSerializer(serializers.HyperlinkedModelSerializer):
    in_date = serializers.DateField(required=True)
    out_date = serializers.DateField(required=True)
    status = EnumChoiceField(enum_class=ReservationState)
    checkin_datetime = serializers.DateTimeField(required=False)
    checkout_datetime = serializers.DateTimeField(required=False)
    guest = serializers.PrimaryKeyRelatedField(queryset=Guest.objects.all(), required=True)
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(), required=True)

    class Meta:
        model = Reservation
        fields = ('id', 'url', 'in_date', 'out_date', 'status', 'checkin_datetime', 'checkout_datetime', 'guest', 'room')

    def update(self, instance, validated_data):
        """
        Update and return an existing `Reservation` instance, given validated data.
        :param instance:
        :param validated_data:
        :return: Reservation resource
        """
        instance.in_date = validated_data.get('in_date', instance.in_date)
        instance.out_date = validated_data.get('out_date', instance.out_date)
        instance.status = validated_data.get('status', instance.status)
        instance.guest = validated_data.get('guest', instance.guest)
        instance.room = validated_data.get('room', instance.room)

        try:
            instance.save()
        except ValidationError as err:
            raise serializers.ValidationError(err.message)

        return instance

    def validate(self, data):
        # Check that the arrival date is on or before the departure date
        if 'in_date' in data and 'out_date' in data:
            if data['in_date'] > data['out_date']:
                raise serializers.ValidationError("Arrival date must be before departure date")

        return data


class CurrentAndUpcomingReservationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CurrentAndUpcomingReservation
        fields = (
            'url',
            'first_name', 'last_name',
            'in_date', 'out_date', 'room_number',
            'checkin_datetime', 'checkout_datetime', 'status'
        )
