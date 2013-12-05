#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab

from django.contrib import admin
from mycron.task.models import Task

admin.site.register(Task)
