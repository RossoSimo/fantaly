from django.test import TestCase
from django.urls import reverse

from leagues.models import FantasyManager
from testing_utils import make_league, make_user


class AddManagerViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.league = make_league(owner=self.user)

    def test_owner_can_add_a_manager(self):
        response = self.client.post(
            reverse('leagues:add_manager', kwargs={'pk': self.league.pk}), {'name': 'Alice'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FantasyManager.objects.filter(league=self.league, name='Alice').exists())

    def test_non_member_cannot_add_a_manager(self):
        outsider = make_user('outsider')
        self.client.force_login(outsider)
        response = self.client.post(
            reverse('leagues:add_manager', kwargs={'pk': self.league.pk}), {'name': 'Eve'},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(FantasyManager.objects.filter(league=self.league, name='Eve').exists())