from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.conf import settings

from pymongo import Connection

from mongo_status.models import StatusCount, DetailedStatus


class MongoStatusIndexViewTests(TestCase):
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

class MongoStatusGetStatusViewTests(TestCase):
    def test_get_status_view_no_data(self):
        """
        Make sure the get_status view works without any provided data.
        """
        response = self.client.get(reverse('mongo_status:get_status'))
        self.assertEqual(response.status_code, 200)

    @override_settings(MONGO_HOST='127.0.0.1')
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
        print response.content
        assets_collection.remove({'assetId':assetId});

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
