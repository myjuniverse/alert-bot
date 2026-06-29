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
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7751593135:AAFcb-bjt6SgLJgLFoas65Vhs7NaR67BEHY")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "7950312215")
# ===================

# === 모니터링 대상 ===
# time_after: "17:00" 이면 17시 이후 슬롯만 체크, None 이면 시간 무관
TARGETS = [
    {"date": "2026-07-23", "time_after": None, "label": "7/23 테스트"},  # 임시 테스트용
    {"date": "2026-07-05", "time_after": "17:00", "label": "7/5(일) 17시 이후"},
    {"date": "2026-07-10", "time_after": None,    "label": "7/10(금) 전체"},
    {"date": "2026-07-12", "time_after": "17:00", "label": "7/12(일) 17시 이후"},
]
BASE_URL = "https://booking.naver.com/booking/13/bizes/222456/items/3048840?startDate=2026-07-05"
CHECK_INTERVAL = 60  # 로컬 루프 실행 시 간격 (초)
# ====================


def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        })
        if response.status_code == 200:
            print("  ✅ 텔레그램 알림 전송")
        else:
            print(f"  ❌ 텔레그램 실패: {response.text}")
    except Exception as e:
        print(f"  텔레그램 오류: {e}")


def to_minutes(time_str, is_pm):
    """'5:00' + is_pm=True → 17*60+0 = 1020 (분 단위 24시간)"""
    h, m = map(int, time_str.split(":"))
    if is_pm and h != 12:
        h += 12
    elif not is_pm and h == 12:
        h = 0
    return h * 60 + m


def check_time_slots(driver, time_after):
    """
    현재 선택된 날짜의 시간 슬롯 확인.
    time_after: "17:00" 이면 17시 이후만, None 이면 아무 시간이나 가능하면 True
    """
    limit = None
    if time_after:
        h, m = map(int, time_after.split(":"))
        limit = h * 60 + m

    try:
        slot_div = driver.find_element(By.CSS_SELECTOR, ".calendar_time_slot")
    except Exception:
        print("    시간 슬롯 영역 없음")
        return False

    # time_title(오전/오후)과 time_list를 순서대로 처리
    children = slot_div.find_elements(By.XPATH, "./*")
    is_pm = False
    available = []

    for child in children:
        cls = child.get_attribute("class") or ""
        if "time_title" in cls:
            is_pm = "오후" in child.text
        elif "time_list" in cls:
            for btn in child.find_elements(By.CSS_SELECTOR, "button.btn_time"):
                if btn.get_attribute("disabled") or "unselectable" in (btn.get_attribute("class") or ""):
                    continue
                t_str = btn.text.strip()
                t_min = to_minutes(t_str, is_pm)
                if limit is None or t_min >= limit:
                    h24, m24 = divmod(t_min, 60)
                    available.append(f"{h24:02d}:{m24:02d}")

    if available:
        print(f"    예약 가능 시간: {', '.join(available)}")
        return True

    print(f"    조건에 맞는 예약 가능 시간 없음")
    return False


def check_all_targets():
    """
    모든 대상 날짜/시간 확인.
    반환: 예약 가능한 target dict 리스트
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,900')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    found = []

    try:
        print(f"  페이지 로드 중...")
        driver.get(BASE_URL)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.calendar_date"))
            )
        except Exception:
            pass
        time.sleep(3)

        # 전체 페이지 스크린샷
        page_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1280, max(page_height, 900))
        time.sleep(1)
        driver.save_screenshot("naver_booking_screenshot.png")

        for target in TARGETS:
            date      = target["date"]
            time_after = target["time_after"]
            label     = target["label"]
            day_num   = str(int(date.split("-")[2]))

            print(f"\n  [{label}] 확인 중...")

            # 날짜 버튼 찾기 (span.num 텍스트로 식별)
            date_buttons = driver.find_elements(By.CSS_SELECTOR, "button.calendar_date")
            target_btn = None
            for btn in date_buttons:
                try:
                    if btn.find_element(By.CSS_SELECTOR, "span.num").text.strip() == day_num:
                        target_btn = btn
                        break
                except Exception:
                    continue

            if target_btn is None:
                print(f"    {day_num}일 버튼을 찾지 못함")
                continue

            cls        = target_btn.get_attribute("class") or ""
            is_disabled = target_btn.get_attribute("disabled") is not None
            print(f"    class='{cls}'")

            if "closed" in cls or "unselectable" in cls or is_disabled:
                print(f"    ❌ 예약 불가 (마감 또는 휴무)")
                continue

            # 날짜 활성 → 클릭해서 시간 슬롯 로드
            print(f"    날짜 활성화됨 → 시간 슬롯 확인")
            driver.execute_script("arguments[0].click();", target_btn)
            time.sleep(2)

            if time_after is None:
                print(f"    ✅ 예약 가능! (시간 무관)")
                found.append(target)
            elif check_time_slots(driver, time_after):
                print(f"    ✅ {time_after} 이후 예약 가능!")
                found.append(target)
            else:
                print(f"    ❌ {time_after} 이후 예약 가능 시간 없음")

    except Exception as e:
        print(f"  오류: {e}")
    finally:
        driver.quit()

    return found


def signal_handler(sig, frame):
    print('\n\n' + '='*60)
    print('프로그램을 수동으로 종료합니다.')
    send_telegram("네이버 예약 모니터링을 수동으로 종료했습니다.")
    sys.exit(0)


def run_once():
    """한 번만 확인하고 종료 (GitHub Actions용)"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{current_time}] 확인 중...")

    found = check_all_targets()

    if found:
        labels = "\n".join([f"  • {t['label']}" for t in found])
        send_telegram(
            f"<b>네이버 예약 가능!</b>\n\n"
            f"{labels}\n\n"
            f"⏰ {current_time}\n"
            f'<a href="{BASE_URL}">지금 바로 예약하기</a>'
        )
        print("✅ 예약 가능 → 텔레그램 알림 전송")
    else:
        print("❌ 조건에 맞는 예약 가능 슬롯 없음")


def run_loop():
    """무한 루프로 반복 확인 (로컬 실행용)"""
    signal.signal(signal.SIGINT, signal_handler)
    start_time = datetime.now()
    labels_str = ", ".join([t["label"] for t in TARGETS])

    send_telegram(
        f"네이버 예약 모니터링 시작!\n\n"
        f"대상: {labels_str}\n"
        f"확인 주기: {CHECK_INTERVAL}초\n\n"
        f"예약 가능해지면 바로 알려드립니다."
    )

    print("="*60)
    print(f"모니터링 대상: {labels_str}")
    print(f"확인 주기: {CHECK_INTERVAL}초  |  종료: Ctrl+C")
    print("="*60)

    check_count = 0

    while True:
        check_count += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[확인 #{check_count}] {current_time}")

        try:
            found = check_all_targets()

            if found:
                elapsed = int((datetime.now() - start_time).total_seconds() / 60)
                labels_found = "\n".join([f"  • {t['label']}" for t in found])
                send_telegram(
                    f"<b>네이버 예약 가능!</b>\n\n"
                    f"{labels_found}\n\n"
                    f"⏰ {current_time} / {check_count}회 / {elapsed}분 소요\n"
                    f'<a href="{BASE_URL}">지금 바로 예약하기</a>'
                )
                try:
                    for _ in range(5):
                        os.system('afplay /System/Library/Sounds/Glass.aiff')
                        time.sleep(0.5)
                    os.system('say "네이버 예약 가능합니다"')
                except Exception:
                    pass
                print("✅ 예약 가능! 프로그램 종료")
                break

        except Exception as e:
            print(f"  ⚠️ 예외: {e}")
            time.sleep(10)
            continue

        if check_count % 30 == 0:
            elapsed = int((datetime.now() - start_time).total_seconds() / 60)
            send_telegram(f"모니터링 중...\n\n확인: {check_count}회\n경과: {elapsed}분\n상태: 아직 없음")

        print(f"  다음 확인: {CHECK_INTERVAL}초 후")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    if os.environ.get("CI"):
        run_once()
    else:
        run_loop()
