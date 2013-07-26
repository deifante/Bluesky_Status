#! /usr/bin/python
# -*- coding: utf-8 -*-
import datetime
import time
import os

#compute_date = datetime.date.today()
compute_date = datetime.date(2013, 07, 19)
earliest_day_of_logging = datetime.date(2013, 6, 22)
while compute_date > earliest_day_of_logging:
    print '%s @ %s' %  (str(compute_date), datetime.datetime.now())
    execution_string = '/home/deifante/Projects/Bluesky_Status/manage.py make_day_summary %s' % (str(compute_date))
    os.system(execution_string)
    compute_date = compute_date + datetime.timedelta(-1)
    time.sleep(60*15)
print 'done'
