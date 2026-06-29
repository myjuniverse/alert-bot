from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime
import requests
import signal
import sys
import os

# === 텔레그램 설정 ===
# 로컬 실행 시: 아래 값을 직접 입력하거나 환경변수로 설정
# GitHub Actions 실행 시: Secrets에서 자동으로 주입됨
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7751593135:AAFcb-bjt6SgLJgLFoas65Vhs7NaR67BEHY")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "7950312215")
# ===================

def send_telegram(message):
    """텔레그램 메시지 전송"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("  ✅ 텔레그램 알림 전송")
        else:
            print(f"  ❌ 텔레그램 실패: {response.text}")
    except Exception as e:
        print(f"  텔레그램 오류: {e}")


def check_naver_booking(url, target_date):
    """
    네이버 예약 페이지에서 특정 날짜 활성화 여부 확인.
    target_date: "2026-07-10" 형식
    반환: True(예약 가능) / False(불가) / None(오류)
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,800')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        print(f"  페이지 로드 중: {url}")
        driver.get(url)

        # 달력 로딩 대기 (최대 15초)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button, td, [role='gridcell']"))
            )
        except Exception:
            pass
        time.sleep(3)

        # 디버그용 스크린샷 (첫 실행 시 확인용)
        screenshot_path = "naver_booking_screenshot.png"
        driver.save_screenshot(screenshot_path)
        print(f"  스크린샷 저장: {screenshot_path}")

        # 날짜에서 월, 일 추출
        # target_date = "2026-07-10" → month="7", day="10"
        parts = target_date.split("-")
        day_num = str(int(parts[2]))  # "10" (앞 0 제거)

        # 달력 날짜 셀렉터 후보 (네이버 예약 UI에 맞게 순서대로 시도)
        selectors = [
            f"[data-date='{target_date}']",
            f"[data-day='{target_date}']",
            f"button[aria-label*='{day_num}일']",
            f"td[aria-label*='{day_num}일']",
            f"[data-value='{target_date}']",
        ]

        target_el = None
        for sel in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            if elements:
                target_el = elements[0]
                print(f"  셀렉터 '{sel}' 으로 날짜 요소 발견")
                break

        # 셀렉터 전부 실패 시 텍스트로 탐색
        if target_el is None:
            print(f"  CSS 셀렉터 실패 → 버튼 텍스트로 탐색 ('{day_num}')")
            all_buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in all_buttons:
                if btn.text.strip() == day_num:
                    target_el = btn
                    print(f"  텍스트 '{day_num}'으로 버튼 발견")
                    break

        if target_el is None:
            print(f"  ⚠️ '{target_date}' 날짜 요소를 찾지 못했습니다.")
            print("  → naver_booking_screenshot.png 를 열어 달력 구조를 확인하세요.")
            return None

        # 활성화 여부 확인
        is_disabled  = target_el.get_attribute("disabled")
        aria_disabled = target_el.get_attribute("aria-disabled")
        class_attr   = (target_el.get_attribute("class") or "").lower()

        unavail_keywords = {"disabled", "closed", "soldout", "past",
                            "unavailable", "unable", "block", "inactive"}
        has_unavail_class = any(k in class_attr for k in unavail_keywords)

        print(f"  날짜 {target_date} → disabled={is_disabled}, "
              f"aria-disabled={aria_disabled}, class={class_attr[:80]}")

        if is_disabled == "true" or is_disabled is True:
            return False
        if aria_disabled == "true":
            return False
        if has_unavail_class:
            return False

        # disabled 없고 비활성 클래스도 없으면 예약 가능
        return True

    except Exception as e:
        print(f"  오류: {e}")
        return None

    finally:
        driver.quit()


def signal_handler(sig, frame):
    print('\n\n' + '='*60)
    print('프로그램을 수동으로 종료합니다.')
    print('='*60)
    send_telegram("네이버 예약 모니터링을 수동으로 종료했습니다.")
    sys.exit(0)


def run_once():
    """한 번만 확인하고 종료 (GitHub Actions용)"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{current_time}] 확인 중...")

    result = check_naver_booking(URL, TARGET_DATE)

    if result is True:
        message = (
            f"<b>네이버 예약 가능!</b>\n\n"
            f"상품: {PRODUCT_NAME}\n"
            f"날짜: {TARGET_DATE}\n"
            f"발견 시간: {current_time}\n\n"
            f'<a href="{URL}">지금 바로 예약하기</a>'
        )
        send_telegram(message)
        print("✅ 예약 가능 → 텔레그램 알림 전송")
    elif result is False:
        print(f"❌ 아직 예약 불가 ({TARGET_DATE})")
    else:
        print("⚠️ 확인 실패 (스크린샷 확인 필요)")


def run_loop():
    """무한 루프로 반복 확인 (로컬 실행용)"""
    signal.signal(signal.SIGINT, signal_handler)

    start_time = datetime.now()
    interval_text = f"{CHECK_INTERVAL}초 ({CHECK_INTERVAL//60}분)마다" if CHECK_INTERVAL >= 60 else f"{CHECK_INTERVAL}초마다"

    send_telegram(f"""네이버 예약 모니터링 시작!

상품: {PRODUCT_NAME}
날짜: {TARGET_DATE}
확인 주기: {interval_text}

예약 가능해지면 바로 알려드립니다.""")

    print("="*60)
    print(f"상품: {PRODUCT_NAME}  |  날짜: {TARGET_DATE}  |  주기: {interval_text}")
    print("종료: Ctrl+C")
    print("="*60)

    check_count = 0
    error_count = 0

    while True:
        check_count += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[확인 #{check_count}] {current_time}")

        try:
            result = check_naver_booking(URL, TARGET_DATE)

            if result is None:
                error_count += 1
                print(f"  ⚠️ 확인 실패 (누적 {error_count}회)")
                if error_count >= 5:
                    send_telegram("⚠️ 네이버 예약 봇 오류 5회 연속\nnaver_booking_screenshot.png 확인 필요")
                    error_count = 0

            elif result:
                elapsed = int((datetime.now() - start_time).total_seconds() / 60)
                message = (
                    f"<b>네이버 예약 가능!</b>\n\n"
                    f"상품: {PRODUCT_NAME}\n"
                    f"날짜: {TARGET_DATE}\n"
                    f"발견 시간: {current_time}\n"
                    f"확인 횟수: {check_count}회 / {elapsed}분 소요\n\n"
                    f'<a href="{URL}">지금 바로 예약하기</a>'
                )
                send_telegram(message)
                try:
                    for _ in range(5):
                        os.system('afplay /System/Library/Sounds/Glass.aiff')
                        time.sleep(0.5)
                    os.system(f'say "네이버 예약 {TARGET_DATE} 가능합니다"')
                except Exception:
                    pass
                print(f"\n✅ 예약 가능! 프로그램 종료")
                break

            else:
                error_count = 0
                print(f"  ❌ 아직 예약 불가")

        except Exception as e:
            print(f"  ⚠️ 예외: {e}")
            time.sleep(10)
            continue

        if check_count % 30 == 0:
            elapsed = int((datetime.now() - start_time).total_seconds() / 60)
            send_telegram(f"모니터링 중...\n\n확인: {check_count}회\n경과: {elapsed}분\n상태: 아직 예약 불가")

        print(f"  다음 확인: {CHECK_INTERVAL}초 후")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":

    # === 설정 ===
    URL          = "https://booking.naver.com/booking/13/bizes/222456/items/3048840?startDate=2026-07-10"
    PRODUCT_NAME = "네이버 예약"
    TARGET_DATE  = "2026-07-10"
    CHECK_INTERVAL = 60  # 로컬 루프 실행 시 간격 (초)
    # ============

    # GitHub Actions 환경(CI=true)이면 1회 실행, 아니면 로컬 루프
    if os.environ.get("CI"):
        run_once()
    else:
        run_loop()
