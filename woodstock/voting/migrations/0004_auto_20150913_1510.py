# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


EVENTS = ['MozFest',
          'All Hands',
          'Leadership Summit']


def add_events(apps, schema_editor):
    Event = apps.get_model('voting', 'Event')
    for event_name in EVENTS:
        if not Event.objects.filter(name=event_name).exists():
            Event.objects.create(name=event_name)


class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0003_auto_20150911_0957'),
    ]

    operations = [
        migrations.RunPython(add_events)
    ]
