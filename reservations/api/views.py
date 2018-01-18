from rest_framework import viewsets, mixins
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from reservations.api.models import Guest, Room, Reservation
from reservations.api.serializers import GuestSerializer, RoomSerializer, ReservationSerializer
from reservations.api.utils.throttles import ReservationStatusRateThrottle


# Guest View set
# We only want to allow GET, POST, GET <id>, and PUT/PATCH <id>
# so we explicitly declare only those mixins.
class GuestViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    API endpoint that allows reservations to be viewed or edited
    """
    authentication_classes = (SessionAuthentication, BasicAuthentication)

    queryset = Guest.objects.all().order_by('last_name', 'first_name')
    serializer_class = GuestSerializer


# Room View set
# We only want to allow GET, POST, GET <id>, and PUT/PATCH <id>
# so we explicitly declare only those mixins.
class RoomViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    API endpoint that allows reservations to be viewed or edited
    """
    authentication_classes = (SessionAuthentication, BasicAuthentication)

    queryset = Room.objects.all().order_by('-number')
    serializer_class = RoomSerializer


# Reservation View set
# We only want to allow GET, POST, GET <id>, and PUT/PATCH <id>
# so we explicitly declare only those mixins.
class ReservationViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    """
    API endpoint that allows reservations to be viewed or edited
    """
    authentication_classes = (SessionAuthentication, BasicAuthentication)
    throttle_classes = (ReservationStatusRateThrottle, AnonRateThrottle, UserRateThrottle)

    queryset = Reservation.objects.all().order_by('-in_date')
    serializer_class = ReservationSerializer
