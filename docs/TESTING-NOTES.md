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
| 5 | Dark/OLED text contrast | Independent, highly visible | DONE — placeholder + muted labels follow dark/OLED palettes |
| 6 | Collapse button is unmarked | Independent, tiny UI fix | DONE — Lite sidebar toggle keeps its label and tooltip |
| 7 | Merge Stays into Calendar + legend | Structural change; must precede calendar tweaks | DONE — Stays is a panel in Calendar; short stays are purple; Help has a legend |
| 8 | Selected property highlights calendar | Applies to merged calendar | DONE — selected property's dates are bold and named in the summary |
| 9 | Same-line move-in/move-out rows | Applies to merged calendar | DONE — one address row carries both move dates |
| 10 | Date click shows owning property | Applies to merged calendar | DONE — selecting a date names its property and event type |
| 11 | Applicant profile on single click | Depends on #2 | DONE — single click opens an editable full profile panel |
| — | Final regression + docs + release | After all eleven | DONE — suites green, docs updated, handoff written |

The numbers in the work-order table are execution positions, not the original
note numbers. The original note number is in the "Note" column.

## Second batch — notes as received

1) step six should not mention the client the tutorial is built for them not me,it should say something like upload your own example lease or use the one provided, we should look up a comprehensive lease that we can use as a base template.
2)calendar highlighting should bring the address to th top of the list.
3)Properties>Movein-Moveout should be a drop down mini calendar instead of a text box
4)Move in and out shoud be in rental terms aswell as pet deposit
4) remove parking spot from ammenties, its reduntant
5)Drive way, street parking, and 1 car or 2car garage should be check boxes
5)remove the before you post line in the test box for preview listing since its on he window itself already
6) in preview list "channel" shoul be changed to "site"
7) pet policy should be a yes or no drop down
8) we need to add sites like Facebook Marketplace, Apartments.com, VRBO, AirBNB, and look up the best way tostructure those post to make sure they are correct and unique
9) lets make sure out lease section is comprehensive

## Second batch — dependency order and plan

Target variant: Lite/production must stay green; full must not regress.

| Pos | Note | Plan | Status |
|---|---|---|---|
| 1 | Pet policy yes/no dropdown | Replace free text with a Yes/No combo; keep the stored text compatible with leases and search. | DONE — Yes/No combo; old free text maps to Yes/No |
| 2 | Move-in/out as mini calendar | Use QDateEdit with calendar popup; keep ISO strings in storage. | DONE — QDateEdit with popup; ISO strings preserved |
| 3 | Move dates in Rental terms | Move the two date widgets from Details into Rental terms without changing storage. | DONE — move dates now sit with rent/deposit/available date |
| 4 | Pet deposit in Rental terms | Add a persisted deposit amount field beside the pet policy; feed the lease clause. | DONE — persisted amount in Rental terms feeds lease tokens |
| 5 | Remove Parking spot amenity | Hide the redundant generic checkbox; keep legacy data readable. | DONE — generic checkbox and listing label removed |
| 6 | Parking/garage checkboxes | Replace the two combos with Driveway, Street parking, 1-car and 2-car checkboxes; derive stored fields. | Pending |
| 7 | Calendar address to top | When a property is selected, move its calendar row to the top of the event list. | Pending |
| 8 | Preview text cleanup | Remove the "Before you post" line from the preview body. | Pending |
| 9 | Channel -> Site | Rename the preview label and related user-facing text. | Pending |
| 10 | Lease template + tutorial wording | Research a comprehensive base lease, update the built-in template and step 6 wording. | Pending |
| 11 | Add listing sites | Research and add Facebook Marketplace, Apartments.com, VRBO and Airbnb packages with distinct structures. | Pending |
| 12 | Regression + docs | Full suite, Lite suite, docs and handoff. | Pending |
