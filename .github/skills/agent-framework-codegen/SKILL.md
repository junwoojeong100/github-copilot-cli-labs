---
name: agent-framework-codegen
description: "Microsoft Agent Framework SDK를 사용한 AI 에이전트·워크플로우 코드 생성. USE FOR: Agent Framework 코드 생성, 에이전트 추가, Handoff/GroupChat/Custom 워크플로우 구성, Foundry 연동. DO NOT USE FOR: Azure 리소스 배포·관리."
---

# Microsoft Agent Framework 코드 생성 스킬

이 프로젝트에서 Microsoft Agent Framework SDK로 에이전트·워크플로우를 작성할 때 따르는
패턴과 레퍼런스입니다. 검증 기준은 `agent-framework==1.11.0`이며, 모든 예제는 `src/`의
비동기 콘솔 스크립트 형태입니다.

---

## 1. SDK 임포트 경로

```python
from agent_framework import (
    Agent,
    AgentExecutorResponse,
    Case,
    Default,
    MCPStreamableHTTPTool,
    WorkflowBuilder,
)
from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import (
    ConcurrentBuilder,
    GroupChatBuilder,
    GroupChatState,
    HandoffBuilder,
    SequentialBuilder,
)
from azure.identity import AzureCliCredential
```

- 핵심 클래스와 그래프 빌더는 `agent_framework` 최상위에서 임포트한다.
- Foundry 클라이언트는 `agent_framework.foundry`에서 임포트한다.
- 미리 정의된 오케스트레이션 빌더는 `agent_framework.orchestrations`에서 임포트한다.
- Foundry IQ 컨텍스트 프로바이더는 별도 패키지를 설치한 뒤
  `from agent_framework.azure import AzureAISearchContextProvider`로 임포트한다.

---

## 2. 공통 골격

```python
import asyncio
import os
import sys

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


async def main():
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME") or "gpt-5.4"
    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    credential = AzureCliCredential()
    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model,
        credential=credential,
    )
    # 에이전트 또는 워크플로우 구성


if __name__ == "__main__":
    asyncio.run(main())
```

- 클라이언트와 자격 증명은 한 번 생성해 참여 에이전트가 공유한다.
- 모든 에이전트 호출은 `await` 또는 `async for`를 사용한다.
- 단일 에이전트는 `_streaming.stream_agent()`, 워크플로우는
  `_streaming.stream_workflow()`로 출력한다.

---

## 3. 단일 에이전트

```python
from _streaming import stream_agent

agent = Agent(
    client=client,
    name="기술_어시스턴트",
    instructions="당신은 Microsoft 기술 전문가입니다. 한국어로 간결하게 답변합니다.",
)

await stream_agent(agent, "Microsoft Agent Framework가 무엇인가요?")
```

- 역할·도메인·말투는 `instructions`로 부여한다.
- Handoff 이외의 단일 에이전트 이름은 한국어도 가능하다.
- 비스트리밍이 필요한 경우에만 `result = await agent.run(...)`을 사용한다.

---

## 4. Handoff 워크플로우

Handoff에서는 에이전트 이름이 `handoff_to_<name>` 도구명에 포함되므로
ASCII 영문·숫자·`_`·`.`·`-`만 사용한다.

```python
tech_agent = Agent(
    client=client,
    name="tech_support",
    instructions="당신은 기술 지원 전문가입니다. 한국어로 답변합니다.",
    require_per_service_call_history_persistence=True,
)
billing_agent = Agent(
    client=client,
    name="billing",
    instructions="당신은 결제 지원 전문가입니다. 한국어로 답변합니다.",
    require_per_service_call_history_persistence=True,
)
triage_agent = Agent(
    client=client,
    name="triage",
    instructions=(
        "당신은 접수 담당자입니다. "
        "기술 문제는 handoff_to_tech_support, 결제 문제는 handoff_to_billing 도구로 위임합니다."
    ),
    require_per_service_call_history_persistence=True,
)

workflow = (
    HandoffBuilder(
        name="고객_지원",
        participants=[triage_agent, tech_agent, billing_agent],
    )
    .with_start_agent(triage_agent)
    .add_handoff(triage_agent, [tech_agent, billing_agent])
    .with_autonomous_mode()
    .build()
)

await stream_workflow(workflow, "결제 오류가 발생했어요.")
```

- 모든 참여 `Agent`에 `require_per_service_call_history_persistence=True`가 필요하다.
- `add_handoff()`를 생략하면 기본 mesh topology가 적용된다. 특정 경로만 허용할 때 명시한다.
- 자동 진행이 필요하면 `with_autonomous_mode()`를 사용하고 필요 시 agent별 turn limit을 둔다.

---

## 5. GroupChat 워크플로우

```python
participants = [planner_agent, developer_agent, designer_agent]
speaker_names = [participant.name for participant in participants]


def select_next_speaker(state: GroupChatState) -> str:
    """라운드 로빈으로 다음 발화자를 선택합니다."""
    return speaker_names[state.current_round % len(speaker_names)]


workflow = GroupChatBuilder(
    participants=participants,
    selection_func=select_next_speaker,
    max_rounds=6,
    intermediate_output_from=participants,
).build()

await stream_workflow(workflow, "토론 주제")
```

- `GroupChatState`는 `current_round`, `participants`, `conversation`을 제공한다.
- 무한 토론을 막기 위해 `max_rounds` 또는 `termination_condition`을 둔다.
- 기본 설정에서는 오케스트레이터 종료 메시지만 최종 출력으로 노출된다.
- 참여자 발언을 표시하려면 `intermediate_output_from=participants`를 지정한다.
- 현재 SDK의 참여자 스트림은 `AgentResponseUpdate.author_name`과 `text`로 식별한다.

---

## 6. Sequential·Concurrent 출력 설정

기본 빌더는 최종 단계 또는 집계기만 `output` 이벤트로 노출한다. 교육용 예제에서 각 참여자의
결과를 보이려면 중간 출력 소스를 명시한다.

```python
sequential = SequentialBuilder(
    participants=[analyzer, writer, editor],
    intermediate_output_from=[analyzer, writer],
).build()

concurrent = ConcurrentBuilder(
    participants=[security, performance, ux],
    intermediate_output_from=[security, performance, ux],
).build()
```

- Sequential은 마지막 참여자가 최종 `output`이므로 앞 단계만 중간 출력으로 지정한다.
- Concurrent의 기본 집계기는 모든 응답을 하나의 `AgentResponse`로 모은다.
  참여자 스트림을 함께 노출하면 출력 헬퍼에서 집계 중복을 제거해야 한다.

---

## 7. Python 제어 흐름 기반 순차 처리

간단한 조건 분기는 일반 Python 흐름으로 연결해도 된다.

```python
analysis = await agents["topic_analyzer"].run(input_topic)
route = "tech_writer" if "기술" in str(analysis).split("\n")[0] else "general_writer"
draft = await agents[route].run(f"다음 분석을 바탕으로 초안을 작성하세요.\n{analysis}")
final = await agents["editor"].run(f"다음 초안을 다듬으세요.\n{draft}")
print(final)
```

복잡한 조건 분기·팬아웃·팬인은 `WorkflowBuilder`를 사용한다.

---

## 8. WorkflowBuilder 조건부 그래프

```python
def is_technical_topic(message: AgentExecutorResponse) -> bool:
    """분석 에이전트의 응답 본문에서 기술 주제 여부를 판별합니다."""
    return "기술" in (message.agent_response.text or "")


workflow = (
    WorkflowBuilder(
        start_executor=analyzer_agent,
        output_from=[editor_agent],
    )
    .add_switch_case_edge_group(
        analyzer_agent,
        [
            Case(condition=is_technical_topic, target=tech_writer_agent),
            Default(target=general_writer_agent),
        ],
    )
    .add_edge(tech_writer_agent, editor_agent)
    .add_edge(general_writer_agent, editor_agent)
    .build()
)

result = await workflow.run("Kubernetes 비용 최적화 전략")
for output in result.get_outputs():
    print(output)
```

| 메서드 | 용도 |
|--------|------|
| `WorkflowBuilder(start_executor=...)` | 시작 노드 지정 |
| `.add_edge(source, target)` | 단순 순차 엣지 |
| `.add_switch_case_edge_group(source, cases)` | 순서대로 평가하는 조건 분기 |
| `.add_fan_out_edges(source, targets)` | 같은 메시지를 여러 노드에 전송 |
| `.add_fan_in_edges(sources, target)` | 여러 결과를 한 노드로 수집 |
| `Case(condition=..., target=...)` | 조건이 참일 때의 대상. Agent 소스에서는 `AgentExecutorResponse`를 받음 |
| `Default(target=...)` | 모든 Case가 거짓일 때의 대상 |

---

## 9. MCP 도구 연동

```python
learn_mcp = MCPStreamableHTTPTool(
    name="MicrosoftLearn",
    url="https://learn.microsoft.com/api/mcp",
    description="Microsoft/Azure 공식 문서 검색",
)

async with learn_mcp:
    agent = Agent(
        client=client,
        name="문서_리서치_어시스턴트",
        instructions="답변 전에 공식 문서를 검색하고 출처와 함께 한국어로 답변합니다.",
        tools=learn_mcp,
    )
    await stream_agent(agent, "질문")
```

- MCP 세션은 반드시 `async with` 안에서 연결하고 종료한다.
- 여러 MCP 도구는 `tools=[tool_a, tool_b]`로 전달한다.
- 인증 서버의 `header_provider`는 호출 컨텍스트 인자 하나를 받는다.

```python
import os


def build_headers(_: dict[str, object]) -> dict[str, str]:
    token = os.environ["MCP_ACCESS_TOKEN"]
    return {"Authorization": f"Bearer {token}"}


secured_mcp = MCPStreamableHTTPTool(
    name="SecuredMCP",
    url="https://example.com/mcp",
    header_provider=build_headers,
)
```

- Copilot CLI 개발자용 MCP 설정은 `.mcp.json` 또는 `.github/mcp.json`이다.
  이 절의 MCP 도구는 생성된 Agent Framework 애플리케이션이 런타임에 사용하는 별도 연결이다.

---

## 10. RAG

질문 관련 문서를 검색하고 컨텍스트로 주입한 뒤 답변을 생성한다.

```python
docs = retrieve(question, top_k=2)
context = build_context(docs)
augmented_prompt = (
    f"다음 참고 문서 안의 정보만 사용하세요.\n\n"
    f"--- 참고 문서 ---\n{context}\n\n"
    f"--- 질문 ---\n{question}"
)

agent = Agent(
    client=client,
    name="RAG_어시스턴트",
    instructions=(
        "제공된 문서 안의 정보만 근거로 한국어로 답변하고, "
        "정보가 없으면 모른다고 답합니다."
    ),
)
await stream_agent(agent, augmented_prompt)
```

- 기본 예제 `06_rag_agent.py`는 Azure AI Search 하이브리드 검색을 직접 구현한다.
- Foundry IQ 변형은 `AzureAISearchContextProvider(mode="agentic")`가 모델 호출 전에
  멀티홉 검색 결과를 컨텍스트에 주입한다.
- 검색 품질과 "문서 밖 추측 금지" 지시문을 함께 검증한다.

---

## 11. 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-------------|
| `PROJECT_ENDPOINT 환경 변수를 설정해주세요` | 루트 `.env` 작성과 `load_dotenv` 경로 확인 |
| 인증 실패 | `az login` 재실행, `az account set`으로 구독 선택 |
| Handoff 도구명 400 오류 | Handoff 참여자 `name`을 ASCII 규칙에 맞게 변경 |
| Handoff `build()` persistence 오류 | 모든 참여 Agent에 `require_per_service_call_history_persistence=True` 지정 |
| GroupChat이 끝나지 않음 | `max_rounds` 또는 `termination_condition` 설정 |
| GroupChat이 종료 메시지만 표시 | 참여자를 `intermediate_output_from`에 지정 |
| Concurrent 결과가 비어 있음 | `AgentResponse` 집계 이벤트를 처리하거나 참여자 중간 출력을 지정 |
| 조건 분기가 항상 첫 Case로 감 | Case는 순서대로 평가되므로 좁은 조건부터 배치 |
| pip 의존성 해석 실패 | `requirements.txt`의 검증된 정확 버전을 함께 설치 |
| `ImportError: agent_framework...` | 가상환경 활성화 후 `pip install -r requirements.txt` 재실행 |
