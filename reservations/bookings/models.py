import uuid

from django.db import models

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


class Reservation(models.Model):
    class Meta:
        ordering = ('in_date',)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, null=True)  # https://en.wikipedia.org/wiki/Mononymous_person
    in_date = models.DateField()
    out_date = models.DateField()
    checkin_datetime = models.DateTimeField(null=True)
    checkout_datetime = models.DateTimeField(null=True)
    # Deletion of Rooms is not currently supported.
    # TODO: Test
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
