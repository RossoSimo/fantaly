from django.test import TestCase
from django.urls import reverse

from players.models import Player, Position
from testing_utils import make_player, make_team, make_user


class PlayerListViewTests(TestCase):
    def setUp(self):
        self.user = make_user('searcher')
        self.client.force_login(self.user)
        self.napoli = make_team('Napoli')
        self.roma = make_team('Roma')
        self.mario = make_player('Mario Rossi', position=Position.MIDFIELDER, club=self.napoli)
        self.luca = make_player('Luca Bianchi', position=Position.FORWARD, club=self.roma)

    def test_search_filters_by_name(self):
        response = self.client.get(reverse('players:list'), {'q': 'Mario'})
        self.assertContains(response, 'Mario Rossi')
        self.assertNotContains(response, 'Luca Bianchi')

    def test_search_filters_by_club(self):
        response = self.client.get(reverse('players:list'), {'q': 'Roma'})
        self.assertContains(response, 'Luca Bianchi')
        self.assertNotContains(response, 'Mario Rossi')

    def test_filter_by_position(self):
        response = self.client.get(reverse('players:list'), {'position': Position.FORWARD})
        self.assertContains(response, 'Luca Bianchi')
        self.assertNotContains(response, 'Mario Rossi')

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('players:list'))
        self.assertEqual(response.status_code, 302)


class PlayerCreateViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_can_create_a_player(self):
        response = self.client.post(reverse('players:create'), {
            'full_name': 'New Player', 'display_name': 'New Player',
            'first_name': 'New', 'last_name': 'Player',
            'position': Position.DEFENDER, 'is_active': 'on',
        })
        self.assertEqual(Player.objects.filter(display_name='New Player').count(), 1)
        self.assertEqual(response.status_code, 302)