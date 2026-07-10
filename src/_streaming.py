"""스트리밍 출력 공용 헬퍼.

단일 에이전트는 토큰(청크) 단위로 출력하고, 워크플로우는 병렬 청크가 섞이지
않도록 각 발화자의 완성 응답 단위로 출력합니다. 모든 예제(01~06)가 공유합니다.
"""

from typing import Any

from agent_framework import AgentExecutorResponse, AgentResponse, AgentResponseUpdate


async def stream_agent(
    agent: Any,
    prompt: str,
    *,
    label: str | None = "에이전트 응답",
    **run_kwargs: Any,
) -> str:
    """에이전트 응답을 토큰 단위로 출력하고, 누적된 전체 텍스트를 반환합니다.

    Args:
        agent: 실행할 에이전트.
        prompt: 에이전트에 전달할 입력 메시지.
        label: 출력 앞에 붙일 머리말. None이면 머리말을 생략합니다.
        **run_kwargs: ``agent.run``에 그대로 전달할 추가 인자(예: tools).

    Returns:
        스트리밍으로 받은 전체 응답 텍스트(다음 단계 입력 등으로 재사용).
    """
    if label:
        print(f"{label}:")
    chunks = []
    async for update in agent.run(prompt, stream=True, **run_kwargs):
        text = getattr(update, "text", "") or ""
        if text:
            chunks.append(text)
            print(text, end="", flush=True)
    print()
    return "".join(chunks)


def _is_internal_executor(speaker: str | None) -> bool:
    """발화자 id가 내부 중계·집계 executor인지 판별합니다."""
    if not speaker:
        return False
    normalized = speaker.lower()
    return "orchestrator" in normalized or "aggregator" in normalized


def _response_blocks(
    response: Any,
    fallback_speaker: str | None,
) -> list[tuple[str | None, str]]:
    """완성 응답을 발화자와 텍스트 블록 목록으로 변환합니다."""
    blocks: list[tuple[str | None, str]] = []
    messages = getattr(response, "messages", None) or []
    for message in messages:
        text = (getattr(message, "text", "") or "").strip()
        if not text:
            continue
        speaker = getattr(message, "author_name", None) or fallback_speaker
        blocks.append((speaker, text))

    if not blocks:
        text = str(response).strip()
        if text:
            blocks.append((fallback_speaker, text))
    return blocks


async def stream_workflow(
    workflow: Any,
    message: str,
    *,
    name_map: dict[str, str] | None = None,
) -> Any:
    """워크플로우를 스트리밍 실행하며 발화자별 완성 응답을 출력합니다.

    현재 SDK는 선택된 ``output``/``intermediate`` 소스의 토큰 갱신
    (``AgentResponseUpdate``)을 내보냅니다. Concurrent 기본 집계기처럼 완성된
    ``AgentResponse``가 한 번에 오는 경우와 이전 SDK의 ``AgentExecutorResponse``도
    함께 처리합니다. 토큰 갱신은 발화자별로 모아 병렬 응답이 서로 섞이지 않게 하고,
    내부 오케스트레이터 메시지와 중복 집계 결과는 출력하지 않습니다.

    Args:
        workflow: 실행할 워크플로우.
        message: 워크플로우에 전달할 입력 메시지.
        name_map: executor_id → 표시 이름 매핑(선택). 없으면 executor_id를 그대로 사용.

    Returns:
        최종 ``WorkflowRunResult``.
    """
    name_map = name_map or {}
    pending_chunks: dict[str | None, list[str]] = {}
    pending_order: list[str | None] = []
    printed_blocks: set[tuple[str | None, str]] = set()

    stream = workflow.run(message, stream=True)
    async for event in stream:
        data = getattr(event, "data", None)
        event_type = getattr(event, "type", None)
        event_executor = getattr(event, "executor_id", None)

        # 1) 병렬 실행에서도 섞이지 않도록 발화자별 토큰을 모읍니다.
        if isinstance(data, AgentResponseUpdate):
            speaker = getattr(data, "author_name", None) or event_executor
            text = getattr(data, "text", "") or ""
            if not text or _is_internal_executor(speaker):
                continue
            if speaker not in pending_chunks:
                pending_chunks[speaker] = []
                pending_order.append(speaker)
            pending_chunks[speaker].append(text)
            continue

        # 2) 완성된 응답 또는 Concurrent 집계 결과
        if event_type not in {"intermediate", "output", "executor_completed"}:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            is_executor_response = isinstance(item, AgentExecutorResponse)
            if isinstance(item, AgentExecutorResponse):
                fallback_speaker = getattr(item, "executor_id", event_executor)
                response = item.agent_response
            elif isinstance(item, AgentResponse):
                fallback_speaker = event_executor
                response = item
            else:
                continue

            for speaker, text in _response_blocks(response, fallback_speaker):
                if _is_internal_executor(speaker):
                    continue
                buffered = "".join(pending_chunks.get(speaker, []))
                if is_executor_response and event_type == "executor_completed" and not buffered:
                    continue
                key = (speaker, text)
                if not is_executor_response and key in printed_blocks:
                    pending_chunks.pop(speaker, None)
                    continue
                printed_blocks.add(key)
                pending_chunks.pop(speaker, None)
                display_name = name_map.get(speaker, speaker) or "에이전트"
                print(f"\n\n[{display_name}]\n{text}")

    # 완성 이벤트 없이 토큰 갱신만 온 사용자 정의 워크플로우도 누락하지 않습니다.
    for speaker in pending_order:
        text = "".join(pending_chunks.get(speaker, [])).strip()
        if not text or _is_internal_executor(speaker):
            continue
        key = (speaker, text)
        if key in printed_blocks:
            continue
        display_name = name_map.get(speaker, speaker) or "에이전트"
        print(f"\n\n[{display_name}]\n{text}")

    print()
    return await stream.get_final_response()
