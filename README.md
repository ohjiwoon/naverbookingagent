# 네이버 예약 슬롯 체커

박철형 원장님 상담+진료 예약 취소 슬롯을 자동으로 감지해서 텔레그램으로 알려주는 봇입니다.

---

## 세팅 순서

### 1단계. 텔레그램 봇 만들기

1. 텔레그램 앱 → **@BotFather** 검색
2. `/newbot` 입력 → 봇 이름 설정
3. **API Token** 받아두기 (예: `7123456789:AAFxxx...`)
4. 본인 텔레그램에서 그 봇에게 아무 메시지 보내기
5. 브라우저에서 아래 URL 접속 → `id` 값이 chat_id
   ```
   https://api.telegram.org/bot{토큰}/getUpdates
   ```

---

### 2단계. GitHub 레포지토리 만들기

1. [github.com](https://github.com) → **New repository**
2. 이 폴더의 파일들을 모두 업로드
   - `checker.py`
   - `requirements.txt`
   - `.github/workflows/check.yml`

---

### 3단계. GitHub Secrets 등록

레포지토리 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 값 |
|-------------|-----|
| `NAVER_COOKIE` | 개발자도구에서 복사한 Cookie 전체 값 |
| `TELEGRAM_TOKEN` | BotFather에서 받은 토큰 |
| `TELEGRAM_CHAT_ID` | getUpdates에서 확인한 id 값 |

---

### 4단계. Actions 활성화

레포지토리 → **Actions** 탭 → **"I understand my workflows, go ahead and enable them"** 클릭

---

## 주의사항

### 쿠키 만료 문제 (가장 중요!)
- 네이버 로그인 쿠키는 **2~4주마다 만료**됩니다
- 만료되면 API 호출 실패 → 텔레그램 알림도 안 옴
- 주기적으로 개발자도구에서 쿠키를 새로 복사해서 GitHub Secrets 업데이트 필요

### 쿠키 갱신 방법
1. 네이버 예약 페이지 접속
2. F12 → Network → hourlySchedule 클릭
3. Headers → Cookie 값 복사
4. GitHub Secrets → NAVER_COOKIE 값 업데이트

### 실행 주기
- 기본: **10분마다** 자동 실행
- GitHub Actions 무료 플랜 월 2,000분 제한 (10분 간격이면 월 약 4,320분 → 유료 초과 가능)
- 초과 방지: `check.yml`에서 `*/10` → `*/30` 으로 바꾸면 30분마다 실행

---

## 수동 실행 방법

GitHub → Actions → "네이버 예약 슬롯 체커" → **Run workflow**
