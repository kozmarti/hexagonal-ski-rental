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
    Plain Django `JsonResponse` views in `rental/adapters/inbound/api/`, use cases injected from `config/urls.py`:
    `GET /api/equipment/`, `POST /api/customers/`, `GET /api/customers/<id>/recommendation/`,
    `POST /api/rentals/`, `POST /api/rentals/<id>/return/`. Errors as JSON: 400 invalid request
    (per field), 404 not found, 409 business rule.

    How to try it:

    ```bash
    # 0. Without the key: 401
    curl -i http://localhost:8000/api/equipment/
    # 1. Available sport skis: copy an item id
    curl -H "Authorization: Bearer dev-tablet-key" "http://localhost:8000/api/equipment/?type=skis&range=sport"
    # 2. Register a customer: copy the id
    curl -X POST http://localhost:8000/api/customers/ -H "Authorization: Bearer dev-tablet-key" \
      -H "Content-Type: application/json" \
      -d '{"name": "Alex Martin", "height_cm": 175, "boot_size": 26.5, "skill_level": "intermediate"}'
    # 3. Recommendation for that customer
    curl -H "Authorization: Bearer dev-tablet-key" http://localhost:8000/api/customers/<customer-id>/recommendation/
    # 4. Rent (starts today, end_date is the last day): copy the rental id
    curl -X POST http://localhost:8000/api/rentals/ -H "Authorization: Bearer dev-tablet-key" \
      -H "Content-Type: application/json" \
      -d '{"customer_id": "<customer-id>", "equipment_ids": ["<item-id>"], "end_date": "<YYYY-MM-DD>"}'
    # 5. Return, flagging damaged items
    curl -X POST http://localhost:8000/api/rentals/<rental-id>/return/ -H "Authorization: Bearer dev-tablet-key" \
      -H "Content-Type: application/json" -d '{"damaged_equipment_ids": ["<item-id>"]}'
    ```

    The rental shows on the dashboard like any other one.
15b. `feature/qr-labels`: QR code stickers on the equipment, web adapter only (core unchanged).
    Each sticker holds a link to the item's page (`/scan/<id>/`). Every item in use is found by
    combining `ListAvailableEquipment`, `GetDashboard` (rented items, inside their rentals) and
    `ListEquipmentInMaintenance`.
    - **Labels for any item** (Inventory → Print labels): available, rented or in maintenance,
      filtered by status, type and range; 50 x 30 mm stickers.
    - **A "QR" button on every item** (Inventory, Rentals, Maintenance): a dialog with the
      item's QR code, its status and **Print this label**.
    - **Scan** in the menu bar: scanning an item opens its page with the one action that makes
      sense now: **Return** its rental, **Maintenance done**, or **Rent it** (the item is then
      already ticked on the equipment step, after the customer step).
    - **Counter page**: scanning items ticks them in the rental being prepared.
    - Free only: `segno` for the QR codes (SVG, server side); a **phone's own camera app** opens
      the sticker's link (no HTTPS needed); camera in the page with `html5-qrcode` (needs HTTPS,
      or localhost); a USB or Bluetooth barcode scanner also works (it types like a keyboard).
      One shared script, `static/rental/scan.js`. `LABELS_BASE_URL` sets the address printed in
      the stickers, reachable by the phones.

    How to try it:

    ```bash
    # 1. segno is a new dependency: rebuild the image
    docker compose build web
    # 2. Demo data, then start the app
    docker compose run --rm web python manage.py seed_demo
    docker compose up
    ```

    3. Inventory → **Print labels**: a QR sticker for every item, whatever its status.
    4. Click **QR** next to any item (Inventory, Rentals, Maintenance): its code in a dialog.
    5. **Scan** in the menu: paste an item id (or its sticker link) and press Enter, or use
       **Camera** on this computer (localhost): the item's page opens with its action.
    6. With a phone on the same Wi-Fi: set `LABELS_BASE_URL=http://<this computer's IP>:8000`
       and add that IP to `DJANGO_ALLOWED_HOSTS` in `.env`, restart, reload the labels, then
       scan a sticker with the phone's camera app: the item's page opens.

Outbound (swap the technology behind existing ports):

16. `feature/mongo-adapters`: MongoDB repositories (pymongo), selectable in `bootstrap.py`.
    MongoDB 7 runs as a single-node replica set (transactions need one). `MongoEquipmentRepository`,
    `MongoCustomerRepository`, `MongoRentalRepository` and `MongoUnitOfWork` implement the same
    ports as the ORM ones; a rental and its items are **one document** (two tables in PostgreSQL).
    `REPOSITORY_BACKEND=orm|mongo` is read only by `bootstrap.py`. The repository contract tests
    run on in-memory, PostgreSQL and MongoDB.

    How to try it:

    ```bash
    # 1. pymongo is a new dependency, MongoDB a new container
    docker compose build web
    # 2. Set REPOSITORY_BACKEND=mongo in .env, then empty MongoDB and load the demo data
    docker compose run --rm web python manage.py flush_mongo
    docker compose run --rm web python manage.py seed_demo
    # 3. Start the app: screens, CLI, API and QR codes now work on MongoDB
    docker compose up
    # 4. Look at a rental document: its items are inside it
    docker compose exec mongo mongosh ski_rental --eval "db.rentals.findOne()"
    ```

    Set `REPOSITORY_BACKEND=orm` again (and restart) to go back to PostgreSQL: each database
    keeps its own data.
17. `feature/email-notifier`: `EmailNotifier` next to `LoggingNotifier`, two adapters of the
    `Notifier` port. `NOTIFIERS=logging|email|logging,email` is read only by `bootstrap.py`;
    with both, a `CompositeNotifier` passes each event to both. Emails go to the shop
    (`SHOP_EMAIL`): customers have no email address yet. An email that cannot be sent is logged
    and never breaks a rental. In development, Mailpit catches every email (nothing is sent).

    How to try it:

    ```bash
    # 1. Set NOTIFIERS=logging,email in .env, then start the app (Mailpit is a new container)
    docker compose up
    ```

    2. Create and return a rental (counter, CLI or API).
    3. Open the Mailpit inbox at http://localhost:8025: one email per event ("Rental created",
       "Rental returned", "🔧 Repair needed"...). The same events are still in the app's log.
18. `feature/editable-price-list`: a **Pricing** page (menu bar) to view and edit every rate.
    New inbound ports `GetPriceList` and `UpdatePriceList`; `PriceListRepository` gets
    `save()`, implemented in PostgreSQL (`DjangoPriceListRepository`, `price` table) and MongoDB
    (`MongoPriceListRepository`, one `prices` document), so prices follow `REPOSITORY_BACKEND`.
    `StaticPriceList` gives the starting prices until the first save. Domain rules: no negative
    amount, a week cheaper than 6 days, and rates are edited, never added or removed
    (`PriceList.with_rates`). An invalid change saves nothing. Contract tests on in-memory,
    PostgreSQL and MongoDB. The core diff: two new use cases, `save()` on the port and
    `PriceList.with_rates`; existing services and `PricingPolicy` unchanged.

## Phase 5: Design (at the end)

19. `feature/design`: one pass over the look of every screen, web adapter only (core unchanged).
    Includes:
    - **A complete Inventory page**: every item in one table with its status (available,
      rented by whom and until when, in maintenance), a status filter and totals per status.
      Built by combining `ListAvailableEquipment`, `GetDashboard` and
      `ListEquipmentInMaintenance`.
    - **Status badges**, the same everywhere: Available 🟢 green, Rented ⚪ grey,
      Maintenance 🟠 orange, 🔧 Repair 🔴 red, Overdue 🔴 red (red only for what needs a person
      to act).
    - **Totals at the top of the lists**: Inventory ("41 items: 25 available, 12 rented,
      4 in maintenance", following the filters), Rentals ("3 active rentals · 1 due back today ·
      1 overdue"), Maintenance ("4 items, 1 to repair"), and on the dashboard in each section
      title ("Overdue (1)", "Due back today (1)", "In maintenance (4, 1 to repair)").
    - **Pagination**, 25 rows per page with Previous / Next and "Page 2 of 4", on Inventory,
      Rentals, Maintenance and Labels. Filters and totals apply to the whole list, not only the
      visible page. Done in the web adapter (a slice of the use case's list): fine at a shop's
      size; database-level pagination would need a port change.
    - **Dashboard sections** show their first 10 rows, with a "See all" link to the full,
      paginated page.
    - **Light / dark button** in the menu bar (☾ / ☀): the page follows the device setting until
      the button is clicked; a click switches between light and dark, with Pico.css's
      `data-theme`. The choice is remembered in the browser, per device.
    - **Menu bar**: a line across the window separates it from the page, and the current page
      is clearly marked with a soft tinted background (no underline).

19b. `feature/mobile`: the mobile style, web adapter only. Under 768px wide (Pico's first
    breakpoint):
    - **A tab bar at the bottom** with line icons (like a phone app): Dashboard, Rentals,
      **Scan** (in the middle, a bigger round button: the main action at the counter),
      Inventory, Maintenance. The top bar keeps the logo, Pricing and the light / dark button.
      The current page is marked in both bars from one `menu_section` template filter.
    - **Lists as cards**: Inventory, Rentals, Maintenance, the dashboard's rentals and Pricing.
      Each row becomes a card with its fields in two columns, the column name (`data-label`) in
      small above each value, the buttons side by side. Same HTML table as on a wide screen,
      only CSS changes, so the HTMX row swaps keep working.
    - The dashboard's four counters two by two.
    - Every page checked at phone width: no sideways scrolling (forms, QR dialog, Scan, Pricing).

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
