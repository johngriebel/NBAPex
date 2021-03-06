# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-12 12:38
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('nba_stats', '0002_auto_20170421_1659'),
    ]

    operations = [
        migrations.AddField(
            model_name='playerseason',
            name='career_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='team',
            name='head_coach',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='nba_stats.Coach'),
        ),
    ]
