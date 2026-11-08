# Roadmap

One branch per step, merged into `main` through a pull request.
Order follows the hexagon from the center outward:
domain → ports (in and out) → services → outbound adapters → inbound adapters.

## Phase 0: CI

0. `chore/ci`
   GitHub Actions workflow on every push and pull request: `ruff` (lint + format check),
   `lint-imports` (architecture rules) and `pytest` (with a PostgreSQL service).
   Add `ruff` to the project dependencies and config.

## Phase 1: Core (no Django, no database)

1. `feature/domain-model`
   Entities (`Equipment`, `Customer`, `Rental`), value objects (`RentalPeriod`, `Money`, `Size`,
   `SkillLevel`, `Range`), `PricingPolicy`, domain exceptions. Unit tests.

2. `feature/outbound-ports`
   Outbound ports: `EquipmentRepository`, `RentalRepository`, `CustomerRepository`,
   `PriceListRepository`, `Clock`, `Notifier`, `UnitOfWork`.
   Adapters: in-memory repositories, `StaticPriceList`, `FixedClock`, `RecordingNotifier`.

3. `feature/inventory-and-customer-use-cases`
   Inbound ports: `RegisterEquipment`, `ListAvailableEquipment`, `RegisterCustomer`.
   Services + tests.

4. `feature/rental-use-cases`
   Inbound ports: `RecommendEquipment`, `CreateRental`, `ReturnRental`.
   Services (availability, pricing by range, damage → maintenance, notifications) + tests.

5. `feature/maintenance-use-cases`
   Inbound ports: `ListEquipmentInMaintenance`, `CompleteMaintenance`. Services + tests.

6. `feature/dashboard-use-case`
   Inbound port: `GetDashboard` (currently rented, due back today, in maintenance). Service + tests.

## Phase 2: Outbound adapters (production)

7. `feature/orm-adapters`
   Django models, migrations, ORM repositories, `UnitOfWork` (`transaction.atomic()`),
   `SystemClock`, wiring in `bootstrap.py`. Integration tests.

8. `feature/logging-notifier`
   `LoggingNotifier`, wired in `bootstrap.py`. Tests.

## Phase 3: Inbound adapters (Django + HTMX)

Each step includes view tests (the view calls the right use case and renders its result).

9.  `feature/web-inventory`: inventory screens → `RegisterEquipment`, `ListAvailableEquipment`
10. `feature/web-rentals`: counter screen → `RegisterCustomer`, `RecommendEquipment`,
    `CreateRental`, `ReturnRental`
11. `feature/web-maintenance`: maintenance list → `ListEquipmentInMaintenance`, `CompleteMaintenance`
12. `feature/web-dashboard`: dashboard → `GetDashboard`

**MVP is complete here.**

## Phase 3b: Demo data

12b. `chore/demo-data`
     `seed_demo` command filling an empty database with demo equipment, customers and
     rentals in every state (out, due back today, overdue, returned with a repair or a service).
     Everything is created through the use cases. Lives in `config/` (dev tooling, outside
     the hexagon). Integration test.

## Phase 4: Demonstration (swap and add adapters, core unchanged)

Each branch adds or swaps adapters only. Proof that the core did not change:

```bash
git diff main..<branch> -- rental/domain rental/application
```

must be empty (only adapters and `bootstrap.py` change).
Each branch includes tests for the new adapter.

Inbound (new ways to create rentals, all calling the same `CreateRental` port):

13. `feature/cli-adapter`: management command to create a rental from the terminal.
14. `feature/csv-import-adapter`: import a group (e.g. a ski school class arriving at the shop),
    one `CreateRentalCommand` per line.
15. `feature/json-api-adapter`: JSON API, e.g. for a self-service tablet in the shop.

Outbound (swap the technology behind existing ports):

16. `feature/mongo-adapters`: MongoDB repositories (pymongo), selectable in `bootstrap.py`.
17. `feature/email-notifier`: `EmailNotifier` replacing `LoggingNotifier`.
18. `feature/editable-price-list`: `DjangoPriceListRepository` replacing `StaticPriceList`,
    new inbound ports `GetPriceList` and `UpdatePriceList` (validation: no negative prices),
    and a web screen to view and edit prices. Use case tests + ORM adapter integration tests.
    The core diff only shows **new** files (the new use cases); existing services and
    `PricingPolicy` stay unchanged.

## Phase 5: CD (to discuss at the end)

19. `chore/cd`
    Deploy the app automatically from `main` (hosting target to decide), so the README
    can link to a live demo.

## Later (business changes, the core will change)

These need new business capabilities, so they are not pure adapter swaps:

- Reservations for a future period (online booking, partner webhooks): availability
  will then use `RentalPeriod` overlaps.
- Staff authentication.
- Payments and deposits, season rentals, multiple shops.
