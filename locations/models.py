from django.db import models

class Location(models.Model):
    address = models.CharField('адрес', max_length=200, unique=True)
    lon = models.FloatField('долгота', null=True, blank=True)
    lat = models.FloatField('широта', null=True, blank=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'адрес'
        verbose_name_plural = 'адреса'

    def __str__(self):
        return self.address
