# AGENTS.md

## Project Overview

This project is a Django-based web application designed to assist fantasy football managers throughout the entire fantasy football season, with a particular focus on the player auction.

The application must support multiple fantasy leagues, each with its own rules, players, budgets, scoring system, and auction configuration.

The primary goal is to provide a reliable decision-support tool during the auction while also becoming a useful companion throughout the season.

The application must be designed with both desktop and mobile users in mind.

The initial implementation should prioritize correctness, data integrity, usability, and extensibility over unnecessary complexity.

---

# Product Goals

The application should help a fantasy football manager:

1. Prepare for the auction.
2. Understand the value of every player.
3. Track player performance from the previous and current seasons.
4. Track injuries, suspensions, starting status, and other relevant player news.
5. Monitor the auction in real time.
6. Track how many credits each manager has spent.
7. Track which players are still available.
8. Estimate an appropriate price for each player.
9. Understand how other fantasy managers across Italy are valuing players.
10. Manage multiple fantasy leagues with different rules.
11. Continue using the application after the auction during the regular season.

The application is an assistant and decision-support system.

It must not make irreversible decisions on behalf of the user.

---

# Technology Stack

## Backend

- Python
- Django
- Django ORM
- Django migrations
- Django authentication
- Django management commands
- Django admin for internal data administration

## Frontend

- Django templates where appropriate
- Bootstrap
- JavaScript for interactive components
- Responsive design
- Mobile-first layouts

A frontend framework such as React/Vue should not be introduced unless a concrete requirement justifies it.

The initial architecture should favor Django's server-rendered approach with progressively enhanced JavaScript.

## Database

The application should support PostgreSQL in production.

SQLite may be used for local development and tests.

## Background Tasks

The architecture should allow asynchronous jobs for:

- RSS ingestion
- Player data updates
- Injury/status updates
- Price aggregation
- Scheduled data synchronization
- Notifications

A task queue such as Celery may be introduced when required.

Do not introduce infrastructure that is not currently necessary.

---

# Core Concepts

The system revolves around the following concepts:

- User
- Fantasy League
- Fantasy Manager
- League Rules
- Season
- Player
- Team
- Player Alias
- Player Statistics
- Player Status
- Player News
- Player Price
- Auction
- Auction Nomination
- Bid
- Manager Budget
- Manager Roster
- Player Valuation
- Market Price
- Player Availability

These concepts should be represented explicitly in the domain model.

Avoid storing important domain information as unstructured JSON when a relational model is more appropriate.

---

# Multi-League Support

A user must be able to manage multiple fantasy leagues.

Each league must be isolated from the others.

A league may define its own:

- Number of managers
- Initial credits
- Squad size
- Goalkeeper rules
- Defender rules
- Midfielder rules
- Forward rules
- Formation rules
- Scoring rules
- Bonus/malus rules
- Auction rules
- Minimum bid
- Maximum bid
- Number of players per position
- Player list
- Season
- Auction configuration

League-specific settings must never be assumed to be global.

For example, two leagues may use the same player but have completely different valuations because their scoring systems differ.

---

# Player Identity

Player identity is one of the most important parts of the system.

The application MUST NOT identify players exclusively by their displayed name.

Players with similar or identical names must always remain distinct entities.

Every player must have a unique internal identity.

The preferred identity strategy should use stable external identifiers whenever available.

A player record should ideally contain:

- Internal ID
- Full name
- Display name
- First name
- Last name
- Date of birth
- Nationality
- Position
- Club
- External provider IDs
- Previous club
- Active/inactive state

## Aliases

Each player may have multiple aliases.

Examples:

- Full name
- Short name
- Common nickname
- Provider-specific name
- Name containing accents
- Name without accents
- Historical name

Aliases must point to an existing player entity.

The system must never automatically merge two players simply because their names are similar.

Automatic matching may suggest a match, but ambiguous identity resolution must have safeguards.

When importing external data, player identity matching should prioritize:

1. Stable external player ID.
2. Provider-specific identifier.
3. Club + player information.
4. Name matching.
5. Fuzzy matching only as a last resort.

Any automatic alias/matching mechanism must be auditable.

---

# Player Data

Each player must have historical and current-season information.

At minimum, the system should support:

## Previous Season

- Appearances
- Starts
- Minutes
- Goals
- Assists
- Yellow cards
- Red cards
- Own goals
- Clean sheets where applicable
- Fantasy points
- Average rating
- Fantasy average
- Matches missed
- Injury information
- Suspension information
- Club
- Position

## Current Season

The same information should be stored for the current season.

Statistics must be associated with a specific season.

Do not overwrite historical statistics when new information arrives.

---

# Player Status

The application must expose the current player status.

At minimum:

- Starting
- Bench
- Injured
- Suspended
- Doubtful
- Unavailable
- Returning from injury
- Unknown

The status system should allow multiple signals where necessary.

For example, a player could be:

- Injured
- Expected return: 2 weeks

Status information should have:

- Source
- Timestamp
- Confidence where available
- Start date
- End date where applicable

The application should distinguish between confirmed information and predictions.

---

# News and RSS

The application should aggregate relevant player news.

Each player may have multiple news items.

News should contain:

- Title
- Description/summary
- Source
- Original URL
- Publication date
- Retrieved date
- Associated player
- Relevant club
- Optional category

Possible categories:

- Injury
- Suspension
- Line-up
- Transfer
- Training
- Performance
- Coach statement
- General news

RSS feeds should be ingested automatically.

The same news item must not be imported multiple times.

News should be deduplicated using stable identifiers where available and URL/title/date fallbacks otherwise.

External content should not be copied unnecessarily.

The application should store metadata and links to the original source.

---

# Auction System

The auction tracker is one of the primary features of the application.

It must be designed for speed and reliability.

The application is NOT an auction administrator.

It does not need to conduct or enforce the auction.

Instead, the user manually records what happens during a real-world auction.

The system should allow the user to:

1. Select a player.
2. Mark the player as currently being auctioned.
3. Record the winning fantasy manager.
4. Record the winning bid.
5. Confirm the purchase.
6. Update the manager's remaining credits.
7. Add the player to the manager's roster.
8. Mark the player as unavailable.
9. Move to the next player.

The entire operation should require as few interactions as possible.

---

# Auction Dashboard

The auction dashboard should provide an immediate overview.

It should display:

- Current player
- Player position
- Club
- Player valuation
- Suggested price
- Current bid
- Winning manager
- Winning bid
- Remaining credits of every manager
- Number of roster slots remaining
- Players already purchased
- Players still available
- Recent purchases
- Average market price
- Relevant player news
- Current player status

The dashboard should work particularly well on mobile devices.

Important actions must remain easily accessible without excessive scrolling.

---

# Manager Budgets

Every fantasy manager must have a budget.

The system must track:

- Initial credits
- Current credits
- Total spent
- Remaining credits
- Number of players purchased
- Remaining roster slots
- Position-specific slots
- Average purchase price

Credits must be calculated from recorded transactions rather than manually maintained wherever possible.

Example:

Initial budget:

`500`

Purchase:

`Player A = 42`

Remaining:

`458`

The system should maintain an immutable transaction history.

Corrections should preferably create an adjustment transaction rather than silently modifying historical transactions.

---

# Manager Rosters

Each fantasy manager must have a roster.

A roster should track:

- Player
- Position
- Purchase price
- Purchase date
- Auction
- Manager
- League
- Season

The system must prevent the same player from being assigned to multiple managers in the same league and auction.

---

# Auction History

Every completed purchase should create a transaction.

An auction transaction should contain:

- Player
- League
- Season
- Manager
- Winning price
- Timestamp
- Auction identifier
- Optional notes

Transactions must be auditable.

The application should provide a complete auction history.

---

# Player Valuation

The application should calculate a suggested price for every player.

This valuation must be configurable and explainable.

The suggested price may consider:

- League budget
- League scoring rules
- Player position
- Previous-season statistics
- Current-season statistics
- Expected playing time
- Starting probability
- Injury status
- Suspension status
- Recent performance
- Team strength
- Player role
- Historical auction prices
- Current market prices
- Remaining league budgets
- Number of players still available
- Squad composition requirements

The valuation system should not be implemented as an opaque magic number.

Where possible, users should be able to understand why a player has a given valuation.

Example:

> Suggested price: 38 credits  
> Base value: 32  
> Expected starting role: +5  
> Recent performance: +4  
> Injury risk: -3

The valuation engine should be designed so that different algorithms can be introduced later.

---

# Italian Market Data

The application should aggregate anonymous auction prices from fantasy football managers across Italy when reliable data sources are available.

For each player, the application should ideally show:

- Average purchase price
- Median purchase price
- Minimum purchase price
- Maximum purchase price
- Number of observed purchases
- Recent purchase prices
- Price distribution
- Trend over time

Market data must always distinguish between:

- Actual observed prices
- Estimated prices
- User-entered prices
- System-generated valuations

Never present an estimate as an observed market price.

Privacy must be respected when collecting data from users.

Individual fantasy managers should not be exposed unless they explicitly consent.

---

# Auction Intelligence

During an auction, the application should help answer:

> "How much should I spend on this player right now?"

The answer should consider the current state of the auction.

For example:

- Current budget
- Remaining managers' budgets
- Remaining positions
- Remaining players
- Player valuation
- Market price
- League-specific rules
- User's current roster
- User's remaining positional needs

The suggested bid should therefore be dynamic.

A player may have a different recommended price at the beginning of an auction compared with the end.

---

# Budget Strategy

The application should eventually support auction strategies.

Possible strategies:

- Balanced
- Stars and fillers
- Conservative
- Aggressive
- Position-focused
- Value hunting

Users should eventually be able to define personal spending limits.

The system may warn the user:

> Paying 52 credits would exceed your recommended maximum of 45.

Warnings must not prevent the user from making the purchase.

The application is advisory.

---

# Player Availability

The application must clearly distinguish between:

- Available
- Currently being auctioned
- Purchased
- Unsold
- Unavailable
- Withdrawn

A player purchased in a league must no longer appear as available in that league.

The same player can, however, remain available in another league.

---

# Search

Player search is critical.

Search should support:

- Full name
- Partial name
- Alias
- Club
- Position

Search results must always display enough identifying information to avoid selecting the wrong player.

For example:

`Mario Rossi — Napoli — Midfielder`

should not simply display:

`Mario Rossi`

Search must be fast enough to use during a live auction.

---

# Filters

Players should be filterable by:

- Position
- Club
- Availability
- Starting status
- Injury status
- Suspension
- Price range
- Suggested value
- Market value
- Previous-season performance
- Current-season performance

Filters should work well on mobile.

---

# Season Management

The system must support multiple seasons.

A player is a persistent entity across seasons.

Statistics, club affiliation, auction transactions, valuations, and statuses are season-specific.

Never duplicate the same real-world player merely because a new season starts.

---

# Data Sources

External data providers should be abstracted behind dedicated services.

Do not spread provider-specific logic throughout Django models and views.

Use a structure similar to:

```text
providers/
    players/
    statistics/
    news/
    injuries/
    lineups/
    market/
```

Each provider should have a clearly defined interface.

This makes it possible to replace a data source without rewriting the entire application.

External data should be treated as untrusted input.

Validate and normalize all imported data before saving it.

---

# Data Freshness

Time-sensitive information must have timestamps.

For example:

- Player status updated at 18:42
- Statistics updated at 18:30
- News retrieved at 18:35
- Market price calculated at 18:40

The UI should make stale information identifiable.

---

# Notifications

A future version should support notifications for:

- Player injury
- Player suspension
- Starting lineup announcement
- Major status change
- Important news
- Player price changes
- Auction reminders
- Player availability changes

Notifications should be configurable per user.

---

# Watchlist

Users should be able to create a personal watchlist.

A watchlist may contain:

- Players
- Target price
- Maximum price
- Priority
- Notes

During the auction, the user should be able to quickly access their watchlist.

---

# Player Notes

Users should be able to maintain private notes for players.

Examples:

- "Very reliable starter"
- "Avoid above 35"
- "Good pairing with X"
- "High injury risk"

Notes must be private to the user unless explicitly shared.

---

# Player Pairing and Dependencies

A future feature should support relationships between players.

Examples:

- Team pairings
- Alternative players
- Direct competitors for the same position
- Players whose value changes depending on another player's presence

The system should not initially attempt to automatically infer complex dependencies.

---

# Squad Planning

Before the auction, users should be able to simulate their ideal squad.

The simulator should allow:

- Selecting target players
- Setting maximum prices
- Allocating a hypothetical budget
- Comparing squad configurations
- Simulating different spending strategies

This simulation must not affect the real auction.

---

# Auction Simulation

A future feature should allow users to simulate auctions using historical data.

Possible capabilities:

- Random manager behavior
- Historical player prices
- Budget constraints
- Different manager strategies
- Multiple simulated auctions

This can eventually be used to estimate realistic spending ranges.

---

# UX Requirements

The application must be responsive.

It must support:

- Desktop
- Tablet
- Mobile

Bootstrap should be used for the main responsive layout.

Do not design a desktop interface and simply shrink it for mobile.

Mobile auction usage is a first-class use case.

---

# Mobile Auction Mode

The application should eventually provide a dedicated mobile auction mode.

This mode should prioritize:

1. Current player
2. Suggested price
3. Maximum recommended price
4. Current bid
5. Manager budgets
6. Confirm purchase
7. Recent purchases
8. Player status

Secondary information such as detailed historical statistics can be collapsed or placed behind expandable sections.

---

# Accessibility

The application should follow modern accessibility practices.

Requirements include:

- Semantic HTML
- Keyboard navigation
- Sufficient contrast
- Visible focus states
- Accessible form controls
- Appropriate labels
- No interaction that depends exclusively on color

Do not use color as the only indicator of player status.

---

# Authentication and Authorization

Users must only be able to access leagues and private information they are authorized to access.

League membership should be explicit.

Roles may eventually include:

- Owner
- Manager
- Viewer

However, the application should not assume that a fantasy league administrator must use the application.

The core auction tracker should work for ordinary participants.

---

# Security

Follow Django security best practices.

Important requirements:

- CSRF protection
- Authentication
- Authorization
- Secure session handling
- Input validation
- ORM queries instead of raw SQL where possible
- Protection against XSS
- Secure handling of external URLs
- No secrets committed to the repository

Secrets must be provided through environment variables.

---

# API Design

The project should be structured so that an API can be introduced without rewriting the domain logic.

Business logic should not live exclusively inside templates or JavaScript.

Domain operations should be reusable from:

- Django views
- API endpoints
- Management commands
- Background jobs
- Tests

---

# Testing

Tests are mandatory for important domain behavior.

At minimum, test:

- Player identity matching
- Alias handling
- League isolation
- Season isolation
- Budget calculations
- Auction transactions
- Player availability
- Manager roster constraints
- Valuation calculations
- Data imports
- Duplicate news detection
- Authorization

Auction-related calculations should have extensive automated tests.

A change that can affect credits or player ownership must include appropriate tests.

---

# Data Integrity Rules

The following invariants must always hold:

1. A player can only belong to one manager within a specific league auction.
2. A manager cannot spend more credits than they have available unless the league explicitly allows it.
3. A purchased player cannot remain available in the same league.
4. Historical transactions must not be silently rewritten.
5. Statistics must remain associated with their original season.
6. Player aliases must point to a real player.
7. External player IDs must not accidentally map multiple real players to one entity.
8. League-specific rules must not leak into other leagues.
9. Market prices must be distinguishable from system valuations.
10. All important financial operations must be auditable.

---

# Architecture Principles

Prefer simple, explicit architecture.

Use Django applications organized around business domains rather than technical layers alone.

A possible initial structure:

```text
project/
    config/
    accounts/
    leagues/
    seasons/
    players/
    statistics/
    news/
    auction/
    valuations/
    market/
    notifications/
    providers/
    templates/
    static/
    tests/
```

The exact structure can evolve as the project grows.

Avoid premature microservices.

The initial application should be a modular Django monolith.

---

# Domain Logic

Important business rules should live in domain-oriented Python code rather than directly inside templates.

Avoid putting complex calculations into:

- Django templates
- JavaScript-only logic
- View functions with hundreds of lines
- Database triggers unless there is a strong reason

The same calculation must produce the same result regardless of how it is invoked.

---

# Auditability

Important user actions should be traceable.

Examples:

- Player assigned to manager
- Auction price recorded
- Auction transaction corrected
- Player identity changed
- Alias created
- External player mapping changed

Where appropriate, store:

- User
- Action
- Timestamp
- Previous value
- New value

This is particularly important for auction data.

---

# Performance

The auction interface must remain fast even with:

- Hundreds of players
- Multiple leagues
- Multiple seasons
- Thousands of news items
- Large auction histories
- Many concurrent users

Avoid N+1 database queries.

Use appropriate Django techniques such as:

- `select_related`
- `prefetch_related`
- Database indexes
- Pagination
- Caching where appropriate

Performance optimizations should be driven by measurements rather than assumptions.

---

# Internationalization

The initial user interface may be Italian, but the architecture should allow future translations.

Player names and external data must never be translated or altered for presentation without preserving the original value.

---

# Logging and Observability

The application should provide structured logging for:

- External data imports
- Failed imports
- Player identity matching
- Auction transactions
- Price calculations
- Background tasks
- Authentication failures
- Unexpected errors

External provider failures should be visible without crashing the entire application.

---

# Error Handling

User-facing errors should be understandable.

Do not expose stack traces or internal implementation details to users.

External data failures should degrade gracefully.

For example, if an RSS provider is temporarily unavailable, existing news should remain available and the application should clearly indicate that the feed has not been updated recently.

---

# Development Principles

When implementing a feature:

1. Understand the domain model first.
2. Check existing functionality before creating new abstractions.
3. Prefer extending existing models/services over duplicating logic.
4. Add tests for important behavior.
5. Keep migrations safe and reversible where possible.
6. Avoid unnecessary dependencies.
7. Keep the UI usable on mobile.
8. Preserve historical data.
9. Never silently merge player identities.
10. Never silently alter financial transactions.

---

# Suggested Future Features

The following features should be considered after the initial foundation:

## High Priority

- Player watchlists
- Personal price limits
- Auction strategy profiles
- Player tiers
- Auction notes
- Price history charts
- Squad planning
- Automatic lineup probability
- Injury risk indicators
- Starting XI predictions
- Alerts and notifications
- Import/export of auction data
- Undo/correction workflow for auction transactions

## Medium Priority

- Historical auction database
- League benchmarking
- Anonymous national market statistics
- Auction simulation
- Squad optimization
- Player pairing analysis
- End-of-season performance analysis
- Personalized player recommendations

## Long Term

- Predictive player valuation
- Machine-learning-based price prediction
- Automatic tactical recommendations
- Cross-league statistical benchmarking
- Advanced auction simulations
- Personalized auction strategy optimization

AI-generated recommendations should always be presented as recommendations, not facts.

---

# Initial MVP

The first version should focus on the following workflow:

1. Create a user account.
2. Create a fantasy league.
3. Configure league rules and budget.
4. Select the season.
5. Import or create the player list.
6. Resolve player identities.
7. View player information.
8. View previous/current season statistics.
9. View current player status.
10. View player news/RSS.
11. Configure fantasy managers.
12. Start an auction session.
13. Select a player.
14. View suggested price.
15. View market price information.
16. Record the winning manager.
17. Record the winning bid.
18. Automatically update the manager's budget.
19. Add the player to the manager's roster.
20. Mark the player as unavailable.
21. Continue with the next player.
22. Review the complete auction history.

Everything else should be built around making this workflow reliable and fast.

---

# Definition of Done

A feature is not considered complete simply because it works in the happy path.

Before considering a feature complete, verify:

- It works on desktop.
- It works on mobile.
- It has appropriate automated tests.
- It respects league isolation.
- It preserves historical data.
- It handles invalid input.
- It does not introduce player identity ambiguity.
- It does not introduce unnecessary dependencies.
- It has reasonable database performance.
- Important business rules are enforced server-side.
- User permissions are respected.
- Errors are handled gracefully.

---

# Guiding Principle

The application should behave like a knowledgeable fantasy football analyst sitting beside the manager during the auction.

It should provide:

- Relevant information
- Context
- Statistics
- News
- Market intelligence
- Price recommendations
- Budget awareness
- Warnings
- Historical data

But the final decision must always remain with the fantasy manager.

Correctness and trust are more important than feature count.