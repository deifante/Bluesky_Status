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
