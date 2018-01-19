from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from reservations.api.models import CurrentAndUpcomingReservation, Guest, Room, Reservation, ReservationState
from reservations.api.utils.throttles import ReservationStatusRateThrottle
from reservations.api.views import GuestViewSet, ReservationViewSet, RoomViewSet

# TODO: Use reverse

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


# Current and Upcoming Reservation model tests
class CurrentAndUpcomingReservationTestCase(TestCase):
    def setUp(self):
        Guest.objects.create(first_name='Michelangelo')
        Room.objects.create(number='ABC101')

    def test_creation_of_reservation(self):
        today = datetime.utcnow().date()
        guest = Guest.objects.first()
        room = Room.objects.first()

        # A reservation whose arrival date way 2 days ago and whose departure date was yesterday is not current
        # and should not refresh the materialized view.
        reservation = Reservation.objects.create(in_date=today - timedelta(days=2), out_date=today - timedelta(days=1), guest=guest, room=room)
        upcoming_reservation = CurrentAndUpcomingReservation.objects.filter(
            in_date=today - timedelta(days=2),
            out_date=today - timedelta(days=1),
            first_name=guest.first_name,
            last_name=guest.last_name,
            room_number=room.number,
            status=reservation.status
        ).first()

        self.assertIs(CurrentAndUpcomingReservation.objects.count(), 0)
        self.assertIsNone(upcoming_reservation)

        # A Reservation whose arrival date was two days ago and whose departure date is today is current
        # and should refresh the materialized view.
        reservation = Reservation.objects.create(in_date=today - timedelta(days=2), out_date=today, guest=guest, room=room)
        upcoming_reservation = CurrentAndUpcomingReservation.objects.filter(
            in_date=today - timedelta(days=2),
            out_date=today,
            first_name=guest.first_name,
            last_name=guest.last_name,
            room_number=room.number,
            status=reservation.status
        ).first()

        self.assertIs(CurrentAndUpcomingReservation.objects.count(), 1)
        self.assertTrue(upcoming_reservation.reservation_id, reservation.pk)

        # A Reservation whose arrival date is today is current and should refresh the materialized view.
        reservation = Reservation.objects.create(in_date=today, out_date=today + timedelta(1), guest=guest, room=room)
        upcoming_reservation = CurrentAndUpcomingReservation.objects.filter(
            in_date=today,
            out_date=today + timedelta(days=1),
            first_name=guest.first_name,
            last_name=guest.last_name,
            room_number=room.number,
            status=reservation.status
        ).first()

        self.assertIs(CurrentAndUpcomingReservation.objects.count(), 2)
        self.assertTrue(upcoming_reservation.reservation_id, reservation.pk)

        # A Reservation that is upcoming in 2 days should refresh the materialized view.
        reservation = Reservation.objects.create(in_date=today + timedelta(days=2), out_date=today + timedelta(3), guest=guest, room=room)
        upcoming_reservation = CurrentAndUpcomingReservation.objects.filter(
            in_date=today + timedelta(days=2),
            out_date=today + timedelta(days=3),
            first_name=guest.first_name,
            last_name=guest.last_name,
            room_number=room.number,
            status=reservation.status
        ).first()

        self.assertIs(CurrentAndUpcomingReservation.objects.count(), 3)
        self.assertTrue(upcoming_reservation.reservation_id, reservation.pk)

        # A Reservation that is upcoming in 3 days should not refresh the materialized view.
        reservation = Reservation.objects.create(in_date=today + timedelta(days=3), out_date=today + timedelta(4), guest=guest, room=room)
        upcoming_reservation = CurrentAndUpcomingReservation.objects.filter(
            in_date=today + timedelta(days=3),
            out_date=today + timedelta(days=4),
            first_name=guest.first_name,
            last_name=guest.last_name,
            room_number=room.number,
            status=reservation.status
        ).first()

        self.assertIs(CurrentAndUpcomingReservation.objects.count(), 3)
        self.assertIsNone(upcoming_reservation)


#####################
# Integration tests #
#####################

class GuestIntegrationTest(TestCase):
    """
    Test Guest resource actions
    """

    GuestViewSet.throttle_classes = ()

    def test_get_guest(self):
        client = APIClient()

        self.assertIs(Guest.objects.count(), 0)
        guest = Guest.objects.create(first_name='Prince')
        self.assertIs(Guest.objects.count(), 1)

        guest_fetched = client.get('/guests/{}'.format(guest.pk))

        self.assertIsNotNone(guest_fetched)
        self.assertEquals(str(Guest.objects.first().pk), guest_fetched.data['id'])

    def test_create_guest(self):
        client = APIClient()

        self.assertIs(Guest.objects.count(), 0)
        guest = client.post('/guests', {'first_name': 'Homer'})
        self.assertIs(Guest.objects.count(), 1)

        self.assertEquals(str(Guest.objects.first().pk), guest.data['id'])

    def test_update_guest(self):
        client = APIClient()

        self.assertIs(Guest.objects.count(), 0)
        guest = Guest.objects.create(first_name='Madonna')
        self.assertIs(Guest.objects.count(), 1)
        self.assertIsNone(guest.last_name)

        client.patch('/guests/{}'.format(guest.pk), {'last_name': 'Ciccone'})
        guest.refresh_from_db()

        self.assertEquals(guest.last_name, 'Ciccone')


class RoomIntegrationTest(TestCase):
    """
    Test Room resource actions
    """

    RoomViewSet.throttle_classes = ()

    def test_get_room(self):
        client = APIClient()

        self.assertIs(Room.objects.count(), 0)
        room = Room.objects.create(number='ABC101')
        self.assertIs(Room.objects.count(), 1)

        room_fetched = client.get('/rooms/{}'.format(room.pk))

        self.assertIsNotNone(room_fetched)
        self.assertEquals(str(Room.objects.first().pk), room_fetched.data['id'])

    def test_create_guest(self):
        client = APIClient()

        self.assertIs(Room.objects.count(), 0)
        room = client.post('/rooms', {'number': 'ABC101'})
        self.assertIs(Room.objects.count(), 1)

        self.assertEquals(str(Room.objects.first().pk), room.data['id'])

    def test_update_guest(self):
        client = APIClient()

        self.assertIs(Room.objects.count(), 0)
        room = Room.objects.create(number='ABC101')
        self.assertIs(Room.objects.count(), 1)

        client.patch('/rooms/{}'.format(room.pk), {'number': 'DEF101'})
        room.refresh_from_db()

        self.assertEquals(room.number, 'DEF101')


class ReservationIntegrationTest(TestCase):
    """
    Test Reservation resource actions
    """

    ReservationViewSet.throttle_classes = ()

    def setUp(self):
        Guest.objects.create(first_name='Cleopatra')
        Room.objects.create(number='ABC101')

    def test_get_reservation(self):
        client = APIClient()

        self.assertIs(Reservation.objects.count(), 0)
        reservation = Reservation.objects.create(
            in_date='2018-01-01', out_date='2018-01-02',
            guest=Guest.objects.first(), room=Room.objects.first()
        )
        self.assertIs(Reservation.objects.count(), 1)

        reservation_fetched = client.get('/reservations/{}'.format(reservation.pk))

        self.assertIsNotNone(reservation_fetched)
        self.assertEquals(str(Reservation.objects.first().pk), reservation_fetched.data['id'])

    def test_create_reservation(self):
        client = APIClient()

        self.assertIs(Reservation.objects.count(), 0)
        reservation = client.post('/reservations', {
            'in_date': '2018-01-01', 'out_date': '2018-01-02',
            'guest': Guest.objects.first().pk, 'room': Room.objects.first().pk
        })
        self.assertIs(Reservation.objects.count(), 1)

        self.assertEquals(str(Reservation.objects.first().pk), reservation.data['id'])

    def test_update_guest(self):
        client = APIClient()

        self.assertIs(Reservation.objects.count(), 0)
        reservation = Reservation.objects.create(
            in_date='2018-01-01', out_date='2018-01-02',
            guest=Guest.objects.first(), room=Room.objects.first()
        )
        self.assertIs(Reservation.objects.count(), 1)

        client.patch('/reservations/{}'.format(reservation.pk), {'out_date': '2018-01-03'})
        reservation.refresh_from_db()

        self.assertEquals(reservation.out_date, datetime(year=2018, month=1, day=3).date())


class ReservationStatusThrottlingTestCase(TestCase):
    """
    Test that Reservation requests involving status updates trigger the special 1/min throttle.
    While non-completely-deterministic tests should generally be avoided
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
        response = client.patch('/reservations/{}'.format(reservation.pk), {'status': 'pending'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = client.patch('/reservations/{}'.format(reservation.pk), {'status': 'pending'})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_reservation_throttled_only_for_reservation_that_triggered_it(self):
        client = APIClient()
        reservation_one = Reservation.objects.create(in_date='2018-01-01', out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.first())
        reservation_two = Reservation.objects.create(in_date='2018-01-01', out_date='2018-01-02', guest=Guest.objects.first(), room=Room.objects.all()[1])

        # Ensure Reservations are different
        self.assertNotEqual(reservation_one.pk, reservation_two.pk)

        # Trigger a Reservation Status throttle for Reservation one
        response = client.patch('/reservations/{}'.format(reservation_one.pk), {'status': 'pending'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = client.patch('/reservations/{}'.format(reservation_one.pk), {'status': 'pending'})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Request for Reservation two is unaffected
        response = client.patch('/reservations/{}'.format(reservation_two.pk), {'status': 'pending'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Request for Reservation one is still under throttling timeout
        response = client.patch('/reservations/{}'.format(reservation_one.pk), {'status': 'pending'})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
