# Azure 리소스 준비 가이드 — `src/` 예제 실제 실행하기

> README의 실습은 **Azure 없이도 완주**할 수 있습니다. 이 문서는 `src/`의 Microsoft Agent Framework
> 예제를 **실제로 실행**해 보고 싶은 분을 위한 리소스 준비 절차입니다.
> Microsoft Learn 공식 문서(하단 [참고 문서](#참고-문서)) 기준으로 작성했습니다.

## 예제별 필요 리소스

| 예제 | Foundry 프로젝트 + 채팅 모델 | Azure AI Search | 임베딩 모델 배포 |
|------|:---:|:---:|:---:|
| `01`~`04` (에이전트·워크플로우) | ✅ | — | — |
| `05` (MCP 도구 연동) | ✅ | — | — |
| `06_rag_agent.py` (하이브리드 RAG) | ✅ | ✅ | ✅ |
| `06_rag_agent_foundry_iq.py` (Foundry IQ) | ✅ | ✅ | ✅ |

## 0. 공통 준비

- **Azure 구독** — 없다면 [무료 계정](https://azure.microsoft.com/pricing/purchase-options/azure-account)을 만듭니다.
- **Azure CLI 2.80.0 이상** — `az version`으로 확인하고 필요 시 `az upgrade`를 실행합니다.
  (2.80.0부터 아래에서 사용하는 `az cognitiveservices account project` 명령을 지원합니다.)

```bash
az login              # 브라우저 인증 — 예제 코드의 AzureCliCredential이 이 세션을 사용합니다
az account show       # 사용할 구독인지 확인
```

이 문서의 예시 이름은 다음과 같습니다. 자유롭게 바꿔 쓰되 **일관되게** 사용하세요.

| 변수 | 예시 값 | 설명 |
|------|---------|------|
| 리소스 그룹 | `maf-lab-rg` | 실습 후 한 번에 삭제할 단위 |
| Foundry 리소스 | `maf-lab-foundry` | `--custom-domain`은 전역 고유해야 함 |
| Foundry 프로젝트 | `maf-lab-project` | `PROJECT_ENDPOINT`의 마지막 경로 |
| 리전 | `eastus` | 모델 가용성에 따라 조정 |
| AI Search 서비스 | `maf-lab-search` | 예제 06 전용 |

## 1. Foundry 리소스·프로젝트 만들기

Foundry 포털(<https://ai.azure.com>)에서 **Create new project**로 만들거나, CLI로 만듭니다.

```bash
# 리소스 그룹
az group create --name maf-lab-rg --location eastus

# Foundry 리소스 (프로젝트 관리 활성화 — 생성 후에는 변경 불가)
az cognitiveservices account create \
  --name maf-lab-foundry \
  --resource-group maf-lab-rg \
  --kind AIServices \
  --sku S0 \
  --location eastus \
  --custom-domain maf-lab-foundry \
  --assign-identity \
  --allow-project-management true

# 프로젝트
az cognitiveservices account project create \
  --name maf-lab-foundry \
  --resource-group maf-lab-rg \
  --project-name maf-lab-project \
  --location eastus
```

> ⚠️ `--custom-domain`이 이미 사용 중이면 `CustomDomainInUse` 오류가 납니다. 다른 이름으로 다시
> 실행하세요. `--assign-identity`를 빼면 프로젝트 생성이 관리 ID 오류로 실패합니다.

## 2. 채팅 모델 배포

이 랩의 기본 모델은 `gpt-5.4`입니다(`.env`의 `MODEL_DEPLOYMENT_NAME`). 먼저 리전에서 사용 가능한
버전·SKU를 확인한 뒤 배포합니다.

```bash
# 리전 가용 버전·SKU 확인
az cognitiveservices model list \
  --location eastus \
  --query "[?model.name=='gpt-5.4'].{version:model.version,skus:join(',',model.skus[].name)}" \
  --output table

# 배포 (model-version은 위에서 확인한 값으로)
az cognitiveservices account deployment create \
  --name maf-lab-foundry \
  --resource-group maf-lab-rg \
  --deployment-name gpt-5.4 \
  --model-name gpt-5.4 \
  --model-version "<확인한 버전>" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name GlobalStandard
```

> 💡 `DeploymentModelNotSupported` 오류는 해당 리전에 모델·버전·SKU 조합이 없다는 뜻입니다.
> 다른 조합이나 리전을 선택하세요. 포털에서는 **Discover → Models**에서 모델을 찾아
> **Deploy**를 선택하면 됩니다. 배포 이름이 곧 `MODEL_DEPLOYMENT_NAME` 값입니다.

## 3. 프로젝트 엔드포인트 확인

```bash
az cognitiveservices account project show \
  --name maf-lab-foundry \
  --resource-group maf-lab-rg \
  --project-name maf-lab-project \
  --query 'properties.endpoints."AI Foundry API"' --output tsv
```

출력이 `https://maf-lab-foundry.services.ai.azure.com/api/projects/maf-lab-project` 형태의
**`PROJECT_ENDPOINT`** 값입니다. 포털에서는 프로젝트 시작 화면에서 복사할 수 있습니다.

> 💡 리소스를 직접 만든 소유자는 보통 바로 호출할 수 있습니다. 팀원에게 권한을 주거나 데이터 평면
> 호출이 거부되면 **Foundry User** 역할(이전 명칭 Azure AI User, 역할 ID
> `53ca6127-db72-4b80-b1b0-d745d6d5456d`)을 프로젝트 범위로 할당하세요.

```bash
PROJECT_ID=$(az cognitiveservices account project show \
  --name maf-lab-foundry --resource-group maf-lab-rg \
  --project-name maf-lab-project --query id -o tsv)

az role assignment create \
  --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" \
  --assignee "<user@example.com>" \
  --assignee-principal-type User \
  --scope "$PROJECT_ID"
```

여기까지 마치면 **예제 01~05를 실행할 수 있습니다.** RAG 예제(06)를 실행하려면 아래를 계속 진행하세요.

## 4. (예제 06) Azure AI Search 만들기 — 키리스(RBAC)

예제 06은 키 없이 Microsoft Entra ID(RBAC)로 인증하므로, 서비스 생성 시 RBAC 인증을 켭니다.

```bash
az search service create \
  --name maf-lab-search \
  --resource-group maf-lab-rg \
  --sku basic \
  --auth-options aadOrApiKey \
  --aad-auth-failure-mode http401WithBearerChallenge
```

로컬 개발 계정(본인)에 데이터·오브젝트 권한 두 가지를 할당합니다
(인덱스 생성 → **Search Service Contributor**, 문서 업로드·조회 → **Search Index Data Contributor**).

```bash
ME=$(az ad signed-in-user show --query id -o tsv)
SEARCH_ID=$(az search service show --name maf-lab-search --resource-group maf-lab-rg --query id -o tsv)

az role assignment create --role "Search Service Contributor"    --assignee "$ME" --scope "$SEARCH_ID"
az role assignment create --role "Search Index Data Contributor" --assignee "$ME" --scope "$SEARCH_ID"
```

`SEARCH_SERVICE_ENDPOINT`는 `https://maf-lab-search.search.windows.net`입니다.

## 5. (예제 06) 임베딩 모델 배포 + Azure OpenAI 권한

문서 임베딩은 Foundry 리소스의 Azure OpenAI 임베딩 배포를 키리스로 호출합니다.

```bash
# 임베딩 모델 배포 (기본값: text-embedding-3-large)
az cognitiveservices account deployment create \
  --name maf-lab-foundry \
  --resource-group maf-lab-rg \
  --deployment-name text-embedding-3-large \
  --model-name text-embedding-3-large \
  --model-version "1" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name GlobalStandard

# 임베딩 API 키리스 호출 권한
ACCOUNT_ID=$(az cognitiveservices account show --name maf-lab-foundry --resource-group maf-lab-rg --query id -o tsv)
az role assignment create --role "Cognitive Services OpenAI User" --assignee "$ME" --scope "$ACCOUNT_ID"
```

`AZURE_OPENAI_ENDPOINT`는 `https://maf-lab-foundry.cognitiveservices.azure.com/`입니다.

> 💡 Foundry IQ 변형(`06_rag_agent_foundry_iq.py`)은 같은 리소스를 쓰되 **별도 인덱스**
> (`SEARCH_INDEX_NAME_IQ`, 기본 `maf-lab-knowledge-iq-v1`)를 자동 생성합니다. 일부 환경에서
> agentic 벡터화가 `.openai.azure.com` 형식을 요구하면 `.env`의 `AZURE_OPENAI_RESOURCE_URL`
> 주석을 해제해 설정하세요.

## 6. `.env` 작성

```bash
cp .env.example .env
```

| `.env` 키 | 채울 값 (이 문서 기준) | 사용 예제 |
|-----------|------------------------|-----------|
| `PROJECT_ENDPOINT` | 3번에서 확인한 엔드포인트 | 전체 |
| `MODEL_DEPLOYMENT_NAME` | `gpt-5.4` (2번 배포 이름) | 전체 |
| `SEARCH_SERVICE_ENDPOINT` | `https://maf-lab-search.search.windows.net` | 06 |
| `SEARCH_INDEX_NAME` | 기본값 유지 (`maf-lab-knowledge-v1`) | 06 |
| `AZURE_OPENAI_ENDPOINT` | `https://maf-lab-foundry.cognitiveservices.azure.com/` | 06 |
| `EMBEDDING_DEPLOYMENT_NAME` | `text-embedding-3-large` (5번 배포 이름) | 06 |

> 🔒 `.env`는 `.gitignore`에 포함되어 커밋되지 않습니다. 시크릿·엔드포인트는 절대 코드에
> 하드코딩하지 마세요.

## 7. 실행·확인

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/01_single_agent.py        # 단일 에이전트 — 스트리밍 한국어 응답이 나오면 성공
python src/04_concurrent_workflow.py # 세 리뷰어의 병렬 검토가 출력되면 성공
python src/06_rag_agent.py           # 첫 실행 시 인덱스 자동 생성·시드 후 [출처: …] 답변

python -m unittest discover -s tests # (선택) 오프라인 회귀 테스트 — Azure 불필요
```

RBAC 역할 할당은 전파에 수 분이 걸릴 수 있습니다. `401`/`403`이 나오면 잠시 후 다시 실행하세요.

## 8. 리소스 정리

실습이 끝나면 리소스 그룹을 삭제해 과금을 방지합니다.

```bash
az group delete --name maf-lab-rg --yes --no-wait
az group exists --name maf-lab-rg   # false가 나오면 삭제 완료
```

## 참고 문서

- [Quickstart: Set up Microsoft Foundry resources](https://learn.microsoft.com/azure/foundry/tutorials/quickstart-create-foundry-resources) — 리소스·프로젝트·모델 배포·엔드포인트
- [Connect to Azure AI Search using roles](https://learn.microsoft.com/azure/search/search-security-rbac) — RBAC 활성화·역할 할당
- [Connect your app to Azure AI Search using identities](https://learn.microsoft.com/azure/search/search-security-rbac-client-code#local-development) — 로컬 개발 키리스 인증
