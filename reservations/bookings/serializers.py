from rest_framework import serializers
from reservations.bookings.models import Reservation, Room


class RoomSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Room
        fields = ('id', 'number',)


class ReservationSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.UUIDField(read_only=True)
    in_date = serializers.DateField(required=True)
    out_date = serializers.DateField(required=True)
    checkin_datetime = serializers.DateTimeField(required=False)
    checkout_datetime = serializers.DateTimeField(required=False)
    room = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),  # TODO: Is this really going to query all Rooms?
        required=True,
        write_only=False
    )

    class Meta:
        model = Reservation
        fields = ('id', 'in_date', 'out_date', 'checkin_datetime', 'checkout_datetime', 'room')

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
        instance.checkin_datetime = validated_data.get('checkin_datetime', instance.checkin_datetime)
        instance.checkout_datetime = validated_data.get('checkout_datetime', instance.checkout_datetime)
        instance.save()
        return instance
