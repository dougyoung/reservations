import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import signals
from django.dispatch import receiver
from django.utils import timezone
from django_pgviews import view as pg
from enumchoicefield import ChoiceEnum, EnumChoiceField
from model_utils import FieldTracker

from reservations.api.utils.indestructable_model import IndestructableModel


class Guest(IndestructableModel):
    class Meta:
        ordering = ('last_name', 'first_name')

    ##############
    # Attributes #
    ##############
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, null=True)  # https://en.wikipedia.org/wiki/Mononymous_person


class Room(IndestructableModel):
    class Meta:
        ordering = ('number',)

    ##############
    # Attributes #
    ##############
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    number = models.CharField(max_length=255, null=False, unique=True)  # A room "number" may contain alphanumerics


class ReservationState(ChoiceEnum):
    pending = 'PENDING'
    checked_in = 'CHECKED_IN'
    checked_out = 'CHECKED_OUT'


class Reservation(IndestructableModel):
    class Meta:
        ordering = ('in_date',)

    ##############
    # Attributes #
    ##############
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    in_date = models.DateField(db_index=True, editable=False)
    out_date = models.DateField(db_index=True, editable=False)
    checkin_datetime = models.DateTimeField(null=True)
    checkout_datetime = models.DateTimeField(null=True)
    status = EnumChoiceField(db_index=True, enum_class=ReservationState, default=ReservationState.pending, null=False)
    # Deletion of Guests is not currently supported.
    guest = models.ForeignKey(Guest, db_index=True, on_delete=models.PROTECT)
    # Deletion of Rooms is not currently supported.
    room = models.ForeignKey(Room, db_index=True, on_delete=models.PROTECT)
    # Tracker to keep track of status changes
    tracker = FieldTracker()

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        self._set_check_in_check_out_time()

        # Save the resource with transactional atomicity.
        with transaction.atomic():
            # Here we would also update Room availability for a given Hotel.
            return super(Reservation, self).save(force_insert, force_update, *args, **kwargs)

    def _set_check_in_check_out_time(self):
        def transition_error(instance):
            raise ValidationError("Reservation cannot transition from {} to {}".format(
                instance.tracker.previous('status'),
                instance.status
            ))

        # If resource is not yet created status will always be PENDING
        if self._state.adding: return
        # If resource status has not changed return
        if not self.tracker.has_changed('status'): return

        # Status is not PENDING
        # If the status was PENDING
        if self.tracker.previous('status') == ReservationState.pending:
            # Then the new status should be CHECKED_IN
            if self.status == ReservationState.checked_in:
                self.checkin_datetime = timezone.now()
            else:
                transition_error(self)
        # If the status was CHECKED_IN
        elif self.tracker.previous('status') == ReservationState.checked_in:
            # Then the new status should be CHECKED_OUT
            if self.status == ReservationState.checked_out:
                self.checkout_datetime = timezone.now()
            else:
                transition_error(self)
        # If the status was CHECKED_OUT
        elif self.tracker.previous('status') == ReservationState.checked_out:
            # Then the new status should be CHECKED_OUT
            if self.status == ReservationState.checked_out:
                pass
            else:
                transition_error(self)
        else:
            # Unknown state
            transition_error(self)


# Signal receiver for Reservation save to concurrently refresh CurrentAndUpcomingReseravtionat materialized view.
@receiver(signals.post_save, sender=Reservation)
def reservation_saved(sender, action=None, instance=None, **kwargs):
    CurrentAndUpcomingReservation.refresh(concurrently=True)


# Select relevant Reservation information including Guest first name and last name as well as Room number.
# Where today's date is equal to or between the arrival date and departure date
# or where the arrival date is less than 3 days into the future.
# If we were modelling Hotels currently we would parameterize this by Hotel ID.
# This is used for the CurrentAndUpcomingReservation materialized view, which acts as a
# denormalized cache for current and upcoming Reservations.
CURRENT_AND_UPCOMING_RESERVATIONS_SQL = """
  SELECT r.id as reservation_id,
          first_name, last_name,
          in_date, out_date, number as room_number,
          checkin_datetime, checkout_datetime,
          status
  FROM reservations_reservation as r
  INNER JOIN reservations_guest ON r.guest_id = reservations_guest.id 
  INNER JOIN reservations_room ON r.room_id = reservations_room.id
  WHERE out_date >= current_date AND (
          in_date <= current_date OR
          age(in_date, current_date) < '3 days'
        )
  ORDER BY in_date;
"""


# A materialized view to cache current and upcoming Reservations.
# This materialized view is not managed by Django. In order to create it run:
# $ python3 manage.py sync_pgviews
class CurrentAndUpcomingReservation(pg.ReadOnlyMaterializedView):
    class Meta:
        managed = False

    # Must declare a unique key which can be used against for concurrent refreshes.
    concurrent_index = 'reservation_id'

    ##############
    # Attributes #
    ##############
    reservation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=255, null=False)
    last_name = models.CharField(max_length=255)
    in_date = models.DateField(editable=False, null=False)
    out_date = models.DateField(editable=False, null=False)
    room_number = models.CharField(max_length=255, null=False)
    checkin_datetime = models.DateTimeField(null=True)
    checkout_datetime = models.DateTimeField(null=True)
    status = EnumChoiceField(enum_class=ReservationState, default=ReservationState.pending, null=False)

    sql = CURRENT_AND_UPCOMING_RESERVATIONS_SQL
