# Redundant code/options found during second-batch testing

Observation only — no changes made. For Master to decide on later.

1. `amenity_parking` remains in the model, schema, repository and legacy data
   even though the checkbox and listing label were removed. It is retained for
   old portfolios, but it is now an unused input field.
2. `parking_type` and `garage_spaces` are derived from four checkboxes and then
   stored again. The stored values are needed by listings and leases, but they
   are technically a second representation of the checkbox state.
3. `PET_DEPOSIT_AMOUNT` still exists as a 300-dollar fallback even though the
   property now stores `pet_deposit_amount`. Useful for old rows, redundant for
   new ones.
4. `_NO_PETS` still accepts "none", "no pet" and "no pets" while the form only
   writes Yes/No. Legacy compatibility, but extra branches to maintain.
5. The code still says "channel" internally (`compile_channel`,
   `channel_fields`, `ChannelListing`, `CHANNELS`) while the user-facing label
   now says "Site". Not broken; just inconsistent vocabulary.
6. `LITE_HIDDEN_CHANNELS` is now an empty frozenset but `visible_channels()`
   still filters through it. Harmless, but it is effectively a no-op.
7. `ChannelListing.as_text()` still prints a "Before you post:" heading for
   clipboard packages, while the preview dialog label no longer repeats it.
   Decide whether the clipboard text should keep that heading.
8. `README.txt` and `INSTRUCTIONS.txt` now overlap in both packages. Both are
   accurate; one could be dropped or cross-linked later.
9. `install_linux.py` is included in the Windows package by the shared
   packager. It is not harmful, but it is not relevant to a Windows client.
10. Several historical app folders remain under `dist/` (`KeKar.pre-*`,
    `KeKar.old-*`) and in scratch as rollback copies. Not shipped, but local
    clutter.
