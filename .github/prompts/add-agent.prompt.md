---
description: "새로운 Agent Framework 에이전트 시나리오를 추가합니다"
mode: "agent"
---

# 새 에이전트 시나리오 추가

## 요청사항

아래 시나리오에 맞는 새 에이전트(또는 워크플로우)를 `src/`에 추가해주세요.

- 파일명: {{file_name}}  (예: 05_my_workflow.py)
- 에이전트/워크플로우명: {{agent_name}}
- 역할: {{role_description}}
- 패턴: 단일 에이전트 / 순차(Sequential) / GroupChat / 동시(Concurrent) / MCP 도구 연동 / RAG / Handoff

## 현재 시나리오 구조 (`src/`)

1. **단일 에이전트** (`01_single_agent.py`) — `Agent(client=client, name=..., instructions=...)` + `stream_agent(agent, prompt)`
2. **순차(Sequential)** (`02_sequential_workflow.py`) — `SequentialBuilder(..., intermediate_output_from=[중간 참여자...])` + `stream_workflow(workflow, topic)`
3. **GroupChat** (`03_group_chat.py`) — `GroupChatBuilder(..., max_rounds=..., intermediate_output_from=participants)` + `stream_workflow(workflow, topic)`
4. **동시(Concurrent)** (`04_concurrent_workflow.py`) — `ConcurrentBuilder(..., intermediate_output_from=participants)` + `stream_workflow(workflow, design)`
5. **MCP 도구 연동** (`05_mcp_agent.py`) — `MCPStreamableHTTPTool(url=...)` + `Agent(tools=mcp_tool)` + `stream_agent(agent, prompt)`
6. **RAG** (`06_rag_agent.py`) — 검색(Search) → 증강(Augment) → 단일 에이전트 실행 + `stream_agent(agent, augmented_prompt)`
7. **RAG (Foundry IQ)** (`06_rag_agent_foundry_iq.py`) — Foundry IQ 검색 결과를 바탕으로 단일 에이전트를 실행 + `stream_agent(agent, question)`

## 규칙

- 공통 골격(`FoundryChatClient`+`Agent` 생성, `PROJECT_ENDPOINT` 검증 후 한국어 오류 + `sys.exit(1)`, import 경로)은 `agent-framework-codegen` 스킬을 따른다
- 모든 호출은 `async/await`, 진입점은 `asyncio.run(main())`
- **스트리밍 출력**: 단일 에이전트는 `from _streaming import stream_agent`, 워크플로우는
  `from _streaming import stream_workflow` (`agent.run()` 직접 print 금지)
- `instructions`와 콘솔 출력은 한국어로 작성
- 반복형 워크플로우(GroupChat·Handoff)는 `max_rounds`·종료 조건·turn limit 중 적절한 제한을 둔다
- 실습에서 참여자별 결과를 보여줘야 하면 빌더의 `intermediate_output_from`을 명시한다
