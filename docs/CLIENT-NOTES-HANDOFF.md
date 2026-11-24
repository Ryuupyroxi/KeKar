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
- Real-pointer click-through with `xdotool` against the current source on
  `:0` (throwaway copy of the seeded data, `KEKAR_TESTING=1`) confirmed:
  Calendar tab click → active tab 3; property row click → selected id 3;
  Dec 15 date click → "2026-12-15: Move-in — 14 Maple Street"; Applicants
  tab click → active tab 1; row click → profile visible; typed name → saved
  with status "Saved Pointer Test."; sidebar toggle → collapsed then
  expanded; Help → Calendar legend opened and was dismissed. Every pointer
  position reported the app's own window id before the click. The test
  process was killed afterwards.

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


## Real-world scenarios tried

A visible eight-step journey was played on `:0` against a throwaway copy of
the seeded data while Master watched the screen:

1. Open Properties.
2. Landlord saves a pet-friendly rental with a 2-car garage and driveway.
3. Calendar shows both move dates on one line.
4. Lease generates with the pet-deposit clause and tenant name.
5. Applicant profile opens on one click, is edited and saved.
6. Short stay is booked; a mid-stay date identifies the property and guest.
7. OLED theme applies.
8. Help → Calendar legend opens and dismisses.

These are also durable regressions in `tests/test_real_world_scenarios.py`.
The journey exposed one real defect: `CalendarTab` only mapped a short stay's
check-in date to its property label, so clicking a middle booked day said "no
stay recorded" even though the day was purple. It now records every booked day.

Final counts after the fix: full suite 477 passed; Lite/production targeted
suite 107 passed. Commit `9e56040` adds the scenarios and the fix.


## Guided tour review

The 11-step tour now names every shipped feature: property search and
selection, garage/parking/pet policy in the details form, the applicants
dropdown and single-click profile, lease generation with the pet-deposit
clause, the combined Calendar/short-stay panel with one-line move dates and
date identification, themes, the labelled panel toggle, Help legend and demo
mode. `test_tour.py` guards the wording in both variants.

A real-pointer walkthrough on `:0` clicked Next through all 11 steps and
Finish back to the app. That exposed a genuine defect: the last button read
"Finish" but was wired to `next()`, which does nothing past the final step.
It now calls `finish()`. Full suite 478 passed; Lite/production targeted
suite 108 passed.


## Lite/production build installed locally

The menu entry for the experimental build pointed at
`dist/KeKar/KeKar`. Lite was only a portable folder and had no launcher.
A fresh Lite production bundle was rebuilt from the current checkout, verified
identical to source with `bundle_source_diff.py`, and installed at:

- Bundle: `/home/Ryuu/Documents/kekar project/out/KeKarLite_Linux/`
- Launcher: `/home/Ryuu/Documents/kekar project/out/KeKarLite_Linux/KeKarLite.sh`
- Menu: "KeKar Lite (Production)" via
  `~/.local/share/applications/kekar-lite.desktop`
- Desktop copy: `~/Desktop/kekar-lite.desktop`

The seeded `KeKarData` folder was preserved across the swap. A launch check
showed the active window title "KeKar — KeKar Lite Property Manager"; the
throwaway instance was closed. No release tag or remote was touched.


## Test data and assistant check

Added QA records to the installed Lite/production database through its
repositories: 7 properties (including pet-friendly rentals, garage/parking
combinations and a short-stay house), 4 applicants and 2 short-stay bookings.
The frozen Lite app was launched and OCR of the real window confirmed the
property list shows all seven addresses. It was closed afterward.

At this point Lite had no assistant, so the assistant was first checked in the
full/experimental build that is in the menu:

- Direct agent run against the configured OpenRouter key: model
  `openrouter/free`, 1 tool call, correct property answer.
- Source UI path: typed a question into ChatPane and got "$500/month".
- Frozen `dist/KeKar/KeKar` launched on the real display: typed "What is the
  rent on my first property?" into the chat input and read the answer
  "The rent on your property at 1023 East Tenth is $500/month" from the
  screen. The frozen app was closed afterward.

No API key was printed or written anywhere. The two short test conversations
remain in the experimental build's chat history as evidence. The assistant
took about 30-40 seconds on the frozen build, so "Thinking..." is not a hang.


## Assistant enabled in Lite with the experimental key

Per instruction, `features.chat_enabled()` now returns True in both builds.
Lite keeps its other restrictions: no Marketplace autofill, no portal sync, no
Maps lookup and no hidden listing channels. The OpenRouter key, provider,
base URL and model chain were copied from the experimental build's settings
into Lite's encrypted settings without printing the key.

The Lite bundle was rebuilt, verified identical to source, and relaunched on
the real display. Typing "How many properties are in my portfolio?" into its
chat input produced: "You have 7 properties in your portfolio, and all 7 are
currently listed as vacant." The app was closed afterward. Full suite 478
passed; Lite/production targeted suite 145 passed. No release tag or remote
was touched.


## Private upload packages and key audit

Audit before packaging: the configured key was searched in all 175 tracked
files and full git history (no exact key and no key-like strings). GitHub code
search for the exact key, `sk-or-v1` and `sk-proj` in `Ryuupyroxi/KeKar`
returned 0 results after pushing the current branch. The key exists only in
encrypted `KeKarData/config/settings.enc` beside its `app.key`; those files
are gitignored.

Two private upload zips were assembled in `upload-packages/` (gitignored):

- `KeKarLite_Windows_WithKey_v1.6.2.zip` — built by GitHub Actions from commit
  `4a9df71` (workflow run `45510896995`), packaged locally with the configured
  data folder. The run's NSIS step failed on a Chocolatey 503, but the Windows
  portable artifact was produced and verified.
- `KeKarLite_Linux_WithKey_v1.6.2.zip` — rebuilt locally from the same commit,
  bundle-verified function-for-function against the checkout.

Both zips were integrity-tested, scanned for the plaintext key (none), and
their `settings.enc`/`app.key` pairs were loaded successfully from an
extracted copy. `UPLOAD-README.txt` in that folder has hashes and install
steps. No release tag or remote artifact was modified. The Windows zip was later rebuilt without an empty leftover `KeKarData.empty` folder; its final SHA-256 is `b8890cd021a0398b874c9d174f0cb149364b5a5818ee21d30a52e9ead5e63dbc`, which is the value in `UPLOAD-README.txt`.
