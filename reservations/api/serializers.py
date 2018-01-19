from enumchoicefield import EnumChoiceField
from rest_framework import serializers
from reservations.api.models import CurrentAndUpcomingReservation, Guest, Reservation, ReservationState, Room


class GuestSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Guest
        fields = ('url', 'first_name', 'last_name',)


class RoomSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Room
        fields = ('url', 'number',)


class ReservationSerializer(serializers.HyperlinkedModelSerializer):
    # TODO: Need all of this?
    in_date = serializers.DateField(required=True)
    out_date = serializers.DateField(required=True)
    status = EnumChoiceField(enum_class=ReservationState)
    checkin_datetime = serializers.DateTimeField(required=False)
    checkout_datetime = serializers.DateTimeField(required=False)
    guest = serializers.PrimaryKeyRelatedField(
        queryset=Guest.objects.all(),
        required=True,
        write_only=False
    )
    room = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),  # TODO: Is this really going to query all Rooms?
        required=True,
        write_only=False
    )

    class Meta:
        model = Reservation
        fields = ('url', 'in_date', 'out_date', 'status', 'checkin_datetime', 'checkout_datetime', 'guest', 'room')

    def create(self, validated_data):
        """
        Create and return a new `Reservation` instance, given the validated data.
        :param validated_data:
        :return: Reservation resource
        """
        return Reservation.objects.create(**validated_data);

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
        instance.save()
        return instance


class CurrentAndUpcomingReservationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CurrentAndUpcomingReservation
        fields = (
            'url',
            'first_name', 'last_name',
            'in_date', 'out_date', 'room_number',
            'checkin_datetime', 'checkout_datetime', 'status'
        )
