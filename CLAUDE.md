# hexagonal-ski-rental

A ski and snowboard rental management app for a winter-season shop, built with Django
to learn and demonstrate **hexagonal architecture (ports and adapters)**.

The architecture is the point of this project. When in doubt, favor clear boundaries
over Django shortcuts.

## Stack

- Python 3.12+, Django
- Frontend: Django templates + HTMX (server-rendered, no SPA)
- Tests: pytest (+ pytest-django for adapter tests only)
- Boundary enforcement: import-linter

## Domain

Users are **shop staff** at the counter. Rentals are made **in person only**:
a rental always starts today (no booking in advance for a future period).

- **Equipment**: an individually tracked physical item (skis, snowboard, boots, helmet, poles)
  with type, brand/model, size, status and days used. Skis, snowboards and boots also have
  a **range** (gamme); helmets and poles don't.
- **Customer**: name, height, boot size, skill level.
- **Rental**: a customer, a list of equipment items, a rental period, a price and a status
  (active, returned).
- **Value objects**: `RentalPeriod` (knows how to detect overlaps), `Money`, `Size`
  (cm or mondopoint), `SkillLevel` (beginner, intermediate, advanced, expert),
  `Range` (e.g. discovery, sport, premium).

### Business rules

- An item can only be rented when its status is `AVAILABLE`. Since rentals start today,
  the status is enough to decide availability in the MVP.
- `RentalPeriod` still knows how to detect overlaps, kept ready for future reservations,
  but availability does not rely on it yet.
- Equipment lifecycle: `AVAILABLE → RENTED → MAINTENANCE → AVAILABLE`;
  any state can go `→ RETIRED`.
- Only a customer who **never rented** can be removed (`Customer.ensure_can_be_removed`):
  rentals, active or returned, are the shop's history.
- A rental is **overdue** when it is still active after its last day. Overdue is computed
  from today's date (`Rental.is_overdue(today)`), never stored as a status.
- Every returned item goes to maintenance (waxing, sharpening, drying) before it can be
  rented again. A damaged item is also flagged as needing repair; completing maintenance
  clears the flag.
- Price is computed from the equipment **range**, the period (day / week rates)
  and package discounts:
  - Period days are counted with start and end included. A ski week is **Sunday to Friday = 6 days**.
  - Per item: each block of 6 days costs the week rate; remaining days cost the day rate each,
    capped at one week rate.
  - The week rate must be lower than 6 day rates.
  - Package: a rental with skis or a snowboard **and** boots gets 10% off the total.
  - `PricingPolicy` (domain) does the calculation only; the prices themselves come from the
    `PriceListRepository` outbound port. Staff edit them on the Pricing page
    (`GetPriceList` / `UpdatePriceList`). Rates are edited, never added or removed
    (`PriceList.with_rates`), so every type and range always has a price. A rental keeps the
    price it was created with.
- Range recommendation: beginner → discovery, intermediate → sport, advanced / expert → premium.
  It is only a suggestion; staff can rent any range to any customer.
- Size recommendation: ski and board length from height and level.
  - Skis: height − 15 cm (beginner), − 10 (intermediate), − 5 (advanced), − 0 (expert).
  - Snowboard: height − 25 cm (beginner), − 20 (intermediate), − 15 (advanced, expert).
  - Boots: the customer's boot size.
  - An item fits when it is in the recommended range and its size is within ± 5 cm
    (skis, snowboards) or ± 0.5 mondopoint (boots).

## MVP scope

1. Inventory: register equipment, list it by type, size and status.
2. Register a customer.
3. Create a rental at the counter (customer, range and size recommendation, available items,
   period starting today, price).
4. Return a rental: every item goes to maintenance, damaged items are flagged for repair.
5. Complete maintenance (item goes back to available).
6. Dashboard: currently rented, due back today, overdue, in maintenance.
7. Notifications through the `Notifier` port, with a **logging adapter only** (no external service).
   Events: rental created, rental returned, item sent to maintenance, maintenance completed.

**Out of scope for now**: online booking and reservations for a future period, payments and deposits,
season rentals, multiple shops, emails to customers and SMS,
staff authentication, DIN calculation. These are future adapters/features, so don't build them unless asked.

The step-by-step branch plan is in [ROADMAP.md](ROADMAP.md).

## Architecture

Dependencies always point **inward**: adapters → application → domain.

```
rental/
  domain/              # entities, value objects, business rules (pure Python)
  application/
    ports/inbound/     # use case interfaces: CreateRental, ReturnRental, ...
    ports/outbound/    # what the app needs: EquipmentRepository, Clock, ...
    services/          # use case implementations (implement inbound ports, use outbound ports)
  adapters/
    inbound/web/       # Django views + HTMX templates (call inbound ports)
    inbound/cli/       # command-line adapter (plain argparse, call inbound ports)
    inbound/csv_import/  # group import from a CSV file (plain Python, call inbound ports)
    inbound/api/       # JSON API (Django JsonResponse views, call inbound ports)
    outbound/orm/      # Django models + ORM repositories (implement outbound ports)
    outbound/mongo/    # MongoDB repositories + unit of work (pymongo, same outbound ports)
    outbound/memory/   # test adapters: in-memory repositories, unit of work, FixedClock, RecordingNotifier
    outbound/price_list/     # StaticPriceList (the starting prices)
    outbound/clock.py        # SystemClock (today in the shop's time zone)
    outbound/notifications/  # LoggingNotifier, EmailNotifier, CompositeNotifier (both at once)
  bootstrap.py         # composition root: wires outbound adapters into services
config/                # wiring and dev tooling, outside the hexagon (may import bootstrap.py)
  urls.py              # injects the use cases from bootstrap.py into the views
  cli.py               # injects the use cases from bootstrap.py into the CLI adapter
  management/commands/ski_rental.py  # starts the CLI adapter
  management/commands/seed_demo.py   # demo data, created through the use cases
```

Code inside `rental/` never imports `bootstrap.py`; only `config/` does.

### Ports

- **Inbound** (what the app offers): `RegisterEquipment`, `ListAvailableEquipment`,
  `RegisterCustomer`, `RemoveCustomer`, `RecommendEquipment`, `CreateRental`, `ReturnRental`,
  `ListEquipmentInMaintenance`, `CompleteMaintenance`, `GetDashboard`, `GetPriceList`,
  `UpdatePriceList`.
- **Outbound** (what the app needs): `EquipmentRepository`, `RentalRepository`,
  `CustomerRepository`, `PriceListRepository`, `Clock`, `Notifier`, `UnitOfWork` (when atomic multi-entity writes are needed).

Ports are defined as `typing.Protocol` classes. Both inbound and outbound ports are explicit.

### Adapters

- **Inbound**: Django + HTMX views for shop staff.
  - Styling: Pico.css (CDN), top menu bar in `base.html`; each new screen adds its link there.
  - Django forms only parse and check the input format, then build the command
    (`form.to_command()`). Domain errors are caught in the view and shown on the form.
  - Every page works without JavaScript (normal GET/POST, redirect after a successful POST).
    With HTMX, the view returns only the changed fragment (`_*.html` templates).
  - Small page scripts are plain JavaScript in `web/static/rental/` (no framework), like
    `scan.js` for QR scanning. They never insert database text as HTML.
  - QR labels and scan pages: `web/scanning.py` (`segno` for the codes, free libraries only).
- **Inbound, other entry points** (same use cases, same injection pattern):
  - CLI (`inbound/cli/`, plain argparse) and group CSV import (`inbound/csv_import/`).
  - JSON API (`inbound/api/`): `parsing.py` turns JSON into commands (400 with errors per field),
    `serialization.py` turns results into JSON; `ApiView` maps errors to 400 / 404 / 409.
    CSRF-exempt because it uses no cookie sessions. Every request needs a device API key
    (`Authorization: Bearer <key>`, keys from the `API_KEYS` setting, injected into `ApiView` as
    `api_keys`): 401 otherwise, and no keys configured means no access. When staff authentication
    arrives, the API keeps token authentication, never cookies.
- **Outbound**:
  - Repositories: Django ORM on PostgreSQL or MongoDB (production, chosen by
    `REPOSITORY_BACKEND=orm|mongo`, read only in `bootstrap.storage()`), in-memory (tests).
    In-memory repositories store copies, so a change is only kept when `save()` is called,
    like a real database.
  - `UnitOfWork`: `transaction.atomic()` (ORM), a MongoDB transaction (`MongoUnitOfWork`, needs
    the replica set), `InMemoryUnitOfWork` (tests). Mongo repositories and their unit of work
    share a `MongoContext`, which holds the transaction's session.
  - `PriceListRepository`: `DjangoPriceListRepository` or `MongoPriceListRepository` (editable,
    following `REPOSITORY_BACKEND`), starting from `StaticPriceList`'s prices until the first
    save; `InMemoryPriceList` and the test price list in tests.
  - `Clock`: `SystemClock` (production), `FixedClock` (tests).
  - `Notifier`: `LoggingNotifier` (Python `logging`, the default) and `EmailNotifier` (Django's
    email, to the shop's `SHOP_EMAIL`; a sending failure is logged, never raised), chosen by
    `NOTIFIERS=logging|email|logging,email`, read only in `bootstrap.notifier()`. Several at once
    go through `CompositeNotifier`. `RecordingNotifier` in tests. In development, Mailpit catches
    every email (http://localhost:8025). No SMS or other external integration unless asked.

### Rules

- `domain/` and `application/` must **never** import Django (enforced by import-linter).
- Django ORM models live only in `adapters/outbound/orm/`. They are persistence details,
  not the domain. Repositories map ORM models ↔ domain entities.
- Use cases take a simple **command** dataclass and return a result dataclass.
  No `HttpRequest`, no ORM models, no querysets cross the port boundary.
- Never call `date.today()` / `datetime.now()` in the core; use the `Clock` port.
- The `Notifier` port receives domain-level notifications (e.g. a `RentalCreated` dataclass),
  never pre-formatted messages. Formatting belongs in the adapter.
- Views never build adapters and never import `bootstrap.py`. Each view **receives** its use
  cases (inbound ports) by injection, e.g. `DashboardView.as_view(get_dashboard=bootstrap.get_dashboard)`.
  This wiring lives in `config/urls.py`, outside the hexagon, so inbound adapters only know ports
  and the "inbound and outbound adapters are independent" import-linter rule stays strict
  (no ignored imports).
- Business rules belong in the domain, not in views, forms or ORM models.
- Domain errors are raised as domain exceptions; inbound adapters translate them
  into HTTP responses / messages.

### Repositories

- Entity ids are **UUIDs generated by the domain** when the entity is created,
  never by the database (no auto-increment ids in the core).
- Repository methods express **business intent** (`find_available(...)`,
  `find_rentals_overlapping(item_ids, period)`, `find_due_back_on(date)`),
  never generic or storage-shaped filters.
- **One repository per aggregate root, not per table**: a `Rental` and its rented items
  are loaded and saved together by `RentalRepository`.
- Repositories store and retrieve; they never apply business rules.
- Only **services** use repositories. Domain entities never call a repository.
- Atomic writes across several aggregates go through `UnitOfWork`.

## Testing

- Every branch includes tests for the code it adds or changes. No code without tests.
- A branch is mergeable only when CI is green (ruff, lint-imports, pytest).
- A bug fix starts with a test that reproduces the bug.

- **Domain + use cases**: plain pytest with in-memory adapters, `StaticPriceList`, `FixedClock`
  and `RecordingNotifier`.
  No database. These are the majority of the tests.
- **Repository contracts** (`tests/contract/`): one set of tests runs against every adapter
  of the repository ports (in-memory, ORM and MongoDB). A new repository adapter must pass them
  too. MongoDB tests get a database of their own (`mongo_context` fixture), dropped afterwards.
- Tests never follow the `.env` choice of database: `tests/conftest.py` forces
  `REPOSITORY_BACKEND=orm` for every test, and MongoDB tests opt in explicitly. Tests must never
  touch the developer's own data.
  Compare entities with all their fields, not only by id.
- **ORM adapters**: a small number of pytest-django integration tests (unit of work, bootstrap).
- **Web adapters**: a few tests checking that views call the right use case and render results.
  Inject a fake use case into the view, so these tests need no database.

## Commands

Everything runs in Docker (Python 3.12 + PostgreSQL 16). First time: `cp .env.example .env`.

- Start the app (runs migrations, then serves on http://localhost:8000): `docker compose up --build`
- Run tests: `docker compose run --rm web pytest`
- Check architecture boundaries: `docker compose run --rm web lint-imports`
- Lint: `docker compose run --rm web ruff check .`
- Format: `docker compose run --rm web ruff format .` (CI runs `ruff format --check .`)

CI (GitHub Actions, `.github/workflows/ci.yml`) runs ruff, lint-imports, a check that
migrations are up to date, and pytest on every pull request and on pushes to `main`.
- Create migrations: `docker compose run --rm web python manage.py makemigrations`
- Fill an empty database with demo data: `docker compose run --rm web python manage.py seed_demo`
- Empty the database: `docker compose run --rm web python manage.py flush --no-input`
  (PostgreSQL), `docker compose run --rm web python manage.py flush_mongo` (MongoDB)
- The counter from the terminal: `docker compose run --rm web python manage.py ski_rental --help`
  (`available`, `customer`, `rent`, `return`)

Demo and test data are always created **through the use cases** (like `seed_demo`), never with
`loaddata` fixtures or direct table writes: the domain checks the data, and it keeps working
when the database adapter changes.

Django apps are the adapters themselves: `rental.adapters.outbound.orm` (models, migrations)
and `rental.adapters.inbound.web` (views, templates). The core is not a Django app.
