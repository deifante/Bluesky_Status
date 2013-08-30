import datetime

from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.conf import settings
import django.utils.timezone

from pymongo import Connection

from mongo_status.models import StatusCount, DetailedStatus, BasicStatus

@override_settings(MONGO_HOST='127.0.0.1')
class MongoStatusIndexViewTests(TestCase):
    def setUp(self):
        BasicStatus.objects.create(connection=settings.MONGO_HOST, update=123, new=234, delete=345)

    def test_index_view(self):
        """
        Make sure the index page doesn't die. Even with no data.
        """
        response = self.client.get(reverse('mongo_status:index'))
        self.assertEqual(response.status_code, 200)

    def test_index_view_status_counts(self):
        """
        Make sure the latest status information is being displayed properly
        """
        StatusCount.objects.create(
            complete=123, error=234, pending=345, processing=456,
            undetermined=567, total = 678, connection=settings.MONGO_HOST)
        response = self.client.get(reverse('mongo_status:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 123)
        self.assertContains(response, 234)
        self.assertContains(response, 345)
        self.assertContains(response, 456)
        self.assertContains(response, 567)
        self.assertContains(response, 678)

    def test_index_view_old_record(self):
        """
        On the main page I only want to display a week's worth of data to reduce
        page size.
        """
        two_weeks_ago = django.utils.timezone.now() - datetime.timedelta(1)
        StatusCount.objects.create(
             generation_time=two_weeks_ago, complete=123, error=234, pending=345,
            processing=456, undetermined=567, total=678)

        response = self.client.get(reverse('mongo_status:index'));
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<td class="text-complete">123</td>')
        self.assertContains(response, '<td class="text-error">234</td>')
        self.assertContains(response, '<td class="text-pending">345</td>')
        self.assertContains(response, '<td class="text-processing">456</td>')
        self.assertContains(response, '<td class="text-undetermined">567</td>')
        self.assertContains(response, '<td><strong>678</strong></td>')


@override_settings(MONGO_HOST='127.0.0.1')
@override_settings(SPLUNK_HOST='localhost')
@override_settings(SPLUNK_PORT=8089)
@override_settings(SPLUNK_USERNAME='admin')
@override_settings(SPLUNK_PASSWORD='changeme')
class MongoStatusGetStatusViewTests(TestCase):
    def setUp(self):
        BasicStatus.objects.create(connection=settings.MONGO_HOST, update=123, new=234, delete=345)

    def test_get_status_view_no_data(self):
        """
        Make sure the get_status view works without any provided data.
        """
        response = self.client.get(reverse('mongo_status:get_status'))
        self.assertEqual(response.status_code, 200)

    def test_get_status_view_not_integer(self):
        """
        Make sure the view can handle some poor user input.
        """
        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':'rr'})
        self.assertEqual(response.status_code, 200)

    def test_get_status_view_status_counts(self):
        """
        This is kinda crappy right now. It's "good" that it's not using the
        live instance of mongo to do testing against, I don't like that it's
        not using a modified name for the collection.
        """
        assetId = 2048
        asset_dict = {
            'assetId': assetId,
            'partnerData':{'getty':{'status':'pending'}}
            }

        mongo_connection = Connection()
        assets_collection = mongo_connection.bluesky.assets
        assets_collection.insert(asset_dict)
        StatusCount.objects.create(
            complete=123, error=234, pending=345, processing=456,
            undetermined=567, total = 678, connection=settings.MONGO_HOST)

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 123)
        self.assertContains(response, 234)
        self.assertContains(response, 345)
        self.assertContains(response, 456)
        self.assertContains(response, 567)
        self.assertContains(response, 678)
        self.assertContains(response, 2048)
        assets_collection.remove({'assetId':assetId})

@override_settings(MONGO_HOST='127.0.0.1')
@override_settings(SPLUNK_HOST='localhost')
@override_settings(SPLUNK_PORT=8089)
@override_settings(SPLUNK_USERNAME='admin')
@override_settings(SPLUNK_PASSWORD='changeme')
class MongoStatusGetStatusViewAttributesOfNoteTests(TestCase):
    """
    Ensure the 'Attributes of Note' section in the index.html template works as
    expected.
    """
    def setUp(self):
        BasicStatus.objects.create(connection=settings.MONGO_HOST, update=123, new=234, delete=345)

    def add_asset_to_mongo(self, asset):
        """
        Make a connection to mongo and insert the asset.

        Returns the assets collection in the bluesky database so the asset
        can be removed later.
        """
        mongo_connection = Connection()
        assets_collection = mongo_connection.bluesky.assets
        assets_collection.insert(asset)
        return assets_collection

    def ensure_getty_partner_data(self, asset):
        """
        Just sets up the asset dictionary the way I expect it to be.
        """
        if 'partnerData' not in asset:
            asset['partnerData'] = {}
        if 'getty' not in asset['partnerData']:
            asset['partnerData']['getty'] = {}

    def add_partner_id_to_asset(self, asset, partnerId):
        """
        Adds the partnerId attribute to an asset.
        """
        self.ensure_getty_partner_data(asset)
        asset['partnerData']['getty']['partnerId'] = int(partnerId)

    def add_legacy_migration_to_asset(self, asset):
        """
        Adds the partnerData.getty.legacyMigration attribute to an asset.
        """
        self.ensure_getty_partner_data(asset)
        asset['partnerData']['getty']['legacyMigration'] = True

    def add_hand_selected_to_asset(self, asset):
        """
        Adds the partnerData.getty.handSelected attribute to an asset.
        """
        self.ensure_getty_partner_data(asset)
        asset['partnerData']['getty']['handSelected'] = True

    def add_migrated_to_asset(self, asset):
        """
        Adds the partnerData.getty.handSelected attribute to an asset.
        """
        self.ensure_getty_partner_data(asset)
        asset['partnerData']['getty']['migrated'] = True

    def add_is_marked_for_pull_to_asset(self, asset):
        """
        Adds the isMarkedForPUll attribute to an asset.
        """
        asset['isMarkedForPull'] = True

    def set_priority_on_asset(self, asset, priority):
        """
        Kinda silly for this one but I want to keep the style of
        how all these tests work consistent.
        """
        asset['priority'] = priority

    def test_getty_id_attribute(self):
        """
        Make sure we're displaying the getty id as expected.
        """
        assetId = 92869
        getty_id = 813567
        asset_dict = {'assetId':assetId}
        self.add_partner_id_to_asset(asset_dict, getty_id)
        assets_collection = self.add_asset_to_mongo(asset_dict)

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Getty Id')
        self.assertContains(response, 'for this file: %d' % getty_id)

        assets_collection.remove({'assetId':assetId})

    def test_legacy_migration_attribute(self):
        """
        Make sure we're reporting on the Legacy Migration files as expected.
        """
        assetId = 92869
        asset_dict = {'assetId':assetId}
        self.add_legacy_migration_to_asset(asset_dict)
        assets_collection = self.add_asset_to_mongo(asset_dict)

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Legacy migrated files have already been transferred to Getty outside of Bluesky.')
        self.assertContains(response, 'Legacy Migration')

        assets_collection.remove({'assetId':assetId})

    def test_migrated_attribute(self):
        """
        Make sure we're reporting on migrating files as expected.
        """
        assetId = 92869
        asset_dict = {'assetId':assetId}
        self.add_migrated_to_asset(asset_dict)
        assets_collection = self.add_asset_to_mongo(asset_dict)

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'These files are in the process of being migrated. Normal Bluesky flow is halted.')
        self.assertContains(response, 'migrating')
        assets_collection.remove({'assetId':assetId})

    def test_is_marked_for_pull_attribute(self):
        """
        Make sure we're reporting on files that are meant to be deleted.
        """
        assetId = 92869
        asset_dict = {'assetId':assetId}
        self.add_is_marked_for_pull_to_asset(asset_dict)
        assets_collection = self.add_asset_to_mongo(asset_dict)

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This file is marked for')
        self.assertContains(response, 'deactivation!')

        assets_collection.remove({'assetId':assetId})

    def test_priority_attribute(self):
        """
        Test the reporting on the priority ranges.
        """
        assetId = 92869
        asset_dict = {'assetId':assetId}

        # update priority
        self.set_priority_on_asset(asset_dict,  2)
        assets_collection = self.add_asset_to_mongo(asset_dict)

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="text-update">update</span> request.</p>')
        assets_collection.remove({'assetId':assetId})

        # new priority
        self.set_priority_on_asset(asset_dict,  12)
        assets_collection = self.add_asset_to_mongo(asset_dict)

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="text-new">new </span>asset request.</p>')
        assets_collection.remove({'assetId':assetId})

        # special priority
        self.set_priority_on_asset(asset_dict,  42)
        assets_collection = self.add_asset_to_mongo(asset_dict)

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="text-special">')
        assets_collection.remove({'assetId':assetId})

        # delete priority
        self.set_priority_on_asset(asset_dict,  52)
        assets_collection = self.add_asset_to_mongo(asset_dict)

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="text-delete">delete</span> request.</p>')
        assets_collection.remove({'assetId':assetId})

class MongoStatusCompleteDetailsViewTests(TestCase):
    def test_complete_details_view(self):
        """
        Make sure the complete details view works without data
        """
        status = 'complete'
        response = self.client.get(reverse('mongo_status:complete_details', kwargs={'status':status}))
        self.assertEqual(response.status_code, 200)

    def test_complete_details_view_status_counts(self):
        """
        Make sure the complete details page displays provided data
        any data.
        """
        status = 'pending'

        DetailedStatus.objects.create(
            status=status, connection=settings.MONGO_HOST,total=123, updates=234,
            new=345, special=456, delete=567, legacy_migration=678,
            migrated=8910, hand_selected=91011)

        response = self.client.get(reverse('mongo_status:complete_details', kwargs={'status':status}))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 123)
        self.assertContains(response, 234)
        self.assertContains(response, 345)
        self.assertContains(response, 456)
        self.assertContains(response, 567)
        self.assertContains(response, 678)
        self.assertContains(response, 8910)
        self.assertContains(response, 91011)

@override_settings(SPLUNK_HOST='localhost')
@override_settings(SPLUNK_PORT=8089)
@override_settings(SPLUNK_USERNAME='admin')
@override_settings(SPLUNK_PASSWORD='changeme')
class MongoStatusAssetHistoryTests(TestCase):
    """
    Ensure the Asset History block is displaying as desired.

    These tests are not ideal because they currently depend on the data
    stored in my local host splunk.
    """
    def setUp(self):
        BasicStatus.objects.create(connection=settings.MONGO_HOST, update=123, new=234, delete=345)

    def test_sent_uri_splunk_action(self):
        """
        file id 11604984 has a had 'sent uri' action in my local host splunk
        """
        assetId = 11604984

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sent Uri')

    def test_sent_asset_splunk_action(self):
        """
        file id 11604984 has a had 'sent asset' action in my local host splunk
        """
        assetId = 11604984

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sent Asset')

    def test_received_error_splunk_action(self):
        """
        file id 11604984 has a had 'received error' action in my local host splunk
        """
        assetId = 11604984

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Received Error')

    def test_received_success_splunk_action(self):
        """
        file id 11604984 has a had 'received success' action in my local host splunk
        """
        assetId = 11604984

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Received Success')

    def test_sent_metadata_splunk_action(self):
        """
        file id 1963326 has a had 'received success' action in my local host splunk
        """
        assetId = 1963326

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sent Metadata')

    def test_sent_metadata_by_id_splunk_action(self):
        """
        file id 11604984 has a had 'sent metadata by id' action in my local host splunk
        """
        assetId = 11604984

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sent Metadata by Id')

    def test_queued_splunk_action(self):
        """
        file id 1005178 has a had a 'queued' action in my local host splunk
        """
        assetId = 1005178

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Queued')

    def test_invalid_splunk_action_display(self):
        """
        Log data can be messy even if it's from machines. Sometimes
        the code changes and there's little way to "unlog" splunk data.
        This will make sure things don't nuke when the code doesn't
        recognise a particular action logged in splunk.

        11604984 happens to have some older format logging messages attached to
        it. If the page renders without exception then the unexpected logging
        messages are being handled one way or another.
        """
        assetId = 11604984

        response = self.client.get(reverse('mongo_status:get_status'), {'assetId':assetId})
        self.assertEqual(response.status_code, 200)
        # an old logging message for getAssetDataById
        self.assertContains(response, 'Sent Specific Metadata')
