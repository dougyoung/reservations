from django.db import models


class IndestructableModel(models.Model):
    class Meta:
        abstract = True

    class NoDeleteQuerySet(models.QuerySet):
        def delete(self):
            raise NotImplementedError("Deletion of Rooms is not currently supported")

    def delete(self):
        # Deletion of this resource is not currently supported
        raise NotImplementedError("Deletion of {} is not currently supported".format(self.__class__))

    def get_queryset(self):
        # Deletion of Rooms is not currently supported
        return self.__class__.NoDeleteQuerySet(self.model, using=self._db)
