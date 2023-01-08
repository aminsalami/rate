from django.db import models


class Region(models.Model):
    slug = models.TextField(primary_key=True)
    name = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.DO_NOTHING, blank=True, null=True, db_column="parent_slug")

    class Meta:
        db_table = 'regions'


class Port(models.Model):
    code = models.CharField(primary_key=True, max_length=5, verbose_name="port code")
    name = models.TextField()
    # Note: null=False, assuming port has always a "Region" parent
    parent = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column="parent_slug")

    class Meta:
        db_table = 'ports'


class Price(models.Model):
    # The `prices` table imported from rates.sql does not have a primaryKey, while django requires a pk to operate.
    #   >> id = models.BigAutoField(primary_key=True)
    orig_code = models.ForeignKey(Port, on_delete=models.DO_NOTHING, related_name="prices_from", db_column="orig_code")
    dest_code = models.ForeignKey(Port, on_delete=models.DO_NOTHING, related_name="prices_to", db_column="dest_code")
    day = models.DateField()
    price = models.IntegerField()

    class Meta:
        db_table = 'prices'
