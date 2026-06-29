from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import pickle
import os
from datetime import datetime
import requests
import signal
import sys

# === 텔레그램 설정 ===
TELEGRAM_BOT_TOKEN = "7751593135:AAFcb-bjt6SgLJgLFoas65Vhs7NaR67BEHY"
TELEGRAM_CHAT_ID = "7950312215"
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
    except Exception as e:
        print(f"  텔레그램 오류: {e}")

def load_yanolja_cookies(driver):
    """저장된 쿠키로 로그인"""
    try:
        driver.get("https://www.yanolja.com")
        time.sleep(2)
        
        if not os.path.exists('yanolja_cookies.pkl'):
            print("  ❌ 쿠키 파일 없음")
            return False
        
        with open('yanolja_cookies.pkl', 'rb') as f:
            cookies = pickle.load(f)
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except:
                pass
        
        print("  ✅ 쿠키 로드 완료")
        time.sleep(2)
        
        return True
        
    except Exception as e:
        print(f"  ❌ 쿠키 로드 실패: {e}")
        return False

def check_yanolja_date_stock(url, target_date):
    """야놀자 특정 날짜 재고 확인"""
    
    options = webdriver.ChromeOptions()
    # headless 모드 끄기!
    # options.add_argument('--headless')  
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    try:
        # 쿠키로 로그인
        if not load_yanolja_cookies(driver):
            return None
        
        # 상품 페이지 접속
        print("  상품 페이지 접속...")
        driver.get(url)
        time.sleep(10)
        
        # 옵션 선택하기 버튼 찾기
        print("  옵션 선택하기 버튼 찾는 중...")
        
        max_attempts = 3
        option_button = None
        
        for attempt in range(max_attempts):
            buttons = driver.find_elements(By.TAG_NAME, "button")
            print(f"    시도 {attempt+1}: 버튼 {len(buttons)}개 발견")
            
            for btn in buttons:
                btn_text = btn.text.strip()
                if "옵션 선택" in btn_text:
                    option_button = btn
                    print(f"    ✅ 버튼 발견: '{btn_text}'")
                    break
            
            if option_button:
                break
            
            if attempt < max_attempts - 1:
                print(f"    버튼 없음, 3초 후 재시도...")
                time.sleep(3)
        
        if not option_button:
            print("  ❌ 옵션 선택하기 버튼을 찾을 수 없음")
            return False
        
        # 버튼 클릭
        print("  버튼 클릭...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option_button)
        time.sleep(2)
        
        try:
            option_button.click()
        except:
            driver.execute_script("arguments[0].click();", option_button)
        
        print("  ✅ 버튼 클릭 완료")
        time.sleep(5)
        
        # 로그인 모달 체크
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if "로그인 후" in body_text:
            print("  ⚠️ 로그인 모달 - 쿠키 만료")
            return None
        
        # 날짜 버튼 찾기
        print(f"  '{target_date}' 날짜 버튼 찾는 중...")
        
        all_buttons = driver.find_elements(By.TAG_NAME, "button")
        
        target_button = None
        for btn in all_buttons:
            text = btn.text.strip()
            
            if text == target_date or text == f"{target_date}일":
                target_button = btn
                break
        
        if not target_button:
            print(f"  ⚠️ '{target_date}' 버튼 없음")
            return False
        
        # disabled 상태 확인
        is_disabled = target_button.get_attribute('disabled')
        aria_disabled = target_button.get_attribute('aria-disabled')
        
        print(f"  버튼 발견: '{target_button.text.strip()}'")
        print(f"    disabled: {is_disabled}")
        
        if is_disabled == 'true' or is_disabled == True:
            print(f"  ❌ {target_date}일 선택 불가")
            return False
        
        if aria_disabled == 'true':
            print(f"  ❌ {target_date}일 선택 불가")
            return False
        
        # 활성화!
        print(f"  ✅ {target_date}일 활성화됨!")
        return True
        
    except Exception as e:
        print(f"  오류: {e}")
        return False
        
    finally:
        driver.quit()

def signal_handler(sig, frame):
    """Ctrl+C 처리"""
    print('\n\n' + '='*60)
    print('프로그램을 수동으로 종료합니다.')
    print('='*60)
    send_telegram("야놀자 재고 모니터링을 수동으로 종료했습니다.")
    sys.exit(0)

if __name__ == "__main__":
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # === 설정 ===
    url = "https://leisure-web.yanolja.com/leisure/10265844"
    product_name = "화담숲 입장권"
    target_date = "8"  # 11월 8일
    check_interval = 30  # 30초 (창이 뜨니까 좀 길게)
    # ============
    
    # 쿠키 파일 확인
    if not os.path.exists('yanolja_cookies.pkl'):
        print("="*60)
        print("⚠️ 쿠키 파일이 없습니다!")
        print("="*60)
        print("먼저 save_yanolja_cookies.py를 실행하세요.\n")
        sys.exit(1)
    
    start_time = datetime.now()
    
    if check_interval >= 60:
        interval_text = f"{check_interval}초 ({check_interval//60}분)마다"
    else:
        interval_text = f"{check_interval}초마다"
    
    # 시작 알림
    send_telegram(f"""재고 모니터링 시작!

상품: {product_name}
날짜: 11월 {target_date}일
확인 주기: {interval_text}

재고 입고되면 바로 알려드립니다.""")
    
    print("="*60)
    print("야놀자 재고 모니터링 시작 (브라우저 창 보임)")
    print("="*60)
    print(f"상품: {product_name}")
    print(f"날짜: 11월 {target_date}일")
    print(f"확인 주기: {interval_text}")
    print(f"종료: Ctrl+C")
    print("="*60)
    print()
    
    check_count = 0
    cookie_expired_count = 0
    
    # === 무한 반복 ===
    while True:
        check_count += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n[확인 #{check_count}] {current_time}")
        
        try:
            result = check_yanolja_date_stock(url, target_date)
            
            if result is None:
                cookie_expired_count += 1
                print(f"\n⚠️ 쿠키 만료 ({cookie_expired_count}회)")
                
                if cookie_expired_count >= 3:
                    send_telegram("⚠️ 쿠키 만료\nsave_yanolja_cookies.py 재실행 필요")
                    break
                
            elif result:
                # 재고 발견!
                elapsed_time = int((datetime.now() - start_time).total_seconds() / 60)
                
                message = f"""
<b>재고 입고 알림!</b>

상품: {product_name}
날짜: 11월 {target_date}일
발견 시간: {current_time}
확인 횟수: {check_count}회

<a href="{url}">지금 바로 구매하기</a>
                """
                send_telegram(message)
                
                # 소리 알림
                try:
                    import os
                    for _ in range(5):
                        os.system('afplay /System/Library/Sounds/Glass.aiff')
                        time.sleep(0.5)
                    os.system(f'say "야놀자 11월 {target_date}일 재고가 입고되었습니다"')
                except:
                    pass
                
                print("\n" + "="*60)
                print("재고 발견! 프로그램 종료")
                print("="*60)
                break
            
            else:
                cookie_expired_count = 0
                
        except Exception as e:
            print(f"⚠️ 오류: {e}")
            time.sleep(10)
            continue
        
        # 30번마다 상태 알림
        if check_count % 30 == 0:
            elapsed_time = int((datetime.now() - start_time).total_seconds() / 60)
            send_telegram(f"""모니터링 중...

확인: {check_count}회
경과: {elapsed_time}분
상태: 재고 없음""")
        
        print(f"다음 확인: {check_interval}초 후")
        time.sleep(check_interval)