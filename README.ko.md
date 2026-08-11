# 👁️ Claude Vision — Claude에게 눈을 달아주다

> **네이티브 이미지 이해 능력이 없는 LLM에 시각을 부여**: 스크린샷, UI 재현, OCR, 이미지 비교, 하드웨어 사진 인식 — 모두 두바오(Doubao) 비전 모델(Volcano Engine Ark)로 자동 처리.

"모델이 이미지를 볼 수 없다"는 아픈 경험에서 "이미지를 올리면 즉시 분석"까지 다듬어낸 완전한 솔루션.

---

## 🚀 30초 복제: 다른 에이전트용 퀵스타트 프롬프트

> 이 내용을 아무 에이전트(Claude / ChatGPT / 기타)에 붙여넣으면 이 비전 기능을 빠르게 학습할 수 있습니다:

```
당신은 나의 시각 분석 어시스턴트입니다. 이 환경의 모델은 이미지를 직접 볼 수 없을 수 있습니다:
1. `vision_doubao.py` 스크립트로 두바오 비전 모델(Volcano Engine Ark)을 호출하여 이미지 분석
2. 키 해결 순서: 환경변수 ARK_API_KEY → 1Password op CLI (OP_REF 참조) → 오류
3. 사용자가 이미지/스크린샷/PDF를 업로드하면 → 자동 분석. "볼까요?"라고 묻지 말고, "unsupported file"이라고 보고하지 말 것
4. 이미지는 uploads 디렉토리에 있음. bash로 찾기 (ls /sessions/*/mnt/uploads/)
5. 모드 선택: UI스크린샷=A(재현); 버그UI=B; 에러로그=C; 문자/표=D; 실물사진=E; 이미지비교=compare
6. 큰 이미지는 먼저 1280px로 축소 (2.1-pro 딥씽킹은 큰 이미지에서 타임아웃); webp는 JPEG로 변환; PDF는 먼저 이미지로 변환
7. 실행 전 프록시 해제: unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy NO_PROXY no_proxy
8. 기본은 doubao-seed-2-1-pro(품질 우선). 배치는 --model doubao-seed-2-0-mini

사용법:
  python3 vision_doubao.py <이미지> A "지시"   # UI 재현
  python3 vision_doubao.py <이미지> B          # 문제 위치
  python3 vision_doubao.py <이미지> C          # 에러 로그 추출
  python3 vision_doubao.py <이미지> D          # OCR
  python3 vision_doubao.py <이미지> E "지시"   # 일반 설명
  python3 vision_doubao.py compare a b "지시"  # 이미지 비교
```

**위 프롬프트 복사 + `vision_doubao.py` 다운로드하면 완전한 비전 분석 기능을 갖추게 됩니다.**

---

## 💡 왜 만들었나

### 문제: 모델이 이미지를 볼 수 없음

이 환경의 모델(Haiku 4.5)에는 **신뢰할 수 있는 내장 이미지 이해 기능이 없습니다**. 사용자가 이미지를 업로드할 때마다 모델이 표시합니다:

> `[Unsupported Image]` / "I can't see the image"

이미지를 다루는 작업(UI 디자인, 하드웨어 개발, 문서 OCR)에는 치명적입니다.

### 해결책: 외부 비전 레이어

모델에 눈이 없다면 **외부 눈**을 달아주세요 — **두바오 비전 모델**(Volcano Engine Ark API)을 호출하여 이미지를 보고 텍스트로 반환합니다.

```
사용자가 이미지 업로드 → Claude 스크립트가 두바오 비전 호출 → 구조화된 텍스트 반환 → Claude가 이해하고 응답
```

---

## 📚 여정 타임라인 (교훈)

| 날짜 | 단계 | 주요 결정 / 함정 |
|------|------|----------------|
| 2026-08-08 | **Qwen 시대** | Qwen3-VL-flash를 DashScope API로 비전 레이어에 사용. OCR/로그 추출은 정확 |
| 2026-08-08 | **환각 발견** | Qwen3-VL-flash는 **이미지 비교에서 환각** — 존재하지 않는 차이를 조작. 결과는 "검증 체크리스트"로만 사용 가능 |
| 2026-08-10 | **두바오로 전환** | 사용자가 전환 결정. doubao-seed-1.6-vision vs 2.0-mini vs **2.1-pro** 평가 |
| 2026-08-10 | **듀얼 모델 결정** | 2.1-pro(품질 우선, 딥씽킹) 메인 + 2-0-mini(배치 속도) 폴백 |
| 2026-08-11 | **1Password 통합** | 키 관리: 수동 붙여넣기 → op CLI 자동 조회 → 스킬에 토큰 내장, 모든 세션에서 사용 가능 |
| 2026-08-11 | **GitHub 공개** | 코드 일반화(하드코딩 제거), monah-studio/claude-vision에 푸시 |

### 주요 함정 체크리스트

1. **Qwen3-VL-flash 이미지 비교 환각** → 두바오 2.1-pro로 전환(딥씽킹으로 안정)
2. **큰 이미지 + 딥씽킹 타임아웃** → 스크립트가 >2048px 자동 축소. 먼저 1280px 축소 권장
3. **webp 거부** → JPEG로 변환(PIL convert RGB)
4. **샌드박스 프록시의 비정상 IPv6** → 실행 전 반드시 `unset ...proxy...`. 안 하면 HTTP 라이브러리 충돌
5. **`op read` 제목에 공백/괄호 있으면 파싱 실패** → 항상 항목 ID 사용
6. **스킬 base64 손상** → 재생성 시 디코드 일치성 검증

---

## ✨ 최종 솔루션

### 아키텍처

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  이미지 업로드 │ ──▶ │    Claude Agent   │ ──▶ │ 두바오 비전       │
│ (uploads dir) │     │ (네이티브 시각 없음)│     │ 2.1-pro (Ark API)│
└─────────────┘     └──────────────────┘     └──────────────────┘
                           │  ▲
                           ▼  │
                    ┌──────────────────┐
                    │ 1Password 키      │
                    │ (op CLI 자동)     │
                    └──────────────────┘
```

### 핵심 기능

| 기능 | 설명 |
|------|------|
| 🖼️ **5가지 인식 모드** | UI 재현 / 문제 위치 / 로그 추출 / OCR / 일반 설명 |
| 🔄 **이미지 비교** | 실제 차이 탐지, 환각 방지 |
| 📦 **자동 축소** | >2048px 자동 리사이즈, 과대 API 요청 방지 |
| 🔑 **자동 키 조회** | 환경변수 → 1Password op → 명확한 오류. 하드코딩 금지 |
| 🚀 **듀얼 모델** | 품질 우선(딥씽킹) + 배치 속도(저지연) |
| 🪶 **서드파티 의존성 없음** | 순수 Python 표준 라이브러리 + Pillow |

### 기술 스택

- **비전 모델**: Doubao Seed 2.1 Pro(`doubao-seed-2-1-pro-260628`) / 2.0 Mini
- **API**: Volcano Engine Ark(OpenAI 호환)
- **인증**: 1Password CLI(`op`) + Service Account 토큰
- **언어**: Python 3.8+(urllib + Pillow)

---

## 🚀 퀵스타트

### 1. 의존성 설치

```bash
pip install Pillow
```

### 2. API 키 설정 (택일)

```bash
# 방법 1: 환경변수
export ARK_API_KEY="ark-..."

# 방법 2: 1Password (권장)
# op read "op://Claude Code/Ark API Key (豆包视觉)/credential"
```

### 3. 첫 이미지 분석

```bash
python3 vision_doubao.py your_image.png E "이 이미지를 설명하세요"
```

---

## 📖 사용자 가이드

### 모드 참조

| 모드 | 용도 | 예 |
|------|------|-----|
| `A` | **UI 픽셀 재현**: 레이아웃/좌표/색/폰트 | `vision_doubao.py ui.png A "페이지 재현"` |
| `B` | **문제 위치**: UI 버그/정렬/겹침 | `vision_doubao.py bug.png B` |
| `C` | **에러 로그 추출**: 원문 그대로 | `vision_doubao.py error.png C` |
| `D` | **OCR**: 텍스트 원문 추출 | `vision_doubao.py doc.png D` |
| `E` | **일반 설명**: 실물/장면/사진 | `vision_doubao.py photo.jpg E` |
| `compare` | **이미지 비교**: 실제 차이 탐지 | `vision_doubao.py compare a.png b.png` |

### 모델 전환

```bash
# 품질 우선 (기본)
python3 vision_doubao.py img.png E

# 배치 속도
python3 vision_doubao.py img.png D --model doubao-seed-2-0-mini-260428

# 환경변수
export ARK_MODEL="doubao-seed-2-0-mini-260428"
```

### 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ARK_API_KEY` | — | Volcano Engine Ark 키(최우선) |
| `ARK_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3/chat/completions` | API 엔드포인트 |
| `ARK_MODEL` | `doubao-seed-2-1-pro-260628` | 기본 모델 |
| `OP_REF` | `op://Claude Code/Ark API Key (豆包视觉)/credential` | 1Password 참조 |

---

## 🔁 자동화 워크플로우

### UI 픽셀 재현 루프

```
디자인 → 두바오 비전 A 분석 → HTML/CSS 작성 → 스크린샷 → compare 이미지 비교 → 수정 → 일치
```

### 업로드 시 자동 분석

Claude 메모리 규칙을 설정하면, **사용자가 이미지 업로드 → 에이전트가 자동 분석**, 수동 트리거 불필요:
- uploads 디렉토리 자동 검색
- 모드 자동 선택(불확실하면 E)
- 자동 축소/형식 변환
- 결과 직접 표시

---

## ⚠️ 문제 해결

| 문제 | 해결책 |
|------|--------|
| 큰 이미지 타임아웃 | 먼저 1280px로 축소 |
| webp 거부 | JPEG로 변환 |
| 프록시 오류 `Invalid port` | `unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy NO_PROXY no_proxy` |
| 401 키 무효 | Volcano Engine 콘솔에서 키/잔액 확인 |
| 429 속도 제한 | 나중에 재시도 |
| 403 권한 없음 | 모델 전환 |

---

## 📚 참조

모든 모델, 플랫폼, 의존성, 라이선스는 [REFERENCES.md](REFERENCES.md) 참조.

- **비전 모델**: [두바오 Seed (Volcano Engine Ark)](https://www.volcengine.com/product/ark)
- **API 플랫폼**: [Volcano Engine](https://www.volcengine.com/) · [Ark 문서](https://www.volcengine.com/docs/82379)
- **인증**: [1Password Developer](https://developer.1password.com/)
- **의존성**: [Pillow](https://python-pillow.org/) · [Python](https://www.python.org/)

---

## 🤝 감사의 말

"모델이 이미지를 볼 수 없다"는 실제 고통에서 태어나 수차례 반복을 거쳐 다듬어졌습니다. 강력한 비전 이해를 제공한 두바오 Seed, 안전한 인증 관리를 제공한 1Password에 감사드립니다.

---

## 📄 라이선스

MIT — [LICENSE](LICENSE) 참조. 자유롭게 사용·수정·공유할 수 있습니다.
