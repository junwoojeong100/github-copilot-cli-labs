# GitHub 멀티 계정 설정 가이드

> Git 작업용 계정과 GitHub Copilot 구독 계정을 한 머신에서 안전하게 분리하는 HTTPS 기준 절차입니다.

## 핵심 원리

| 용도 | 인증 주체 | 전환 방법 |
|------|-----------|-----------|
| `git push`/`pull`, `gh` 명령 | GitHub CLI의 현재 active 계정 | `gh auth switch` |
| Git 커밋 작성자 | Git의 `user.name`·`user.email` | 리포별 `git config --local` |
| Copilot CLI | Copilot CLI에 로그인한 계정 또는 전용 환경변수 | `/login`·`/user` |

`gh`의 active 계정과 Copilot CLI 로그인은 서로 독립적입니다. Git 작업용 계정을 active로 유지한 채
Copilot CLI에는 구독 계정으로 따로 로그인할 수 있습니다.

---

## 1단계: GitHub CLI에 계정 등록

두 계정을 차례로 등록합니다. 각 브라우저 인증 단계에서 올바른 계정을 선택하세요.

```bash
gh auth login --hostname github.com --git-protocol https
gh auth login --hostname github.com --git-protocol https
gh auth status
```

`gh auth status`에 `<git-account>`와 `<copilot-account>`가 모두 표시되는지 확인합니다.

> `GH_TOKEN` 또는 `GITHUB_TOKEN`이 셸에 설정되어 있으면 저장된 계정보다 우선할 수 있습니다.
> 대화형 멀티 계정 전환을 사용할 때는 불필요한 토큰 환경변수를 제거하세요.

---

## 2단계: Git 작업 계정 선택

Git 작업에 사용할 계정을 active로 전환하고, GitHub CLI를 HTTPS credential helper로 등록합니다.

```bash
gh auth switch --hostname github.com --user <git-account>
gh auth setup-git --hostname github.com
gh api user --jq .login
```

마지막 명령이 `<git-account>`를 출력해야 합니다. `gh auth setup-git`은 GitHub CLI가 관리하는 자격
증명을 Git에 연결하므로, 토큰을 직접 출력하거나 별도 helper 스크립트에 저장할 필요가 없습니다.

다른 GitHub 계정으로 Git 작업을 전환할 때는 다음처럼 active 계정만 바꿉니다.

```bash
gh auth switch --hostname github.com --user <other-git-account>
gh api user --jq .login
```

---

## 3단계: 커밋 작성자 정보 설정

인증 계정과 커밋 작성자 정보는 별도입니다. 여러 계정을 쓴다면 전역값보다 리포별 설정을 권장합니다.

```bash
git config --local user.name "<git-account>"
git config --local user.email "<verified-email>"

git config --local --get user.name
git config --local --get user.email
```

GitHub 프로필에 등록된 이메일 또는 계정의 `noreply` 이메일을 사용해야 커밋이 올바른 계정에 연결됩니다.

---

## 4단계: Copilot 구독 계정으로 로그인

저장소 루트에서 Copilot CLI를 시작하고 Copilot 구독이 있는 계정으로 로그인합니다.

```bash
copilot
```

```text
> /login
> /user
```

`/user`에서 `<copilot-account>`가 현재 Copilot 사용자로 선택됐는지 확인합니다. 이 과정에서
`gh auth switch`를 `<copilot-account>`로 바꿀 필요는 없습니다.

브라우저 로그인을 사용할 수 없는 자동화 환경에서는 개인 계정에서 만든 **fine-grained PAT**에
`Copilot Requests` 권한을 부여한 뒤 다음 우선순위의 환경변수 중 하나로 전달할 수 있습니다.

```text
COPILOT_GITHUB_TOKEN > GH_TOKEN > GITHUB_TOKEN
```

Classic PAT(`ghp_` 접두사)는 Copilot CLI 인증에 사용할 수 없습니다. 토큰 값은 문서·스크립트·셸
히스토리에 기록하지 말고 CI 시크릿 또는 운영체제의 보안 저장소로 주입하세요.

---

## 최종 확인

```bash
# gh와 HTTPS Git 작업에 쓰일 active 계정
gh auth status
gh api user --jq .login

# 현재 리포의 커밋 작성자
git config --local --get user.name
git config --local --get user.email
```

Copilot CLI 안에서는 `/user`로 구독 계정을 확인합니다. 토큰 자체를 출력하는 `gh auth token`이나
`git credential fill`은 검증 목적으로 사용하지 마세요.

---

## 문제 해결

| 증상 | 해결 |
|------|------|
| `gh`가 잘못된 계정으로 동작 | `gh auth status` 확인 후 `gh auth switch --hostname github.com --user <git-account>` |
| Git push가 다른 계정 권한으로 실패 | `gh auth switch` 후 `gh auth setup-git --hostname github.com` 재실행 |
| `gh auth switch` 결과가 환경변수와 다름 | 셸의 `GH_TOKEN`·`GITHUB_TOKEN` 제거 후 다시 확인 |
| Copilot이 Git 작업 계정으로 로그인됨 | Copilot CLI에서 `/logout` 후 `/login`, 이어서 `/user` 확인 |
| PAT가 거부됨 | Classic PAT 대신 `Copilot Requests` 권한이 있는 fine-grained PAT 사용 |
| 커밋이 잘못된 프로필에 연결됨 | 해당 리포의 `user.name`·`user.email`을 `--local`로 수정 |

## 보안 주의 사항

1. `~/.config/gh/hosts.yml`을 직접 편집하거나 토큰을 복사하지 않습니다.
2. 기존 글로벌 credential helper를 빈 값으로 초기화하지 않습니다.
3. 토큰을 출력하는 커스텀 credential helper를 만들지 않습니다.
4. SSH로 여러 Git 계정을 동시에 고정해야 한다면 계정별 키와 `~/.ssh/config` Host alias를 사용합니다.
