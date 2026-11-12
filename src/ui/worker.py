"""Safe ownership of worker QThreads.

Qt aborts the whole process when a QThread is destroyed while its thread is
still running:

    QThread: Destroyed while thread is still running
    Aborted (core dumped)

The app hit this on startup at roughly a 13% rate: a finished thread's last
Python reference was dropped inside a slot, and PyQt deleted the C++ object
while the thread was still unwinding. It is a race, so it survives casual
testing and kills real launches.

Two rules keep it from happening:

* Threads are registered here, so a dialog or pane destroyed mid-operation
  cannot drop the last reference and delete a running thread.
* ``reap()`` is called from the GUI thread once the work is done. It waits for
  the thread to fully finish *before* the registry releases it — releasing
  first is the bug.

``reap()`` must only be called from the GUI thread, and only for a thread
whose work has already completed, so the wait returns immediately.
"""
from __future__ import annotations

from PyQt6.QtCore import QThread

# Every worker thread that has not been reaped. Module-level on purpose:
# ownership lives here, not on a dialog that might get closed.
_LIVE: set[QThread] = set()


def register(thread: QThread) -> QThread:
    """Take ownership of a worker thread. Call ``start()`` afterwards."""
    _LIVE.add(thread)
    return thread


def reap(thread: QThread | None) -> None:
    """Wait for a finished thread, then release it. GUI thread only."""
    if thread is None:
        return
    try:
        thread.wait()
    except RuntimeError:
        # Already destroyed elsewhere; nothing to wait for.
        pass
    _LIVE.discard(thread)


def shutdown(timeout_ms: int = 10_000) -> None:
    """Wait (bounded) for every live worker, for use on application exit."""
    for thread in list(_LIVE):
        try:
            thread.wait(timeout_ms)
        except RuntimeError:
            pass
    _LIVE.clear()


def live_count() -> int:
    """Number of workers not yet reaped — used by the test suite."""
    return len(_LIVE)
