"""Azure AI Search 인덱싱 완료 대기 공용 헬퍼."""

import asyncio
import time
from typing import Protocol


class SupportsDocumentCount(Protocol):
    """문서 수 조회를 지원하는 검색 클라이언트 프로토콜."""

    def get_document_count(self) -> int:
        """현재 인덱스 문서 수를 반환합니다."""
        ...


async def wait_for_document_count_async(
    search_client: SupportsDocumentCount,
    target: int,
    *,
    timeout_seconds: float = 30,
    poll_interval_seconds: float = 1,
) -> None:
    """비동기로 목표 문서 수까지 기다립니다."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds

    while search_client.get_document_count() < target:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError(f"{timeout_seconds:g}초 안에 문서 {target}건의 인덱싱이 완료되지 않았습니다.")
        await asyncio.sleep(min(poll_interval_seconds, remaining))


def wait_for_document_count(
    search_client: SupportsDocumentCount,
    target: int,
    *,
    timeout_seconds: float = 30,
    poll_interval_seconds: float = 1,
) -> None:
    """동기 방식으로 목표 문서 수까지 기다립니다."""
    deadline = time.monotonic() + timeout_seconds

    while search_client.get_document_count() < target:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"{timeout_seconds:g}초 안에 문서 {target}건의 인덱싱이 완료되지 않았습니다.")
        time.sleep(min(poll_interval_seconds, remaining))
