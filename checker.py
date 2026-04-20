import requests
import json
import os
from datetime import datetime, timezone, timedelta

# ============================================================
# 설정값
# ============================================================
COOKIE = os.environ.get("NAVER_COOKIE", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

BUSINESS_TYPE_ID = 13
BUSINESS_ID = "1389149"
BIZ_ITEM_ID = "6663752"

# 한국 시간 기준으로 오늘 날짜 계산 (UTC+9)
KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)
START_DATE = now_kst.strftime("%Y-%m-%dT00:00:00")
END_DATE = "2027-02-28T23:59:59"

BOOKING_URL = "https://map.naver.com/p/entry/place/1774854927?placePath=/booking"

# ============================================================

def send_telegram(message: str):
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
        "variables": {
            "scheduleParams": {
                "businessTypeId": BUSINESS_TYPE_ID,
                "businessId": BUSINESS_ID,
                "bizItemId": BIZ_ITEM_ID,
                "startDateTime": START_DATE,
                "endDateTime": END_DATE,
                "fixedTime": True,
                "includesHolidaySchedules": True
            }
        },
        "query": "query hourlySchedule($scheduleParams: ScheduleParams) {\n  schedule(input: $scheduleParams) {\n    bizItemSchedule {\n      hourly {\n        id\n        name\n        slotId\n        scheduleId\n        detailScheduleId\n        unitStartDateTime\n        unitStartTime\n        unitBookingCount\n        unitStock\n        bookingCount\n        stock\n        isBusinessDay\n        isSaleDay\n        isUnitSaleDay\n        isUnitBusinessDay\n        isHoliday\n        duration\n        desc\n        minBookingCount\n        maxBookingCount\n        saleStartDateTime\n        saleEndDateTime\n        seatGroups {\n          color\n          maxPrice\n          name\n          remainStock\n          __typename\n        }\n        prices {\n          groupName\n          isDefault\n          price\n          priceId\n          scheduleId\n          priceTypeCode\n          name\n          normalPrice\n          desc\n          order\n          groupOrder\n          slotId\n          agencyKey\n          bookingCount\n          isImp\n          saleStartDateTime\n          saleEndDateTime\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}"
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)

        # 401/403은 쿠키 만료 신호
        if res.status_code in (401, 403):
            send_telegram(
                "⚠️ <b>네이버 쿠키 만료!</b>\n\n"
                "GitHub Secrets의 NAVER_COOKIE를 새로 업데이트해주세요.\n\n"
                "방법: 네이버 예약 페이지 → F12 → Network → hourlySchedule → Headers → Cookie 복사"
            )
            print("❌ 쿠키 만료 (401/403) - 텔레그램 알림 발송")
            return []

        res.raise_for_status()
        data = res.json()

        # 응답은 200인데 로그인 세션 만료된 경우
        if "errors" in data or data.get("data", {}).get("schedule") is None:
            send_telegram(
                "⚠️ <b>네이버 쿠키 만료!</b>\n\n"
                "GitHub Secrets의 NAVER_COOKIE를 새로 업데이트해주세요.\n\n"
                "방법: 네이버 예약 페이지 → F12 → Network → hourlySchedule → Headers → Cookie 복사"
            )
            print("❌ 세션 만료 - 텔레그램 알림 발송")
            return []

    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        return []

    available_slots = []
    try:
        biz_item_schedule = data["data"]["schedule"]["bizItemSchedule"]

        # bizItemSchedule이 dict인 경우 (리스트가 아닐 수 있음)
        if isinstance(biz_item_schedule, dict):
            all_days = [biz_item_schedule]
        elif isinstance(biz_item_schedule, list):
            all_days = biz_item_schedule
        else:
            print(f"⚠️ 예상치 못한 bizItemSchedule 타입: {type(biz_item_schedule)}")
            return []

        for day in all_days:
            if not isinstance(day, dict):
                print(f"⚠️ day가 dict가 아님: {type(day)} / 값: {day}")
                continue

            hourly_slots = day.get("hourly", [])
            if hourly_slots is None:
                continue

            for slot in hourly_slots:
                if not isinstance(slot, dict):
                    continue

                unit_stock = slot.get("unitStock", 0) or 0
                unit_booking_count = slot.get("unitBookingCount", 0) or 0
                is_unit_sale_day = slot.get("isUnitSaleDay", False)
                is_unit_business_day = slot.get("isUnitBusinessDay", False)
                unit_start = slot.get("unitStartDateTime", "") or slot.get("unitStartTime", "")

                # 실제 예약 가능 조건: 단위 영업일 + 단위 판매일 + 잔여석 있음
                remaining = unit_stock - unit_booking_count
                if is_unit_business_day and is_unit_sale_day and remaining > 0:
                    available_slots.append({
                        "datetime": unit_start,
                        "remaining": remaining,
                        "name": slot.get("name", "") or "상담+진료"
                    })

    except (KeyError, TypeError) as e:
        print(f"❌ 응답 파싱 실패: {e}")
        print(f"전체 응답: {json.dumps(data, ensure_ascii=False)[:2000]}")

    return available_slots


def main():
    print(f"🔍 체크 시작: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} (KST)")

    # GitHub Actions에서 DAILY_REPORT=true 환경변수로 구분
    is_daily_report = os.environ.get("DAILY_REPORT", "false").lower() == "true"

    if not COOKIE:
        print("❌ NAVER_COOKIE 환경변수가 없습니다.")
        return
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID 환경변수가 없습니다.")
        return

    slots = check_available_slots()

    def to_kst(dt_str):
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            dt_kst = dt.astimezone(KST)
            return dt_kst.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return dt_str[:16].replace("T", " ")

    if slots:
        print(f"🎉 빈 슬롯 {len(slots)}개 발견!")
        slot_list = "\n".join([
            f"  📅 {to_kst(s['datetime'])} KST (잔여 {s['remaining']}건)"
            for s in slots[:10]
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

        # 매일 오전 9시 리포트일 때만 정상 작동 확인 메시지 발송
        if is_daily_report:
            send_telegram(
                f"✅ <b>모니터링 정상 작동 중</b>\n\n"
                f"📅 {now_kst.strftime('%Y-%m-%d %H:%M')} KST 기준\n"
                f"현재 빈 슬롯 없음. 취소 발생 시 즉시 알림 드릴게요!"
            )
            print("📢 일일 리포트 발송 완료")


if __name__ == "__main__":
    main()
