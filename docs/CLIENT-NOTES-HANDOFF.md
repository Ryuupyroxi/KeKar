# Client testing notes — Lite/production handoff

All eleven notes are implemented and committed on `calendar-and-labels`. No
release tag was moved and no build was pushed: the client tests first.

## Work order and commits

| # | Client note | Commit |
|---|---|---|
| 1 | Lease > Property selector populated | `1cb5bda` |
| 2 | Applicants > Property live dropdown | `940c289` |
| 3 | Garage size + street/driveway parking | `1ef2f81` |
| 4 | Pet policy + $300 refundable deposit in lease | `56ee8b5` |
| 5 | Dark/OLED text contrast | `7f2bae9` |
| 6 | Label on property-panel collapse button | `18a61e9` |
| 7 | Stays merged into Calendar + Help legend | `5369b02` |
| 8 | Selected property emphasised on calendar | `a0996e7` |
| 9 | One address line carries both move dates | `d4a066a` |
| 10 | Clicking a date names its property | `e592656` |
| 11 | Applicant profile opens on single click | `a8c6754` |

## Verification evidence

- Full suite (default/full variant): **473 passed**
  `.venv/bin/python -m pytest -o addopts='' -q`
- Lite/production targeted suite: **103 passed**
  `KEKAR_VARIANT=lite .venv/bin/python -m pytest -o addopts='' -q
  tests/test_features.py tests/test_kekar_lite.py tests/test_lite_ui.py
  tests/test_tour.py tests/test_calendar_tab.py tests/test_main_cli.py
  tests/test_set_variant.py tests/test_usb_packaging.py
  tests/test_bundle_safety.py tests/test_button_feedback.py
  tests/test_testing_notes.py`
- Every note has a regression in `tests/test_testing_notes.py`; each was run
  red before the fix and green after it.
- Real-display widget grabs of the current source with seeded data confirmed
  the Calendar tab (green/red/purple highlights, Dates + Short stays panels,
  date-detail label) and the Applicants tab (single-click profile form).

## Bugs found and fixed along the way

- The Lite `MainWindow` returned early when there was no chat pane, so the
  property-panel toggle kept an empty label and tooltip.
- Placeholder text inherited the platform's dark colour under dark/OLED
  themes; the app palette now sets `PlaceholderText` from the active palette.
- `test_short_stay.py` and `test_ui_behaviour.py` contain full-build-only
  assertions and are deliberately not part of the Lite-targeted suite.

## Re-check commands

Run the two commands above. For a real-display check against the current
source, use the configured package data directory and `DISPLAY=:0` with
`KEKAR_TESTING=1`; do not point at a stale frozen binary. Bundle freshness is
covered by `tests/test_bundle_safety.py` and
`~/.hermes/profiles/fenrys/skills/software-development/kekar/scripts/bundle_source_diff.py`.
