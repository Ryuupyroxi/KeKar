"""Tests for worker-thread ownership.

Deleting a QThread while its thread is still running makes Qt abort the whole
process ("QThread: Destroyed while thread is still running"). The app hit
that on startup at ~13%, so these tests pin the contract that prevents it:
the registry owns the thread, and reap() waits before releasing.
"""
from __future__ import annotations

import gc
import time
import weakref

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QCoreApplication, QThread

from src.ui import worker


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


class _Sleepy(QThread):
    def __init__(self, seconds: float = 0.05):
        super().__init__()
        self.seconds = seconds

    def run(self) -> None:
        time.sleep(self.seconds)


def test_register_then_reap_releases_only_after_finish(qapp):
    thread = worker.register(_Sleepy())
    assert worker.live_count() == 1

    thread.start()
    worker.reap(thread)

    assert thread.isFinished()
    assert worker.live_count() == 0


def test_reap_is_safe_on_none(qapp):
    worker.reap(None)
    assert worker.live_count() == 0


def test_shutdown_waits_for_live_threads(qapp):
    thread = worker.register(_Sleepy())
    thread.start()

    worker.shutdown(timeout_ms=5000)

    assert thread.isFinished()
    assert worker.live_count() == 0


def test_registry_keeps_a_running_thread_alive(qapp):
    """Dropping every local reference must not destroy a running thread."""
    thread = worker.register(_Sleepy(0.15))
    thread.start()
    ref = weakref.ref(thread)
    del thread
    gc.collect()

    assert ref() is not None, "the registry must own the thread"

    worker.shutdown(timeout_ms=5000)


def test_a_reaped_thread_is_reusable_as_a_slot_target(qapp):
    """reap() must leave the object valid, not half-destroyed."""
    thread = worker.register(_Sleepy())
    thread.start()
    worker.reap(thread)

    # Still a usable QThread object: finished, but not destroyed.
    assert thread.isFinished()
    assert not thread.isRunning()
