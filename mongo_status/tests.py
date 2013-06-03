from django.test import TestCase
from django.core.urlresolvers import reverse

from mongo_status.models import StatusCount, DetailedStatus
from Bluesky_Status.settings import MONGO_HOST

class MongoStatusViewTests(TestCase):
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
            undetermined=567, total = 678, connection=MONGO_HOST)
        response = self.client.get(reverse('mongo_status:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 123)
        self.assertContains(response, 234)
        self.assertContains(response, 345)
        self.assertContains(response, 456)
        self.assertContains(response, 567)
        self.assertContains(response, 678)

    def test_complete_details_view_status_counts(self):
        """
        Make sure the complete details page displays provided data
        any data.
        """
        status = 'complete'

        DetailedStatus.objects.create(
            status=status, connection=MONGO_HOST,total=123, updates=234,
            new=345, special=456, delete=567, legacy_migration=678,
            migrated=8910, hand_selected=91011)

        response = self.client.get(reverse('mongo_status:complete_details', kwargs={'status':status}))
        self.assertEqual(response.status_code, 200)

    def test_complete_details_view(self):
        """
        Make sure the complete details page works without data
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
            status=status, connection=MONGO_HOST,total=123, updates=234,
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
