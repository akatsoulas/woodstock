# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0006_auto_20150914_1244'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='slug',
        ),
        migrations.RemoveField(
            model_name='mozillianprofile',
            name='slug',
        ),
    ]
