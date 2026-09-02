from django.test import TestCase

from players.identity import ExternalPlayerRecord, resolve_player
from players.models import (
    AliasType,
    MatchMethod,
    Player,
    PlayerAlias,
    PlayerExternalId,
    PlayerIdentityMatchLog,
    Position,
    Team,
)


class PlayerIdentityResolutionTests(TestCase):
    def setUp(self):
        self.napoli = Team.objects.create(name='Napoli', short_name='NAP')
        self.roma = Team.objects.create(name='Roma', short_name='ROM')
        self.mario = Player.objects.create(
            full_name='Mario Rossi', display_name='Rossi', position=Position.MIDFIELDER,
            club=self.napoli,
        )
        # A same-named player at a different club — this is exactly the
        # kind of ambiguity the system must never silently resolve.
        self.mario2 = Player.objects.create(
            full_name='Mario Rossi', display_name='Rossi M.', position=Position.DEFENDER,
            club=self.roma,
        )

    def test_external_id_has_highest_priority_and_is_unambiguous(self):
        PlayerExternalId.objects.create(player=self.mario, provider='sportradar', external_id='123')
        record = ExternalPlayerRecord(
            provider='sportradar', external_id='123', full_name='Mario Rossi', club_name='Napoli',
        )
        result = resolve_player(record)
        self.assertEqual(result.player, self.mario)
        self.assertEqual(result.method, MatchMethod.EXTERNAL_ID)
        self.assertFalse(result.is_ambiguous)

    def test_club_and_name_disambiguates_when_name_alone_would_be_ambiguous(self):
        record = ExternalPlayerRecord(
            provider='sportradar', full_name='Mario Rossi', club_name='Roma',
        )
        result = resolve_player(record)
        self.assertEqual(result.player, self.mario2)
        self.assertEqual(result.method, MatchMethod.CLUB_AND_NAME)

    def test_ambiguous_name_match_is_never_silently_resolved(self):
        record = ExternalPlayerRecord(provider='sportradar', full_name='Mario Rossi', club_name=None)
        result = resolve_player(record)
        self.assertIsNone(result.player)
        self.assertTrue(result.is_ambiguous)

    def test_alias_resolves_to_existing_player_via_name_matching(self):
        PlayerAlias.objects.create(
            player=self.mario, alias='Il Mago', alias_type=AliasType.NICKNAME,
        )
        record = ExternalPlayerRecord(provider='sportradar', full_name='Il Mago', club_name='Napoli')
        result = resolve_player(record)
        self.assertEqual(result.player, self.mario)

    def test_every_resolution_attempt_is_logged_for_audit(self):
        record = ExternalPlayerRecord(provider='sportradar', full_name='Mario Rossi', club_name='Napoli')
        resolve_player(record)
        self.assertEqual(PlayerIdentityMatchLog.objects.count(), 1)
        log = PlayerIdentityMatchLog.objects.first()
        self.assertEqual(log.raw_input['full_name'], 'Mario Rossi')

    def test_unmatched_record_is_logged_without_a_player(self):
        record = ExternalPlayerRecord(provider='sportradar', full_name='Nobody Real', club_name=None)
        result = resolve_player(record)
        self.assertIsNone(result.player)
        log = PlayerIdentityMatchLog.objects.first()
        self.assertIsNone(log.player)

    def test_duplicate_external_id_for_different_player_is_rejected_at_db_level(self):
        PlayerExternalId.objects.create(player=self.mario, provider='sportradar', external_id='999')
        with self.assertRaises(Exception):
            PlayerExternalId.objects.create(player=self.mario2, provider='sportradar', external_id='999')
