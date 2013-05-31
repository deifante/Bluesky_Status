from django.test import TestCase
from django.core.urlresolvers import reverse

from mongo_status.models import StatusCount, DetailedStatus

class MongoStatusViewTests(TestCase):
    def test_index_view(self):
        """
        Make sure the home page doesn't die. Even with no data.
        """
        response = self.client.get(reverse('mongo_status:index'))
        self.assertEqual(response.status_code, 200)

    def test_index_view_status_counts(self):
        """
        Make sure the status latest status information is being displayed properly
        """
        StatusCount.objects.create(
            complete=123, error=234, pending=345, processing=456,
            undetermined=567, total = 678)
        response = self.client.get(reverse('mongo_status:index'))
        #print response
        # self.assertEqual(response.status_code, 200)
        # # self.assertContains(response, 123)

        # self.assertContains(response, 234)
        # # self.assertContains(response, 345)
        # # self.assertContains(response, 456)
        # # self.assertContains(response, 567)
        # # self.assertContains(response, 678)
        

        

        

