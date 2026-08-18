"""Phase 12 Task 4 (unit): drop_old_candles builds the right DELETE and commits.

No DB — a fake async session captures the statement so the test runs anywhere.
"""

from datetime import UTC, datetime, timedelta

from app.core.retention import drop_old_candles


class _FakeResult:
    rowcount = 3


class _FakeAsyncSession:
    def __init__(self):
        self.executed = None
        self.committed = False

    async def execute(self, stmt):
        self.executed = stmt
        return _FakeResult()

    async def commit(self):
        self.committed = True


async def test_drop_old_candles_deletes_1m_older_than_cutoff_and_commits():
    session = _FakeAsyncSession()
    now = datetime(2026, 7, 10, tzinfo=UTC)

    deleted = await drop_old_candles(session, tf="1m", older_than_days=60, now=now)

    assert deleted == 3
    assert session.committed is True
    compiled = str(
        session.executed.compile(compile_kwargs={"literal_binds": True})
    )
    assert "candles" in compiled.lower()
    assert "'1m'" in compiled
    # cutoff = now - 60d must appear as the ts bound
    cutoff = (now - timedelta(days=60)).strftime("%Y-%m-%d")
    assert cutoff in compiled
