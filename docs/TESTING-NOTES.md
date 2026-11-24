# KeKar testing notes — client feedback (2026-11-24)

Target: the **Lite / production** build. The full-featured experimental build
must not regress. These notes came from hands-on testing of the local KeKar
Lite build. They are kept verbatim first, then re-ordered by dependency so
fixes do not cause rework. Each item is worked one at a time:
plan → implement → test → next.

## Notes as received

1. Lease > Property does not populate with current properties data in the application.
2. Button to collapse properties side panel is unmarked.
3. Selecting a property should change the highlighted property in the calendar view.
4. Calendar view should show the move in and move out for given address on the same line instead of separate lines.
5. Applicants tab should include a "profile" view on single click for more info and ease of editing.
6. Selecting date on calendar should show the property that the date is highlighting; currently the calendar has no way to know which property the highlighted date is indicating.
7. Applicants > Property should be a dropdown menu that auto populates with the properties in data.
8. Pet policy should be part of the Lease generator, and if it is a yes to pets the lease should include a pet deposit place as well.
9. Garage, 1 or 2 car, should be in amenities, and parking spot should be street parking or driveway.
10. Dark and OLED theme should not include any dark text at all; it gets lost.
11. Stays tab should be combined into the Calendar tab with different colors for short stays to help indicate them differently from long stays on the calendar and in the properties side panel, and a small legend in the Help dropdown.

## Dependency analysis

- Items 1 and 7 are the same class of defect: a property selector that does
  not read the live property repository. Fix them together with one shared
  helper before anything that depends on those selectors.
- Item 9 changes the property data model (garage count, parking type). The
  lease generator in item 8 and the listing packages should see those fields,
  so it must land before 8.
- Item 8 depends on 1 (Lease > Property) and 9 (new property fields).
- Items 10 and 2 are independent, self-contained UI affordances. They can be
  done early because they are cheap and highly visible, but they do not block
  anything.
- Item 11 restructures the Calendar and removes the separate Stays tab. Items
  3, 4 and 6 all change Calendar behaviour, so they must come **after** 11 to
  avoid being implemented twice.
- Item 5 adds an applicant profile/edit view; it depends on 7 so the profile
  can show a property dropdown.

## Agreed work order

| # | Note | Why here | Status |
|---|---|---|---|
| 1 | Lease Property selector | Root data-wiring bug; unblocks lease work | DONE — combo populated at startup and after save/delete |
| 2 | Applicants Property dropdown | Same helper as #1 | DONE — Property cell is a live combo that saves the link |
| 3 | Garage + parking amenities | Data-model change needed by lease/listing | DONE — garage count + street/driveway persist and appear in listings |
| 4 | Pet policy + pet deposit in lease | Depends on #1 and #3 | DONE — pets-allowed leases include a $300 refundable pet-deposit clause |
| 5 | Dark/OLED text contrast | Independent, highly visible | Pending |
| 6 | Collapse button is unmarked | Independent, tiny UI fix | Pending |
| 7 | Merge Stays into Calendar + legend | Structural change; must precede calendar tweaks | Pending |
| 8 | Selected property highlights calendar | Applies to merged calendar | Pending |
| 9 | Same-line move-in/move-out rows | Applies to merged calendar | Pending |
| 10 | Date click shows owning property | Applies to merged calendar | Pending |
| 11 | Applicant profile on single click | Depends on #2 | Pending |
| — | Final regression + docs + release | After all eleven | Pending |

The numbers in the work-order table are execution positions, not the original
note numbers. The original note number is in the "Note" column.
