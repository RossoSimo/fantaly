# Fantaly

A Django-based decision-support tool for fantasy football (Fantacalcio) managers,
built around the player auction, following the product spec in `AGENTS.md`.

The app is an **assistant**, not an auction administrator: it doesn't run or
enforce the auction — it records what a user reports happened, calculates
budgets from that record, and surfaces player data, market intelligence, and
suggested prices to help the manager make their own decisions.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py runserver
```

Then:

1. Go to `/admin/` and create at least one `Season` (e.g. label `2026/2027`,
   year_start `2026`, year_end `2027`) — leagues need a season to attach to.
2. Sign up at `/accounts/signup/` (or log in with your superuser).
3. Create a league at `/leagues/new/`.
4. Add players and fantasy managers via `/admin/` (dedicated UI for this is
   a near-term follow-up — see "What's not built yet" below).
5. Open the auction board from the league detail page.

## Running tests

```bash
python3 manage.py test
```

33 tests cover the invariants AGENTS.md calls out as mandatory: player
identity matching (including ambiguous-match handling), league isolation,
season isolation (stats/valuations never bleed across seasons), budget
calculations, auction transaction invariants (one owner per player per
league, overspend protection, corrections vs. history rewriting), news
deduplication, and market price aggregation (observed vs. estimated).

## Project structure

Domain-oriented Django apps, per the architecture principles in AGENTS.md:

```
config/         Project settings, root URLconf
accounts/       Auth (signup/login/logout — uses Django's built-in views)
leagues/        League, LeagueMembership, FantasyManager
seasons/        Season
players/        Player, Team, PlayerAlias, PlayerExternalId,
                PlayerIdentityMatchLog + players/identity.py resolver
stats/          PlayerSeasonStats, PlayerStatus (named `stats`, not
                `statistics`, to avoid shadowing the stdlib module)
news/           NewsSource, PlayerNews + news/ingestion.py dedup service
auction/        PlayerAvailability, Auction, AuctionNomination, Bid,
                AuctionTransaction + auction/services.py (all
                credit/ownership business logic lives here)
valuations/     PlayerValuation, ValuationComponent + valuations/engine.py
                (pluggable ValuationEngine interface, BaselineValuationEngine)
market/         MarketPriceObservation + market/aggregation.py
notifications/  Notification, NotificationPreference (scaffold only)
providers/      Empty package skeleton for future external data providers
                (players/statistics/news/injuries/lineups/market)
templates/      Shared Bootstrap-based templates (mobile-first)
testing_utils.py  Shared test factory helpers (not a Django app)
```

Business logic for anything that touches credits or player ownership lives
in `auction/services.py`, not in views or templates, so it's reusable from
a future API, management commands, and background jobs without duplication.

## Key design decisions worth knowing about

- **Player identity** is never inferred from display name alone.
  `players/identity.py` resolves external data in priority order (stable
  external ID → provider ID → club+name → name → fuzzy) and never
  auto-merges two players — ambiguous matches come back unmatched with
  `is_ambiguous=True` for manual review. Every attempt is logged to
  `PlayerIdentityMatchLog`.
- **Budgets are never stored** — `auction.services.get_manager_budget()`
  computes everything from the `AuctionTransaction` ledger, which is
  append-only. Corrections create a new transaction pointing back at the
  one they correct (`is_correction` / `corrects`) rather than editing
  history in place.
- **One owner per player per league** is enforced both in the service
  layer (for a clear error message) and at the database level (a
  `UniqueConstraint` on `AuctionTransaction(league, player)` for
  non-correction rows), so a race condition can't violate it.
- **Market data** strictly separates `observed` prices from `estimated`,
  `user_entered`, and `system_valuation` ones — `market/aggregation.py`
  only aggregates `observed` rows, so an estimate can never be presented
  as a real market price.
- **Valuations are explainable** — every `PlayerValuation.suggested_price`
  is backed by `ValuationComponent` line items (base value, form
  adjustment, risk penalty, ...) rather than being an opaque number.

## What's implemented vs. what's next

**Implemented:** the full domain model from AGENTS.md's "Core Concepts",
multi-league/season isolation, the identity/dedup/aggregation services
above, a working (if intentionally minimal) auction dashboard UI, and the
mandatory test coverage.

**Not built yet** (flagged as future work in AGENTS.md itself, or simply
out of scope for a first pass):
- Dedicated UI for adding players/managers (currently via `/admin/`)
- RSS ingestion jobs / Celery task queue (architecture supports adding one;
  none is wired up yet)
- Provider integrations under `providers/` (only the package skeleton exists)
- Watchlists, player notes, squad planning simulator, auction simulation
- Notification delivery (the data model exists; nothing sends anything yet)
- REST/JSON API (the service layer is already structured to support one
  without rewriting domain logic)

## Database

SQLite is used by default (zero setup, fine for development and the test
suite). To use PostgreSQL, copy `.env.example` to `.env`, fill in the
`DJANGO_DB_*` values, and `pip install -r requirements-postgres.txt` in
addition to the base requirements.
