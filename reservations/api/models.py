import uuid

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from enumchoicefield import ChoiceEnum, EnumChoiceField
from model_utils import FieldTracker


class IndestructableModel(models.Model):
    class Meta:
        abstract = True

    class NoDeleteQuerySet(models.QuerySet):
        def delete(self):
            raise NotImplementedError("Deletion of Rooms is not currently supported")

    def delete(self):
        # Deletion of Guests is not currently supported
        raise NotImplementedError("Deletion of Guests is not currently supported")

    def get_queryset(self):
        # Deletion of Rooms is not currently supported
        return self.__class__.NoDeleteQuerySet(self.model, using=self._db)


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
    number = models.CharField(max_length=255, null=False)  # A room "number" may contain alphanumerics


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
    in_date = models.DateField(editable=False)
    out_date = models.DateField(editable=False)
    checkin_datetime = models.DateTimeField(null=True)
    checkout_datetime = models.DateTimeField(null=True)
    status = EnumChoiceField(enum_class=ReservationState, default=ReservationState.pending)
    # Deletion of Guests is not currently supported.
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT)
    # Deletion of Rooms is not currently supported.
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    # Tracker to keep track of status changes
    tracker = FieldTracker()

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        self._set_check_in_check_out_time()

        # Save the resource
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