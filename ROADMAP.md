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

13. `feature/cli-adapter`: the counter from the terminal (`ski_rental available | customer |
    rent | return`). Plain argparse adapter in `rental/adapters/inbound/cli/`, use cases
    injected from `config/cli.py`, started by a thin management command in `config/`.

    How to try it (each step prints the ids needed by the next one):

    ```bash
    # 1. List available items, copy an item id
    docker compose run --rm web python manage.py ski_rental available --type skis --range sport
    # 2. Register the customer, copy the customer id
    docker compose run --rm web python manage.py ski_rental customer --name "Alex Martin" --height 175 --boots 26.5 --level intermediate
    # 3. Rent: starts today, --until is the last day (YYYY-MM-DD)
    docker compose run --rm web python manage.py ski_rental rent --customer <customer-id> --items <item-id> <item-id> --until <YYYY-MM-DD>
    # 4. Return, optionally flagging damaged items
    docker compose run --rm web python manage.py ski_rental return <rental-id> --damaged <item-id>
    ```

    The rental shows on the dashboard and the Rentals page; after the return, its items are
    on the Maintenance page.
14. `feature/csv-import-adapter`: import a group (e.g. a ski school class arriving at the shop),
    one rental per child. Plain Python adapter in `rental/adapters/inbound/csv_import/`, used by
    an "Import a group" web page. For each line it calls existing use cases only:
    `RegisterCustomer`, `RecommendEquipment` (closest-fitting available skis or snowboard, boots,
    and a helmet if asked), then `CreateRental`. A wrong file rents nothing (problems listed by
    line); a child who cannot be equipped is reported, the others are still rented.

    Unmatched children stay visible until they are handled, without leaving the report:
    - **Fit by hand** opens a modal dialog with the usual equipment choice for that child
      (recommendation, available items, "Other available equipment"). After **Create rental**
      the dialog closes and only that child's row is updated (equipment and price), with HTMX.
    - **Not renting** marks the row as handled. In this branch it does not delete anything
      (deleting the customer needs a core change, see 14b).
    - A banner shows how many children still need equipment, and turns green once every row is
      equipped or marked "Not renting". While rows are unresolved, leaving the page asks for
      confirmation. Links and buttons are not disabled: the back button or closing the tab
      would bypass a lock anyway.
    - Core unchanged: only `CreateRental` and the other existing use cases are called.

    How to try it:

    ```bash
    # 1. Start from the demo data
    docker compose run --rm web python manage.py flush --no-input
    docker compose run --rm web python manage.py seed_demo
    docker compose up
    ```

    2. Open http://localhost:8000/rentals/ → **Import a group**.
    3. Upload `examples/ski_school_group.csv` (5 children), keep today as the last day.
    4. Expected report: **4 of 5 children equipped**, banner "1 child still needs equipment".
       Inès (150 cm) gets "No available skis in a fitting size and range."
    5. Click **Fit by hand** for Inès: pick skis under "Other available equipment", **Create
       rental**. The dialog closes, her row shows the equipment, the banner turns green.
       (Or click **Not renting**: her row is marked as handled.)
    6. Before that, try leaving the page: the browser asks for confirmation.
    7. The new rentals are on the dashboard and the Rentals page.
14b. `feature/remove-customer` (core change): a new `RemoveCustomer` use case. Domain rule:
    only a customer who never rented can be removed, so a mistake cannot erase the history of
    a real rental. Needs a `delete` method on the `CustomerRepository` port, implemented by the
    in-memory and ORM adapters (and covered by the repository contract tests), plus a way to
    know whether a customer has rentals (`RentalRepository.has_rentals_for`). Then **Not
    renting** in the group import really deletes the customer, after a confirmation, so no
    unused customer records are left (also better for personal data). The core diff is not
    empty here, by design: this is a new business capability.

    How to try it:

    1. Same start as step 14: `flush --no-input`, `seed_demo`, `docker compose up`, then
       upload `examples/ski_school_group.csv` under Rentals → **Import a group**.
    2. For Inès, click **Not renting** and confirm: her cell becomes "Not renting. Customer
       removed." and the banner turns green.
    3. Her customer record is gone: the "Fit by hand" link for her would now be a 404.
    4. The rule is checked by the domain: a customer who rented can never be removed
       (covered by `tests/unit/application/test_remove_customer.py`).
15. `feature/json-api-adapter`: JSON API, e.g. for a self-service tablet in the shop.

Outbound (swap the technology behind existing ports):

16. `feature/mongo-adapters`: MongoDB repositories (pymongo), selectable in `bootstrap.py`.
17. `feature/email-notifier`: `EmailNotifier` replacing `LoggingNotifier`.
18. `feature/editable-price-list`: `DjangoPriceListRepository` replacing `StaticPriceList`,
    new inbound ports `GetPriceList` and `UpdatePriceList` (validation: no negative prices),
    and a web screen to view and edit prices. Use case tests + ORM adapter integration tests.
    The core diff only shows **new** files (the new use cases); existing services and
    `PricingPolicy` stay unchanged.

## Phase 5: Design (at the end)

19. `feature/design`: one pass over the look of every screen, web adapter only (core unchanged).
    Includes:
    - Totals at the top of the lists: Rentals ("3 active rentals · 1 due back today ·
      1 overdue"), Inventory ("25 items available", following the filters), and on the
      dashboard in each section title ("Overdue (1)", "Due back today (1)",
      "In maintenance (4, 1 to repair)").

## Phase 6: CD (to discuss at the end)

20. `chore/cd`
    Deploy the app automatically from `main` (hosting target to decide), so the README
    can link to a live demo.

## Later (business changes, the core will change)

These need new business capabilities, so they are not pure adapter swaps:

- Reservations for a future period (online booking, partner webhooks): availability
  will then use `RentalPeriod` overlaps.
- Staff authentication.
- Payments and deposits, season rentals, multiple shops.
- Customer contact and identity details: phone number, email address, postal address and
  ID card number, recorded when the customer is registered. Needed to call a customer with
  an overdue rental, and to identify who holds the equipment. The ID card number is personal
  data under the GDPR: decide what is really needed, how long it is kept, and who can see it.
- `FindCustomers` use case (search by name, later also by phone or email): a customer list,
  finding children not fitted after a group import, and avoiding duplicate customers when a
  group file is imported again.
- Ski boots and snowboard boots as two different kinds of equipment. Today they are one
  `BOOTS` type everywhere, but they are not interchangeable: a ski boot clips into a ski
  binding, a snowboard boot into a board binding. Touches the whole app:
  - Domain: `SKI_BOOTS` and `SNOWBOARD_BOOTS` types (both sized in mondopoint, both ranged);
    the recommendation suggests the boots matching the board; the package discount becomes
    "skis + ski boots" or "snowboard + snowboard boots"; a rental should not mix a snowboard
    with ski boots.
  - Price list: separate prices for each kind of boots.
  - ORM: a data migration turning existing `boots` into one of the two types.
  - Screens, CLI, CSV import and demo data: the two kinds shown and chosen separately.
