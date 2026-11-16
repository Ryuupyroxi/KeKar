"""Tests for the live portal-sync check tool."""
from src.data.db import Database
from src.data.models import Property
from src.data.property_repo import PropertyRepo


def _portfolio(tmp_path) -> tuple:
    data = tmp_path / "KeKarData"
    data.mkdir()
    db = Database(data / "database.db")
    prop_id = PropertyRepo(db).create(
        Property(address="7 Airbnb Way", kind="short_stay"))
    db.close()
    return data, prop_id


def test_live_sync_check_reports_without_writing(tmp_path, monkeypatch):
    from tools import live_sync_check

    data, prop_id = _portfolio(tmp_path)
    seen = {}

    def fake_sync(db, prop, portal):
        seen.update(prop=prop.id, portal=portal)
        return {"status": "ok", "added": 2, "updated": 0, "skipped": 1,
                "total": 3}

    monkeypatch.setattr(live_sync_check, "sync_portal", fake_sync)

    report = live_sync_check.run("https://example/cal.ics", "airbnb",
                                 source_dir=data)

    assert report["dry_run"] is True
    assert report["portal"] == "airbnb"
    assert report["added"] == 2
    assert report["property"] == "7 Airbnb Way"
    assert seen == {"prop": prop_id, "portal": "airbnb"}


def test_live_sync_check_stores_the_url_before_syncing(tmp_path, monkeypatch):
    """The tool is handed the URL, so it must persist it before syncing.

    Otherwise sync_portal answers "no calendar URL is set" and the check can
    never exercise a real calendar.
    """
    from tools import live_sync_check

    data, prop_id = _portfolio(tmp_path)
    captured = {}

    def fake_sync(db, prop, portal):
        row = db.conn.execute(
            "SELECT external_ical_url FROM property_portals "
            "WHERE property_id=? AND portal=?", (prop.id, portal)).fetchone()
        captured["url"] = row[0] if row else None
        return {"status": "ok", "added": 1, "updated": 0, "skipped": 0,
                "total": 1}

    monkeypatch.setattr(live_sync_check, "sync_portal", fake_sync)

    live_sync_check.run("https://example/real.ics", "vrbo", source_dir=data)

    assert captured["url"] == "https://example/real.ics"
    assert prop_id is not None


def test_live_sync_check_refuses_an_unknown_portal(tmp_path):
    from tools import live_sync_check

    data, _ = _portfolio(tmp_path)
    try:
        live_sync_check.run("https://example/cal.ics", "zillow",
                            source_dir=data)
    except SystemExit as exc:
        assert "unknown portal" in str(exc)
    else:
        raise AssertionError("an unknown portal must be refused")
