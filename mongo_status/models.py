import datetime

from django.db import models

class StatusCount(models.Model):
    """
    Records historical information from MongoAccess.get_status_counts with the
    goal being to be able to graph this information at a later date.
    """
    generation_time = models.DateTimeField(auto_now_add=True, help_text='The time this information was generated.')
    connection = models.IPAddressField(default = '127.0.0.1', help_text='The server this data was gathered from.')
    complete = models.BigIntegerField(default=0, help_text='The count of how many records are in complete status.')
    error = models.BigIntegerField(default=0, help_text='The count of how many records are in error status.')
    pending = models.BigIntegerField(default=0, help_text='The count of how many records are in pending status.')
    processing = models.BigIntegerField(default=0, help_text='The count of how many records are in processing status.')
    undetermined = models.BigIntegerField(default=0, help_text='The count of how many records are in an unknown status.')
    total = models.BigIntegerField(default=0, help_text='A count of all the records in mongo')

    def __unicode__(self):
        return 'Status count generated @ %s. complete:%d error:%d pending:%d processing:%d total:%d' % (self.generation_time.strftime('%Y-%m-%d %H-%M-S'), self.complete, self.error, self.pending, self.pending)

    class Meta:
        ordering = ['connection', 'generation_time']
        get_latest_by = 'generation_time'

class DetailedStatus(models.Model):
    """
    Stores the information gathered via MongoAccess.get_status_details

    It can take a while (seconds... even minutes!) to get this all this
    information from mongo so I want to save it for later so I can graph it
    and potentially get this information via cron and not have to ever pull
    from a non-fresh cached version of this data.
    """
    status = models.CharField(max_length=10, help_text='The status that this information correlates to.')
    generation_time = models.DateTimeField(auto_now_add=True, help_text='The time this information was generated.')
    connection = models.IPAddressField(default = '127.0.0.1', help_text='The server this data was gathered from.')
    total = models.BigIntegerField(default=0, help_text='A count of all the records of this status in mongo.')

    # These should *roughly* add up to all the records that are of the particular status.
    updates = models.BigIntegerField(default=0, help_text='A count of all the updating records of this status in mongo. These records have their priority set to the update range (0-4).')
    new = models.BigIntegerField(default=0, help_text='A count of all the new records of this status in mongo. These records have their priority set to the new range (10-14).')
    special = models.BigIntegerField(default=0, help_text='A count of all the "special" records of this status in mongo. These records have their priority set to the "special" range (40-44).')
    delete = models.BigIntegerField(default=0, help_text='A count of all the delete records of this status in mongo. These records have their priority set to the delete range (50-54).')

    # These attributes are independant of the previous 4. Don't expect them to add up @ all
    legacy_migration = models.BigIntegerField(default=0, help_text='Files that were previously migrated via methods other than Bluesky.')
    migrated = models.BigIntegerField(default=0, help_text='Files that are currently in the process of being migrated via methods other than Bluesky.')
    hand_selected = models.BigIntegerField(default=0, help_text='Files that have been specifically chosen for inclusion in Bluesky.')

    # instead of being a count, these 2 are the assetIds of the oldest and newest record for this status.
    oldest = models.BigIntegerField(default=0, help_text='The oldest record found with this status.')
    newest = models.BigIntegerField(default=0, help_text='The newest record found with this status.')

    def __unicode__(self):
        return 'Detailed Status for %s generated @ %s' % (self.status, self.generation_time.strftime('%Y-%m-%d %H-%M-S'))

    class Meta:
        ordering = ['connection', 'status', 'generation_time']
        get_latest_by = 'generation_time'

class BasicStatus(models.Model):
    """
    Stores a simple view of the Bluesky queue

    We want to cut all the detail from the status so we can get a good feel for
    the health of the queue. We're purposely leaving out error because that
    doesn't *directly* add to any back log.
    """
    generation_time = models.DateTimeField(auto_now_add=True, help_text='The time this information was generated.')
    connection = models.IPAddressField(default = '127.0.0.1', help_text='The server this data was gathered from.')
    update = models.BigIntegerField(default=0, help_text='The count of how many records in the Bluesky queue are for modifications.')
    new = models.BigIntegerField(default=0, help_text='The count of how many records in the Bluesky queue are for new files.')
    delete = models.BigIntegerField(default=0, help_text='The count of how many records in the Bluesky queue are for file deletions.')

    def __unicode__(self):
        return 'Basic status generated @ %s. updates:%s news:%s deletes:%s' % (self.generation_time.strftime('%Y-%m-%d %H-%M-S'), self.update, self.new, self.delete)

    class Meta:
        ordering = ['connection', 'generation_time']
        get_latest_by = 'generation_time'


class DaySummary(models.Model):
    """
    Computing a summary of the things that happened in a day takes from 4 to 7 minutes right now. Too long to process @ request time.

    I don't think the calling api makes use of all the function calls that we provide, so I think I'll leave space for them in the db but not make a large attempt to actually compute their usage.

    This class will be used to store the results of a high level scan of the logging that happened in a particular day.
    This is a small outline of the logging that is currently in the system.n

   | Thing that happend       | logging message                   |
   |--------------------------+-----------------------------------|
   | file set to pending      | Queued.                           |
   | setAssetStatus (error)   | Received Error.                   |
   | setAssetStatus (success) | Received Success.                 |
   | getAssetData             | 'Sent Metadata.' for each file ID |
   | getAssetDataById         | Sent Metadata by Id.              | (not used)
   | generateNewAssetUri      | Sent Uri.                         | (not used)
   | File retrieved           | Sent Asset.                       |
    """
    day = models.DateField(help_text='The day that is summarised', blank=False)
    connection = models.CharField(max_length=64, help_text='The IP or host name for the splunk server where these results were retrieved from')

    total_queued = models.BigIntegerField(default=0, help_text='The total number of queueing events')
    unique_queued = models.BigIntegerField(default=0, help_text='The number of unique file ids queued in this time')

    total_errored = models.BigIntegerField(default=0, help_text='The total number of error events')
    unique_errored = models.BigIntegerField(default=0, help_text='The number of unique file ids that reported errors on this day')

    total_success = models.BigIntegerField(default=0, help_text='The total number of success events')
    unique_success = models.BigIntegerField(default=0, help_text='The number of unique file ids that reported success on this day')

    total_sent_metadata = models.BigIntegerField(default=0, help_text='The total number of meta data packets sent')
    unique_sent_metadata = models.BigIntegerField(default=0, help_text='The number of meta data packets sent for unique fild ids on this day')

    total_sent_asset = models.BigIntegerField(default=0, help_text='The total number of meta data packets sent')
    unique_sent_asset = models.BigIntegerField(default=0, help_text='The number of meta data packets sent for unique fild ids on this day')

    def __unicode__(self):
        return '%s for %s on %s' % (type(self), self.day.isoformat(), self.connection)

    class Meta:
        ordering = ['connection', '-day']
        unique_together = ('day', 'connection')
        get_latest_by = 'day'
