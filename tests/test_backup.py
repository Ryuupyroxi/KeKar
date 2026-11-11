from src.data.backup import (create_backup, list_backups, open_with_recovery,
                             prune_backups, restore_backup, verify_backup)
from src.data.models import Property
from src.data.property_repo import PropertyRepo


def test_backup_and_restore(db):
    repo = PropertyRepo(db.conn)
    pid = repo.create(Property(address="1 Backup Ln"))
    backup = create_backup(db, label="test")
    assert verify_backup(backup)
    repo.delete(pid)
    assert repo.get(pid) is None
    restore_backup(db, backup)
    assert repo.get(pid) is not None


def test_list_backups_newest_first(db):
    create_backup(db, label="first")
    create_backup(db, label="second")
    backups = list_backups()
    assert len(backups) == 2
    assert backups[0].name >= backups[1].name


def test_prune(db, monkeypatch):
    from src.data import backup as backup_mod
    create_backup(db, label="old")
    monkeypatch.setattr(backup_mod, "_days_since", lambda p: 999)
    assert prune_backups(keep_days=30) == 1
    assert list_backups() == []


def test_recovery_restores_on_corruption(db):
    repo = PropertyRepo(db.conn)
    pid = repo.create(Property(address="2 Recover Rd"))
    create_backup(db, label="good")
    db.close()
    with open(db.path, "r+b") as fh:
        fh.seek(0)
        fh.write(b"this is not a sqlite database at all")
    reopened = open_with_recovery(db.path)
    try:
        assert reopened.integrity_check()
        assert PropertyRepo(reopened.conn).get(pid) is not None
    finally:
        reopened.close()
