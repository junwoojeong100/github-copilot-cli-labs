"""워크플로우 예제가 모든 참여자 출력을 표시하는지 검증합니다."""

import asyncio
import importlib
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_framework import Agent, ChatResponse, ChatResponseUpdate, ResponseStream
from agent_framework.orchestrations import ConcurrentBuilder

from _streaming import stream_workflow


class FixedChatClient:
    """외부 호출 없이 고정 응답을 반환하는 테스트용 채팅 클라이언트입니다."""

    additional_properties: dict = {}

    def get_response(self, messages, *, stream=False, **kwargs):
        """Agent Framework 채팅 클라이언트 프로토콜에 맞는 응답을 반환합니다."""

        def make_update() -> ChatResponseUpdate:
            return ChatResponseUpdate(
                role="assistant",
                contents=[{"type": "text", "text": "테스트 응답"}],
            )

        if stream:

            async def updates():
                yield make_update()

            return ResponseStream(updates(), finalizer=ChatResponse.from_updates)

        async def response():
            return ChatResponse.from_updates([make_update()])

        return response()


class DelayedChatClient:
    """청크 도착 순서를 교차시키는 테스트용 채팅 클라이언트입니다."""

    additional_properties: dict = {}

    def __init__(self, label: str, delays: list[float]) -> None:
        self.label = label
        self.delays = delays

    def get_response(self, messages, *, stream=False, **kwargs):
        """서로 다른 지연을 둔 세 개의 응답 청크를 반환합니다."""

        def make_update(index: int) -> ChatResponseUpdate:
            return ChatResponseUpdate(
                role="assistant",
                contents=[{"type": "text", "text": f"{self.label}{index} "}],
            )

        if stream:

            async def updates():
                for index, delay in enumerate(self.delays, start=1):
                    await asyncio.sleep(delay)
                    yield make_update(index)

            return ResponseStream(updates(), finalizer=ChatResponse.from_updates)

        async def response():
            return ChatResponse.from_updates([make_update(1)])

        return response()


class WorkflowOutputTests(unittest.IsolatedAsyncioTestCase):
    """순차·GroupChat·동시 예제의 콘솔 출력을 검사합니다."""

    async def _run_example(self, module_name: str) -> str:
        """Azure SDK 객체를 테스트 대역으로 교체하고 예제 main을 실행합니다."""
        module = importlib.import_module(module_name)
        output = io.StringIO()
        env = {
            "PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/lab",
            "MODEL_DEPLOYMENT_NAME": "test-model",
        }

        with (
            patch.dict(os.environ, env),
            patch.object(module, "AzureCliCredential", return_value=object()),
            patch.object(module, "FoundryChatClient", return_value=FixedChatClient()),
            redirect_stdout(output),
        ):
            await module.main()

        return output.getvalue()

    async def test_sequential_example_prints_every_stage(self) -> None:
        """순차 워크플로우가 분석가·작가·편집자를 모두 표시해야 합니다."""
        output = await self._run_example("02_sequential_workflow")

        for name in ("분석가", "작가", "편집자"):
            self.assertEqual(output.count(f"[{name}]"), 1)

    async def test_group_chat_example_prints_every_participant(self) -> None:
        """GroupChat이 기획자·개발자·디자이너 발언을 모두 표시해야 합니다."""
        output = await self._run_example("03_group_chat")

        for name in ("기획자", "개발자", "디자이너"):
            self.assertGreaterEqual(output.count(f"[{name}]"), 1)
        self.assertNotIn("[group_chat_orchestrator]", output)

    async def test_concurrent_example_prints_every_reviewer_once(self) -> None:
        """동시 워크플로우가 집계 중복 없이 세 리뷰어를 표시해야 합니다."""
        output = await self._run_example("04_concurrent_workflow")

        for name in ("보안 리뷰어", "성능 리뷰어", "UX 리뷰어"):
            self.assertEqual(output.count(f"[{name}]"), 1)
        self.assertNotIn("[aggregator]", output)

    async def test_stream_workflow_handles_default_concurrent_aggregation(self) -> None:
        """중간 출력을 지정하지 않아도 기본 집계 응답을 표시해야 합니다."""
        agents = [
            Agent(client=FixedChatClient(), name=name, instructions="한국어로 답변합니다.")
            for name in ("보안", "성능", "UX")
        ]
        workflow = ConcurrentBuilder(participants=agents).build()
        output = io.StringIO()

        with redirect_stdout(output):
            await stream_workflow(workflow, "설계안을 검토해 주세요.")

        rendered = output.getvalue()
        for name in ("보안", "성능", "UX"):
            self.assertEqual(rendered.count(f"[{name}]"), 1)

    async def test_concurrent_multichunk_responses_do_not_interleave(self) -> None:
        """병렬 다중 청크 응답을 발화자별 완성 응답으로 묶어야 합니다."""
        agents = [
            Agent(
                client=DelayedChatClient(name, delays),
                name=name,
                instructions="한국어로 답변합니다.",
            )
            for name, delays in (
                ("보안", [0.01, 0.06, 0.01]),
                ("성능", [0.03, 0.01, 0.05]),
                ("UX", [0.02, 0.03, 0.02]),
            )
        ]
        workflow = ConcurrentBuilder(
            participants=agents,
            intermediate_output_from=agents,
        ).build()
        output = io.StringIO()

        with redirect_stdout(output):
            await stream_workflow(workflow, "설계안을 검토해 주세요.")

        rendered = output.getvalue()
        for name in ("보안", "성능", "UX"):
            self.assertEqual(rendered.count(f"[{name}]"), 1)
            self.assertIn(f"[{name}]\n{name}1 {name}2 {name}3", rendered)


if __name__ == "__main__":
    unittest.main()
