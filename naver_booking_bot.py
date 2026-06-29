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

        # 페이지 끝까지 스크롤해서 달력 렌더링 유도
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # 전체 페이지 스크린샷 (스크롤 포함)
        screenshot_path = "naver_booking_screenshot.png"
        original_size = driver.get_window_size()
        page_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1280, max(page_height, 800))
        time.sleep(1)
        driver.save_screenshot(screenshot_path)
        driver.set_window_size(original_size['width'], original_size['height'])
        print(f"  스크린샷 저장 (전체 페이지, 높이={page_height}px): {screenshot_path}")

        # target_date = "2026-07-10" → day_num = "10"
        day_num = str(int(target_date.split("-")[2]))

        # 네이버 예약 달력 구조:
        #   예약 가능 → <button class="calendar_date">
        #   마감      → <button class="calendar_date closed">
        #   휴무/비영업 → <button class="calendar_date unselectable" disabled>
        # span.num 안의 텍스트로 날짜 식별

        date_buttons = driver.find_elements(By.CSS_SELECTOR, "button.calendar_date")
        print(f"  달력 버튼 {len(date_buttons)}개 발견")

        if not date_buttons:
            print("  ⚠️ 달력 버튼을 찾지 못했습니다. 스크린샷을 확인하세요.")
            return None

        target_el = None
        for btn in date_buttons:
            try:
                num_span = btn.find_element(By.CSS_SELECTOR, "span.num")
                if num_span.text.strip() == day_num:
                    target_el = btn
                    break
            except Exception:
                continue

        if target_el is None:
            print(f"  ⚠️ 달력에서 {day_num}일을 찾지 못했습니다.")
            return None

        class_attr  = target_el.get_attribute("class") or ""
        is_disabled = target_el.get_attribute("disabled") is not None
        print(f"  {day_num}일 class='{class_attr}', disabled={is_disabled}")

        # closed(마감) 또는 unselectable(휴무) 이면 예약 불가
        if "closed" in class_attr or "unselectable" in class_attr or is_disabled:
            return False

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
