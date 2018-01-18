import time

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from reservations.api.models import Guest, Room, Reservation, ReservationState
from reservations.api.utils.throttles import ReservationStatusRateThrottle
from reservations.api.views import ReservationViewSet

###############
# Model tests #
###############


# Guest model tests
class GuestTestCase(TestCase):
    def test_create(self):
        Guest.objects.create(first_name='John', last_name='Smith')
        guest = Guest.objects.filter(first_name='John', last_name='Smith').first()
        self.assertIsNotNone(guest)

    def test_update(self):
        guest_orig = Guest.objects.create(first_name='Typo', last_name='Smith')
        guest = Guest.objects.filter(first_name='John', last_name='Smith').first()
        self.assertIsNone(guest)
        guest_orig.first_name = 'John'
        guest_orig.save()
        guest = Guest.objects.filter(first_name='John', last_name='Smith').first()
        self.assertIsNotNone(guest)

    def test_delete_not_supported(self):
        guest = Guest.objects.create(first_name='Socrates')
        with self.assertRaises(NotImplementedError):
            guest.delete()
        guest = Guest.objects.filter(first_name='Socrates').first()
        self.assertIsNotNone(guest)

    def test_last_name_not_required(self):
        Guest.objects.create(first_name='Cher')
        guest = Guest.objects.filter(first_name='Cher').first()
        self.assertIsNotNone(guest)


# Room model tests
class RoomTestCase(TestCase):
    def test_create(self):
        Room.objects.create(number='ABC101')
        room = Room.objects.filter(number='ABC101').first()
        self.assertIsNotNone(room)

    def test_update(self):
        room = Room.objects.create(number='TYPO')
        room_fetched = Room.objects.filter(number='ABC101').first()
        self.assertIsNone(room_fetched)
        room.number = 'ABC101'
        room.save()
        room = Room.objects.filter(number='ABC101').first()
        self.assertIsNotNone(room)

    def test_delete_not_supported(self):
        room = Room.objects.create(number='ABC101')
        with self.assertRaises(NotImplementedError):
            room.delete()
        room = Room.objects.filter(number='ABC101').first()
        self.assertIsNotNone(room)


# Reservation model tests
class ReservationTestCase(TestCase):
    def setUp(self):
        Guest.objects.create(first_name='Voltaire')
        Room.objects.create(number='ABC101')

    def test_create(self):
        Reservation.objects.create(in_date='2018-01-01', out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.first())
        reservation = Reservation.objects.filter(in_date='2018-01-01').first()
        self.assertIsNotNone(reservation)

    def test_update(self):
        Reservation.objects.create(in_date='2018-01-01',  out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.first())
        reservation = Reservation.objects.filter(in_date='2018-01-01',  out_date='2018-01-02').first()
        self.assertIsNotNone(reservation)
        reservation.out_date = '2018-01-03'
        reservation.save()
        reservation = Reservation.objects.filter(out_date='2018-01-03').first()
        self.assertIsNotNone(reservation)

    def test_delete(self):
        reservation = Reservation.objects.create(in_date='2018-01-01',  out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.first())
        with self.assertRaises(NotImplementedError):
            reservation.delete()
        reservation = Reservation.objects.filter(in_date='2018-01-01',  out_date='2018-01-02').first()
        self.assertIsNotNone(reservation)

    def test_state_changes(self):
        reservation = Reservation.objects.create(in_date='2018-01-01',  out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.first())
        # It is acceptable to change status to the same status
        reservation.status = ReservationState.pending
        reservation.save()
        # It is not acceptable to skip a status
        reservation.status = ReservationState.checked_out
        with self.assertRaises(ValidationError):
            reservation.save()
        # It is acceptable to move from pending to checked_in
        reservation.status = ReservationState.checked_in
        reservation.save()
        # It is acceptable to change status to the same status
        reservation.status = ReservationState.checked_in
        reservation.save()
        # It is not acceptable to go backward in status
        reservation.status = ReservationState.pending
        with self.assertRaises(ValidationError):
            reservation.save()
        # It is acceptable to move from checked_in to checked_out
        reservation.status = ReservationState.checked_out
        reservation.save()
        # It is acceptable to change status to the same status
        reservation.status = ReservationState.checked_out
        reservation.save()
        # It is not acceptable to go backward in status
        reservation.status = ReservationState.pending
        with self.assertRaises(ValidationError):
            reservation.save()
        reservation.status = ReservationState.checked_in
        with self.assertRaises(ValidationError):
            reservation.save()

#####################
# Integration tests #
#####################


# TODO: Use reverse
class ReservationStatusThrottlingTestCase(TestCase):
    """
    Test that Reservation requests involving status updates trigger the special 1/min throttle.
    While non-completely-determinstic tests should generally be avoided
    the 1/min rate should almost certainly be hit within two lines of code.
    If the 1/min rate is lowered this test may become too in-deterministic to be viable.
    """

    # We only want to test the Reservation Status throttle
    ReservationViewSet.throttle_classes = (ReservationStatusRateThrottle,)

    def setUp(self):
        Guest.objects.create(first_name='Napoleon')
        Room.objects.create(number='ABC101')
        Room.objects.create(number='ABC102')

    def test_reservation_not_throttled_when_status_not_included(self):
        client = APIClient()
        reservation = Reservation.objects.create(in_date='2018-01-01', out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.first())

        # When a request does not involve the status it is not throttled by the Reservation Status throttle
        for i in range(2):
            response = client.patch('/reservations/{}'.format(reservation.pk), {'out_date': '2018-01-02'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reservation_throttled_when_status_included(self):
        client = APIClient()
        reservation = Reservation.objects.create(in_date='2018-01-01', out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.first())

        # When a request does involve the status it is throttled with the Reservation Status policy
        request = client.patch('/reservations/{}'.format(reservation.pk), {'status': 'pending'})
        self.assertEqual(request.status_code, status.HTTP_200_OK)
        request = client.patch('/reservations/{}'.format(reservation.pk), {'status': 'pending'})
        self.assertEqual(request.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_reservation_throttled_only_for_reservation_that_triggered_it(self):
        client = APIClient()
        reservation_one = Reservation.objects.create(in_date='2018-01-01', out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.first())
        reservation_two = Reservation.objects.create(in_date='2018-01-01', out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.all()[1])

        # Ensure Reservations are different
        self.assertNotEqual(reservation_one.pk, reservation_two.pk)

        # Trigger a Reservation Status throttle for Reservation one
        request = client.patch('/reservations/{}'.format(reservation_one.pk), {'status': 'pending'})
        self.assertEqual(request.status_code, status.HTTP_200_OK)
        request = client.patch('/reservations/{}'.format(reservation_one.pk), {'status': 'pending'})
        self.assertEqual(request.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Request for Reservation two is unaffected
        request = client.patch('/reservations/{}'.format(reservation_two.pk), {'status': 'pending'})
        self.assertEqual(request.status_code, status.HTTP_200_OK)

        # Request for Reservation one is still under throttling timeout
        request = client.patch('/reservations/{}'.format(reservation_one.pk), {'status': 'pending'})
        self.assertEqual(request.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
