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

    def test_delete(self):
        guest = Guest.objects.create(first_name='John', last_name='Smith')
        guest.delete()
        guest = Guest.objects.filter(first_name='John', last_name='Smith').first()
        self.assertIsNone(guest)

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
        reservation.delete()
        reservation = Reservation.objects.filter(in_date='2018-01-01',  out_date='2018-01-02').first()
        self.assertIsNone(reservation)

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
