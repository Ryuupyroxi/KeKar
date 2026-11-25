"""Regressions for the second batch of client notes (Lite/production)."""
from PyQt6.QtWidgets import QComboBox

from src.data.models import Property


def test_pet_policy_is_a_yes_no_dropdown(kekar_app):
    """Note 1: the form asks Yes/No, not free text."""
    form = kekar_app.main_window.property_form
    form.load_property(None)
    combo = form.pet_input
    assert isinstance(combo, QComboBox)
    assert [combo.itemText(i) for i in range(combo.count())] == ["No", "Yes"]
    combo.setCurrentText("Yes")
    form.address_input.setText("Pet Combo Way")
    form.save()
    assert kekar_app.property_repo.get(form.current_id).pet_policy == "Yes"


def test_existing_pet_text_maps_to_the_new_dropdown(kekar_app):
    form = kekar_app.main_window.property_form
    pid = kekar_app.property_repo.create(
        Property(address="Old Pets Way", pet_policy="Cats OK"))
    form.load_property(pid)
    assert form.pet_input.currentText() == "Yes"
    pid2 = kekar_app.property_repo.create(
        Property(address="Old No Pets Way", pet_policy="No pets"))
    form.load_property(pid2)
    assert form.pet_input.currentText() == "No"
