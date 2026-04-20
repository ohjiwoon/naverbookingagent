import requests
import json
import os
from datetime import datetime, timedelta

# ============================================================
# 설정값 (GitHub Actions Secrets에서 환경변수로 주입)
# ============================================================
COOKIE = os.environ.get("NAVER_COOKIE", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# 네이버 예약 API 설정
BUSINESS_TYPE_ID = 13
BUSINESS_ID = "1389149"
BIZ_ITEM_ID = "6663752"

# 체크할 날짜 범위 (오늘부터 1년치)
START_DATE = datetime.now().strftime("%Y-%m-%dT00:00:00")
END_DATE = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT23:59:59")

BOOKING_URL = "https://map.naver.com/p/entry/place/1774854927?placePath=/booking"

# ============================================================

def send_telegram(message: str):
    """텔레그램으로 알림 발송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        print("✅ 텔레그램 알림 발송 완료")
    except Exception as e:
        print(f"❌ 텔레그램 발송 실패: {e}")


def check_available_slots() -> list:
    """네이버 예약 API 호출 → 빈 슬롯 반환"""
    url = "https://m.booking.naver.com/graphql?opName=hourlySchedule"

    headers = {
        "Content-Type": "application/json",
        "Origin": "https://m.booking.naver.com",
        "Referer": "https://m.booking.naver.com/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Cookie": COOKIE,
    }

    payload = {
        "operationName": "hourlySchedule",
        "query": """
            query hourlySchedule($scheduleParams: ScheduleParams) {
              schedule(input: $scheduleParams) {
                bizItemSchedule {
                  date
                  slots {
                    time
                    available
                    remainingCount
                  }
                }
                __typename
              }
            }
        """,
        "variables": {
            "scheduleParams": {
                "businessTypeId": BUSINESS_TYPE_ID,
                "businessId": BUSINESS_ID,
                "bizItemId": BIZ_ITEM_ID,
                "startDateTime": START_DATE,
                "endDateTime": END_DATE,
                "fixedTime": True,
                "includesHolidaySchedules": True,
            }
        }
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        return []

    # 빈 슬롯 파싱
    available_slots = []
    try:
        schedules = data["data"]["schedule"]["bizItemSchedule"]
        for day in schedules:
            date = day.get("date", "")
            slots = day.get("slots", [])
            for slot in slots:
                if slot.get("available") and slot.get("remainingCount", 0) > 0:
                    available_slots.append({
                        "date": date,
                        "time": slot.get("time", ""),
                        "remaining": slot.get("remainingCount", 0)
                    })
    except (KeyError, TypeError) as e:
        print(f"❌ 응답 파싱 실패: {e}")
        print(f"응답 내용: {json.dumps(data, ensure_ascii=False)[:500]}")

    return available_slots


def main():
    print(f"🔍 체크 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not COOKIE:
        print("❌ NAVER_COOKIE 환경변수가 없습니다.")
        return
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID 환경변수가 없습니다.")
        return

    slots = check_available_slots()

    if slots:
        print(f"🎉 빈 슬롯 {len(slots)}개 발견!")

        # 메시지 구성
        slot_list = "\n".join([
            f"  📅 {s['date']} {s['time']} (잔여 {s['remaining']}건)"
            for s in slots[:10]  # 최대 10개만 표시
        ])
        message = (
            f"🚨 <b>네이버 예약 빈 슬롯 발생!</b>\n\n"
            f"박철형 원장님 상담+진료 예약 가능\n\n"
            f"{slot_list}\n\n"
            f"👉 <a href='{BOOKING_URL}'>지금 바로 예약하기</a>"
        )
        send_telegram(message)
    else:
        print("😴 빈 슬롯 없음. 다음 체크를 기다립니다.")


if __name__ == "__main__":
    main()
