# -*- coding: utf-8 -*-
#
from django.dispatch import Signal

on_app_ready = Signal()

post_user_create = Signal(providing_args=('cloudaccount',))
