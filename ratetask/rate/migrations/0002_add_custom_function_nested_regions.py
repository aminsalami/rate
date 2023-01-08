from django.db import migrations

from rate.custom_sqls import raw__ports_in_region


class Migration(migrations.Migration):
    dependencies = [("rate", "0001_initial")]

    operations = [
        migrations.RunSQL(raw__ports_in_region)
    ]
