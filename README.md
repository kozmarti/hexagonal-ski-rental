# hexagonal-ski-rental

A ski and snowboard rental management app for a winter-season shop, built with Django
to demonstrate **hexagonal architecture (ports and adapters)**.

> Work in progress. See the [roadmap](ROADMAP.md).

## Why this project

Rental shops deal with real business rules: equipment availability, sizing and range
recommendations, pricing by range and period, damage and maintenance.

The goal is to keep those rules in a **core that knows nothing about Django, the database
or the UI**, and to show that the technology around it can be swapped (database, notification
channel, new entry points like a CLI or a CSV import) **without changing the core**.

## Architecture

```
            inbound adapters                                outbound adapters
   (Django + HTMX views, CLI, CSV, API)            (ORM, in-memory, logging notifier, ...)
                  │                                                 ▲
                  ▼                                                 │
          ┌─────────────── core ──────────────────────────────────────┐
          │  inbound ports ──► services ──► outbound ports            │
          │                       │                                   │
          │                       ▼                                   │
          │                    domain                                 │
          │      (entities, value objects, business rules)            │
          └───────────────────────────────────────────────────────────┘
```

- **Domain**: the business rules, in pure Python.
- **Inbound ports**: the use cases the app offers (`CreateRental`, `ReturnRental`, ...).
- **Services**: implement the inbound ports, coordinate the domain and the outbound ports.
- **Outbound ports**: what the app needs (`EquipmentRepository`, `Clock`, `Notifier`, ...).
- **Adapters**: concrete technology plugged into the ports. Wiring happens in one place,
  `rental/bootstrap.py`.

```
rental/
  domain/
  application/
    ports/inbound/
    ports/outbound/
    services/
  adapters/
    inbound/web/
    outbound/orm/
    outbound/memory/
    outbound/notifications/
  bootstrap.py
```

The boundaries are enforced automatically with [import-linter](https://github.com/seddonym/import-linter):

- the core (`domain`, `application`) never imports Django
- dependencies always point inward (`adapters → application → domain`)
- inbound and outbound adapters never import each other

## Stack

Python 3.12, Django, HTMX, PostgreSQL, Docker, pytest, import-linter, ruff.

## Getting started

Requires Docker.

```bash
cp .env.example .env
docker compose up --build
```

The app runs on http://localhost:8000.

Run the tests:

```bash
docker compose run --rm web pytest
```

Check the architecture rules:

```bash
docker compose run --rm web lint-imports
```

## Roadmap

The project is built step by step, one branch per step, from the core outward.
See [ROADMAP.md](ROADMAP.md).
