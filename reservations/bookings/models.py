import uuid

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from enumchoicefield import ChoiceEnum, EnumChoiceField

class NoDeleteQuerySet(models.QuerySet):
    def delete(self):
        raise NotImplementedError("Deletion of Rooms is not currently supported")


class Room(models.Model):
    class Meta:
        ordering = ('number',)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    number = models.IntegerField(null=False)

    def delete(self):
        # Deletion of Rooms is not currently supported
        raise NotImplementedError("Deletion of Rooms is not currently supported")

    def get_queryset(self):
        # Deletion of Rooms is not currently supported
        return NoDeleteQuerySet(self.model, using=self._db)


class ReservationStates(ChoiceEnum):
    pending = 'PENDING'
    checked_in = 'CHECKED_IN'
    checked_out = 'CHECKED_OUT'


class Reservation(models.Model):
    class Meta:
        ordering = ('in_date',)

    def __init__(self, *args, **kwargs):
        super(Reservation, self).__init__(*args, **kwargs)
        self.__status_was = self.status

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        def save_super(instance):
            super(Reservation, instance).save(force_insert, force_update, *args, **kwargs)

        def transition_error(instance):
            raise ValidationError("Reservation cannot transition from {} to {}".format(
                instance.__status_was,
                instance.status
            ))

        # If resource is not yet created status will always be PENDING
        if self._state.adding: return save_super(self)
        # If resource status is PENDING return
        if self.status == ReservationStates.pending: return save_super(self)

        # Status is not PENDING
        # If the status was PENDING
        if self.__status_was == ReservationStates.pending:
            # Then the new status should be CHECKED_IN
            if self.status == ReservationStates.checked_in:
                self.checkin_datetime = timezone.now()
            else:
                transition_error(self)
        elif self.__status_was == ReservationStates.checked_in:
            # Then the new status should be CHECKED_OUT
            if self.status == ReservationStates.checked_out:
                self.checkout_datetime = timezone.now()
            else:
                transition_error(self)
        elif self.__status_was == ReservationStates.checked_out:
            # Then the new status should be CHECKED_OUT
            if self.status == ReservationStates.checked_out:
                pass
            else:
                transition_error(self)
        else:
            # Unknown state
            transition_error(self)

        # Finally, save the resource
        return save_super(self)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, null=True)  # https://en.wikipedia.org/wiki/Mononymous_person
    in_date = models.DateField()
    out_date = models.DateField()
    checkin_datetime = models.DateTimeField(null=True)
    checkout_datetime = models.DateTimeField(null=True)
    status = EnumChoiceField(enum_class=ReservationStates, default=ReservationStates.pending)
    # Deletion of Rooms is not currently supported.
    # TODO: Test
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
