"""Lease generation from a client-supplied example lease."""
import pytest

from src.data.models import Lease, Property
from src.services import lease_builder


def _property(**overrides):
    base = dict(address="123 Main Street", city="Springfield", zip_code="62701",
                rent_price=1200.0, deposit_amount=1200.0, bedrooms=2,
                bathrooms=1.0, sqft=900, pet_policy="Cats OK",
                available_date="2026-12-01", status="Vacant")
    base.update(overrides)
    return Property(**base)


def _seed_property(kekar_app):
    """Give the portfolio exactly one property and refresh the views."""
    prop_id = kekar_app.property_repo.create(_property())
    kekar_app.main_window.reload_all()
    return prop_id


def test_template_fills_property_values():
    fields = lease_builder.tokens_for(_property(), tenant="John Doe",
                                      landlord="Jane Smith", term_months=12)
    body = lease_builder.render(
        "{{address}}, {{city}} {{zip}} — ${{rent}} / ${{deposit}}",
        fields)
    assert body == "123 Main Street, Springfield 62701 — $1,200.00 / $1,200.00"


def test_template_fills_tenant_and_landlord():
    fields = lease_builder.tokens_for(_property(), tenant="John Doe",
                                      landlord="Jane Smith")
    body = lease_builder.render("{{landlord}} lets to {{tenant}}", fields)
    assert body == "Jane Smith lets to John Doe"


def test_template_leaves_unknown_markers_alone():
    """A client's own markers must not be mangled."""
    fields = lease_builder.tokens_for(_property())
    body = lease_builder.render("{{address}} {{their_marker}}", fields)
    assert body == "123 Main Street {{their_marker}}"


def test_unknown_tokens_are_reported():
    template = "{{address}} {{foo}} {{bar}} {{foo}}"
    assert lease_builder.unknown_tokens(template) == ["foo", "bar"]


def test_known_markers_are_not_reported_as_unknown():
    template = "{{address}} {{rent}} {{tenant}}"
    assert lease_builder.unknown_tokens(template) == []


def test_money_formats_with_two_decimals():
    assert lease_builder.money(1200.0) == "1,200.00"
    assert lease_builder.money(950.5) == "950.50"
    assert lease_builder.money(None) == ""


def test_sqft_clause_only_when_known():
    with_sqft = lease_builder.render("{{sqft_clause}}",
                                     lease_builder.tokens_for(_property()))
    assert "900 square feet" in with_sqft
    without = lease_builder.render("{{sqft_clause}}",
                                  lease_builder.tokens_for(_property(sqft=None)))
    assert without == ""


def test_missing_property_still_renders():
    """Generating without a property must not raise."""
    fields = lease_builder.tokens_for(None, tenant="John")
    assert lease_builder.render("{{address}} / {{tenant}}", fields) == " / John"


def test_default_template_uses_only_known_markers():
    assert lease_builder.unknown_tokens(lease_builder.DEFAULT_TEMPLATE) == []


def test_default_template_renders_complete_lease():
    body = lease_builder.render(
        lease_builder.DEFAULT_TEMPLATE,
        lease_builder.tokens_for(_property(), tenant="John Doe",
                                 landlord="Jane Smith", term_months=12))
    assert "123 Main Street" in body
    assert "Springfield" in body
    assert "John Doe" in body
    assert "Jane Smith" in body
    assert "$1,200.00" in body
    assert "{{" not in body


def test_repo_round_trip(kekar_app):
    repo = kekar_app.lease_repo
    prop_id = kekar_app.property_repo.create(_property())
    lease_id = repo.create(Lease(property_id=prop_id, tenant_name="John Doe",
                                 body="LEASE BODY"))
    saved = repo.get(lease_id)
    assert saved.tenant_name == "John Doe"
    assert saved.body == "LEASE BODY"
    assert saved.property_id == prop_id

    saved.tenant_name = "Updated Name"
    repo.update(saved)
    assert repo.get(lease_id).tenant_name == "Updated Name"


def test_repo_lists_newest_first_and_filters_by_property(kekar_app):
    repo = kekar_app.lease_repo
    first = repo.create(Lease(tenant_name="First", body="a"))
    second = repo.create(Lease(tenant_name="Second", body="b"))
    assert [lease.id for lease in repo.list()] == [second, first]
    assert repo.list(property_id=12345) == []


def test_repo_delete(kekar_app):
    repo = kekar_app.lease_repo
    lease_id = repo.create(Lease(tenant_name="Gone", body="x"))
    repo.delete(lease_id)
    assert repo.get(lease_id) is None


def test_leases_table_exists(kekar_app):
    tables = {r[0] for r in kekar_app.db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert "leases" in tables


def test_tab_is_on_the_main_window(kekar_app):
    window = kekar_app.main_window
    assert window.lease_tab is not None
    assert window.tabs.indexOf(window.lease_tab) >= 0


def test_generate_requires_a_property(kekar_app, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    prompted = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: prompted.append(a))
    window = kekar_app.main_window
    window.lease_tab.tenant_edit.setText("John Doe")
    window.lease_tab.generate()
    assert prompted, "generating with no property should explain itself"
    assert window.lease_tab.preview.toPlainText() == ""


def test_generate_fills_the_preview(kekar_app):
    _seed_property(kekar_app)
    window = kekar_app.main_window
    window.lease_tab.tenant_edit.setText("John Doe")
    window.lease_tab.generate()
    body = window.lease_tab.preview.toPlainText()
    assert "123 Main Street" in body
    assert "John Doe" in body
    assert "{{" not in body


def test_save_and_reload_a_lease(kekar_app):
    _seed_property(kekar_app)
    window = kekar_app.main_window
    window.lease_tab.tenant_edit.setText("John Doe")
    window.lease_tab.generate()
    window.lease_tab.save_lease()

    saved = kekar_app.lease_repo.list()
    assert len(saved) == 1
    assert saved[0].tenant_name == "John Doe"
    assert "123 Main Street" in saved[0].body
    assert window.lease_tab.saved_combo.count() >= 2


def test_saved_lease_loads_back(kekar_app):
    _seed_property(kekar_app)
    window = kekar_app.main_window
    window.lease_tab.tenant_edit.setText("John Doe")
    window.lease_tab.generate()
    window.lease_tab.save_lease()

    window.lease_tab.preview.clear()
    window.lease_tab.saved_combo.setCurrentIndex(1)
    assert "123 Main Street" in window.lease_tab.preview.toPlainText()
    assert window.lease_tab.tenant_edit.text() == "John Doe"


def test_template_survives_a_restart(kekar_app):
    kekar_app.settings.lease_template = "CUSTOM {{address}}"
    kekar_app.settings.save()
    assert kekar_app.settings.lease_template == "CUSTOM {{address}}"


def test_tour_includes_the_lease_tab(kekar_app):
    from src.ui.tour import build_tour_steps
    steps = build_tour_steps(kekar_app.main_window)
    assert kekar_app.main_window.lease_tab in [s.target for s in steps]


def test_print_lease_uses_the_system_dialog(kekar_app, monkeypatch):
    from PyQt6.QtPrintSupport import QPrintDialog
    from src.ui import lease_tab as module

    _seed_property(kekar_app)
    window = kekar_app.main_window
    window.lease_tab.tenant_edit.setText("John Doe")
    window.lease_tab.generate()

    printed = []

    class FakeDocument:
        def setPlainText(self, text):
            self.text = text

        def print(self, printer):
            printed.append((self.text, printer))

    monkeypatch.setattr(module.QPrintDialog, "exec",
                        lambda self: QPrintDialog.DialogCode.Accepted)
    monkeypatch.setattr(module, "QTextDocument", FakeDocument)

    window.lease_tab.print_lease()

    assert len(printed) == 1
    assert "123 Main Street" in printed[0][0]


def test_print_cancelled_prints_nothing(kekar_app, monkeypatch):
    from PyQt6.QtPrintSupport import QPrintDialog
    from src.ui import lease_tab as module

    _seed_property(kekar_app)
    window = kekar_app.main_window
    window.lease_tab.tenant_edit.setText("John Doe")
    window.lease_tab.generate()

    printed = []
    monkeypatch.setattr(module.QPrintDialog, "exec",
                        lambda self: QPrintDialog.DialogCode.Rejected)
    monkeypatch.setattr(module.QTextDocument, "print",
                        lambda self, printer: printed.append(printer))
    window.lease_tab.print_lease()
    assert printed == []


def test_email_opens_a_mailto_link(kekar_app, monkeypatch):
    from urllib.parse import parse_qs, urlparse

    from src.ui import lease_tab as module

    _seed_property(kekar_app)
    window = kekar_app.main_window
    window.lease_tab.tenant_edit.setText("John Doe")
    window.lease_tab.email_edit.setText("john@example.com")
    window.lease_tab.generate()

    opened = []
    monkeypatch.setattr(module.QDesktopServices, "openUrl", lambda url: opened.append(url) or True)

    window.lease_tab.email_lease()

    assert len(opened) == 1
    url = opened[0].toString()
    assert url.startswith("mailto:john@example.com?")
    query = parse_qs(urlparse(url).query)
    assert query["subject"] == ["Lease agreement — 123 Main Street"]
    assert "123 Main Street" in query["body"][0]


def test_email_without_a_mail_client_warns(kekar_app, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    from src.ui import lease_tab as module

    _seed_property(kekar_app)
    window = kekar_app.main_window
    window.lease_tab.tenant_edit.setText("John Doe")
    window.lease_tab.generate()

    monkeypatch.setattr(module.QDesktopServices, "openUrl", lambda url: False)
    warned = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **k: warned.append(a))
    window.lease_tab.email_lease()
    assert warned, "a missing mail client should be reported"
