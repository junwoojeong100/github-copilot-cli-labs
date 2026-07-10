"""인덱싱 완료 대기 경계 조건을 검증합니다."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from _indexing import wait_for_document_count, wait_for_document_count_async


class SequenceCounter:
    """호출 순서에 따라 문서 수를 반환합니다."""

    def __init__(self, counts: list[int]) -> None:
        self.counts = counts
        self.calls = 0

    def get_document_count(self) -> int:
        """마지막 값은 이후 호출에도 유지합니다."""
        index = min(self.calls, len(self.counts) - 1)
        self.calls += 1
        return self.counts[index]


class IndexingWaitTests(unittest.IsolatedAsyncioTestCase):
    """마지막 대기 이후의 성공 여부를 재확인해야 합니다."""

    async def test_async_wait_rechecks_after_sleep(self) -> None:
        """비동기 대기는 sleep 이후 문서 수를 다시 확인해야 합니다."""
        counter = SequenceCounter([0, 4])

        await wait_for_document_count_async(
            counter,
            4,
            timeout_seconds=0.1,
            poll_interval_seconds=0.001,
        )

        self.assertEqual(counter.calls, 2)

    async def test_async_wait_times_out(self) -> None:
        """제한시간 안에 목표에 못 미치면 명시적으로 실패해야 합니다."""
        counter = SequenceCounter([0])

        with self.assertRaises(TimeoutError):
            await wait_for_document_count_async(counter, 4, timeout_seconds=0)

    def test_sync_wait_rechecks_after_sleep(self) -> None:
        """동기 대기는 sleep 이후 문서 수를 다시 확인해야 합니다."""
        counter = SequenceCounter([0, 4])

        wait_for_document_count(
            counter,
            4,
            timeout_seconds=0.1,
            poll_interval_seconds=0.001,
        )

        self.assertEqual(counter.calls, 2)

    def test_sync_wait_times_out(self) -> None:
        """제한시간 안에 목표에 못 미치면 명시적으로 실패해야 합니다."""
        counter = SequenceCounter([0])

        with self.assertRaises(TimeoutError):
            wait_for_document_count(counter, 4, timeout_seconds=0)
