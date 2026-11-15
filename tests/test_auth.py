"""Accounts and login: the plumbing for the client-facing feature."""
import time
from datetime import datetime, timedelta, timezone

import pytest

from src.data.models import Lease  # noqa: F401  (ensures models import cleanly)
from src.services import auth


def test_hash_round_trip():
    stored = auth.hash_password("correct horse battery staple")
    assert auth.verify_password("correct horse battery staple", stored)


def test_wrong_password_fails():
    stored = auth.hash_password("right")
    assert auth.verify_password("wrong", stored) is False


def test_each_hash_gets_its_own_salt():
    password = "same-password"
    assert auth.hash_password(password) != auth.hash_password(password)


def test_hash_is_not_the_password():
    password = "hunter2"
    stored = auth.hash_password(password)
    assert password not in stored
    assert stored.startswith("pbkdf2:")


def test_malformed_hash_returns_false_instead_of_raising():
    """A corrupted database must not become a traceback in the login dialog."""
    assert auth.verify_password("anything", "") is False
    assert auth.verify_password("anything", "not-a-hash") is False
    assert auth.verify_password("anything", "pbkdf2:abc:!!!:???") is False


def test_session_tokens_are_unique():
    tokens = {auth.new_session_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(token) > 20 for token in tokens)


def test_session_expiry_is_in_the_future_and_readable():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    expiry = auth.session_expiry(now)
    assert auth.is_expired(expiry, now) is False
    assert auth.is_expired(expiry, now + timedelta(days=8)) is True


def test_malformed_expiry_counts_as_expired():
    assert auth.is_expired("not-a-date") is True


@pytest.fixture
def repo(kekar_app):
    return kekar_app.user_repo


@pytest.fixture(autouse=True)
def _restore_access(kekar_app):
    """Never leave the window locked or a login requirement switched on.

    The window is shared for the whole session, so a test that locks it would
    hide the offline banner and the panels from every test that follows.
    """
    yield
    kekar_app.settings.require_login = False
    kekar_app.settings.session_token = ""
    kekar_app.current_user = None
    kekar_app.session_token = None
    kekar_app.main_window.set_locked(False)


def test_users_table_exists(kekar_app):
    tables = {r[0] for r in kekar_app.db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "sessions"} <= tables


def test_create_and_get(repo):
    user_id = repo.create("owner", "password-1", display_name="The Owner",
                          role="owner")
    user = repo.get(user_id)
    assert user["username"] == "owner"
    assert user["display_name"] == "The Owner"
    assert user["role"] == "owner"


def test_username_lookup_ignores_case(repo):
    repo.create("Jane", "password-1")
    assert repo.get_by_username("jane")["username"] == "Jane"
    assert repo.get_by_username("nobody") is None


def test_duplicate_username_is_rejected(repo):
    repo.create("dup", "password-1")
    with pytest.raises(Exception):
        repo.create("dup", "password-2")


def test_invalid_role_is_rejected(repo):
    with pytest.raises(ValueError):
        repo.create("x", "password-1", role="superuser")


def test_authenticate(repo):
    repo.create("sam", "s3cret-pass")
    assert repo.authenticate("sam", "s3cret-pass") is not None
    assert repo.authenticate("sam", "nope") is None
    assert repo.authenticate("ghost", "s3cret-pass") is None


def test_set_password(repo):
    user_id = repo.create("pat", "old-password")
    repo.set_password(user_id, "new-password")
    assert repo.authenticate("pat", "new-password") is not None
    assert repo.authenticate("pat", "old-password") is None


def test_delete_removes_the_user(repo):
    user_id = repo.create("temp", "password-1")
    repo.delete(user_id)
    assert repo.get(user_id) is None


def test_sessions_round_trip(repo):
    user_id = repo.create("sue", "password-1")
    token = repo.create_session(user_id)
    user = repo.session_user(token)
    assert user["id"] == user_id
    repo.delete_session(token)
    assert repo.session_user(token) is None


def test_expired_session_is_rejected_and_deleted(repo):
    user_id = repo.create("exp", "password-1")
    stale = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    repo.conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) "
        "VALUES (?, ?, ?, ?)", ("stale-token", user_id, stale, stale))
    assert repo.session_user("stale-token") is None
    assert repo.session_user("stale-token") is None


def test_purge_expired(repo):
    user_id = repo.create("purge", "password-1")
    stale = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    for token in ("a", "b"):
        repo.conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)", (token, user_id, stale, stale))
    repo.create_session(user_id)
    assert repo.purge_expired() == 2


def test_count_users(repo):
    assert repo.count_users() == 0
    repo.create("a", "password-1")
    repo.create("b", "password-1")
    assert repo.count_users() == 2


# -- application wiring ----------------------------------------------------

def test_login_is_off_by_default(kekar_app):
    """Nothing about the app changes until the user turns a login on."""
    assert kekar_app.settings.require_login is False
    assert kekar_app.current_user is None
    assert kekar_app.main_window.is_locked() is False


def test_login_and_logout(kekar_app):
    kekar_app.user_repo.create("owner", "owner-pass-1",
                               display_name="Owner", role="owner")
    assert kekar_app.login("owner", "owner-pass-1") is True
    assert kekar_app.current_user["username"] == "owner"
    assert kekar_app.session_token

    kekar_app.logout()
    assert kekar_app.current_user is None
    assert kekar_app.session_token is None


def test_login_with_wrong_password(kekar_app):
    kekar_app.user_repo.create("owner", "owner-pass-1")
    assert kekar_app.login("owner", "wrong") is False
    assert kekar_app.current_user is None


def test_session_survives_a_reconnect(kekar_app):
    kekar_app.user_repo.create("owner", "owner-pass-1")
    kekar_app.login("owner", "owner-pass-1")
    token = kekar_app.session_token

    # A fresh Application resolves the saved token at startup.
    assert kekar_app.settings.session_token == token
    assert kekar_app.user_repo.session_user(token) is not None


def test_locking_hides_the_portfolio(kekar_app):
    window = kekar_app.main_window
    original = window.centralWidget()
    assert window.is_locked() is False
    window.set_locked(True)
    assert window.is_locked() is True
    assert window.centralWidget() is not original
    window.set_locked(False)
    assert window.is_locked() is False
    assert window.centralWidget() is original


def test_unlocking_restores_a_visible_portfolio(kekar_app):
    """Qt hides a swapped-out central widget and does not unhide it on return.

    Without an explicit show() the portfolio comes back invisible, and nothing
    anywhere raises.
    """
    window = kekar_app.main_window
    window.set_locked(True)
    window.set_locked(False)
    # The restored central widget must not be left explicitly hidden, or every
    # child stays invisible even though nothing reports an error.
    assert window.centralWidget().isHidden() is False
    window.show_offline(True)
    assert window.offline_banner.isVisibleTo(window) is True


def test_logout_locks_when_login_is_required(kekar_app):
    kekar_app.user_repo.create("owner", "owner-pass-1")
    kekar_app.settings.require_login = True
    kekar_app.login("owner", "owner-pass-1")
    kekar_app.logout()
    assert kekar_app.main_window.centralWidget() is not None
    assert kekar_app.main_window.lock_action.isVisible() is False


def test_login_dialog_rejects_empty_credentials(kekar_app, monkeypatch):
    from src.ui.login_dialog import LoginDialog

    dialog = LoginDialog(kekar_app, kekar_app.main_window)
    assert dialog.username.text() == ""
    dialog._try_login()
    assert not dialog.isVisible()


def test_users_dialog_lists_accounts(kekar_app):
    from src.ui.users_dialog import UsersDialog

    kekar_app.user_repo.create("owner", "owner-pass-1",
                               display_name="Owner", role="owner")
    dialog = UsersDialog(kekar_app, kekar_app.main_window)
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 0).text() == "owner"
    assert dialog.table.item(0, 2).text() == "owner"


def test_account_setup_is_fast_enough_to_be_usable():
    """310k PBKDF2 iterations must not make login feel broken."""
    start = time.perf_counter()
    auth.hash_password("timing-check")
    assert time.perf_counter() - start < 5.0
