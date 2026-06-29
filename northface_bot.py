from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
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
        else:
            print(f"  ❌ 텔레그램 실패: {response.text}")
    except Exception as e:
        print(f"  텔레그램 오류: {e}")

def check_northface_stock(url, target_size):
    """노스페이스 재고 확인"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".product-option_radio label")))
        time.sleep(3)
        
        size_labels = driver.find_elements(By.CSS_SELECTOR, ".product-option_radio label")
        
        for label in size_labels:
            label_text = label.text.strip()
            
            if target_size in label_text and label_text != '':
                try:
                    input_elem = label.find_element(By.TAG_NAME, "input")
                    is_disabled = input_elem.get_attribute("disabled")
                    
                    print(f"  [{label_text}] disabled: {is_disabled}")
                    
                    if is_disabled is None:
                        print(f"  ✅ 재고 발견! {label_text}")
                        return True
                    else:
                        print(f"  ❌ 품절: {label_text}")
                        return False
                        
                except Exception as e:
                    print(f"  input 찾기 실패: {e}")
                    continue
        
        print(f"  ⚠️ 사이즈 {target_size}를 찾을 수 없음")
        return False
        
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
    send_telegram("재고 모니터링을 수동으로 종료했습니다.")
    sys.exit(0)

if __name__ == "__main__":
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # === 상품 설정 ===
    PRODUCTS = [
        {
            "name": "노스페이스 벤투스 온 자켓 (블랙)",
            "url": "https://www.thenorthfacekorea.co.kr/product/NJ3NR56J",
            "target": "092(WL)",
        },
        {
            "name": "노스페이스 벤투스 온 자켓 (카키)",
            "url": "https://www.thenorthfacekorea.co.kr/product/NJ3NR56L",
            "target": "092(WL)",
        },
        {
            "name": "노스페이스 벤투스 온 자켓 (실버)",
            "url": "https://www.thenorthfacekorea.co.kr/product/NJ3NR56K",
            "target": "092(WL)",
        },
    ]
    
    check_interval = 30  # 30초
    # ==================
    
    start_time = datetime.now()
    
    if check_interval >= 60:
        interval_text = f"{check_interval}초 ({check_interval//60}분)마다"
    else:
        interval_text = f"{check_interval}초마다"
    
    # 시작 알림
    product_list = "\n".join([f"  • {p['name']}" for p in PRODUCTS])
    send_telegram(f"""재고 모니터링 시작!

상품 목록 ({len(PRODUCTS)}개):
{product_list}

사이즈: 092(WL)
확인 주기: {interval_text}

재고 입고되면 바로 알려드립니다.""")
    
    print("="*60)
    print("노스페이스 재고 모니터링 시작")
    print("="*60)
    print(f"모니터링 상품: {len(PRODUCTS)}개")
    for p in PRODUCTS:
        print(f"  - {p['name']}")
    print(f"사이즈: 092(WL)")
    print(f"확인 주기: {interval_text}")
    print(f"종료: Ctrl+C")
    print("="*60)
    print()
    
    check_count = 0
    
    # === 무한 반복 ===
    while True:
        check_count += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n[확인 #{check_count}] {current_time}")
        print("="*60)
        
        found_items = []
        
        # 모든 상품 확인
        for product in PRODUCTS:
            print(f"\n{product['name']} 확인 중...")
            
            try:
                stock_available = check_northface_stock(
                    product["url"],
                    product["target"]
                )
                
                if stock_available:
                    found_items.append(product)
                    
            except Exception as e:
                print(f"  ⚠️ 확인 중 오류: {e}")
                print("  10초 후 다음 상품 확인...")
                time.sleep(10)
                continue
        
        # === 재고 발견 처리 ===
        if found_items:
            elapsed_time = int((datetime.now() - start_time).total_seconds() / 60)
            
            for item in found_items:
                message = f"""
<b>재고 입고 알림!</b>

상품: {item['name']}
사이즈: {item['target']}
발견 시간: {current_time}
확인 횟수: {check_count}회
소요 시간: {elapsed_time}분

<a href="{item['url']}">지금 바로 구매하기</a>
                """
                send_telegram(message)
            
            # 소리 알림
            try:
                import os
                for _ in range(5):
                    os.system('afplay /System/Library/Sounds/Glass.aiff')
                    time.sleep(0.5)
                os.system('say "재고가 입고되었습니다"')
            except:
                pass
            
            print("\n" + "="*60)
            print(f"재고 발견! {len(found_items)}개 상품")
            for item in found_items:
                print(f"  - {item['name']}")
            print(f"총 {check_count}회 확인 / {elapsed_time}분 소요")
            print("="*60)
            break
        
        # 30번마다 상태 알림 (3분 × 30 = 90분마다)
        if check_count % 50 == 0:
            elapsed_time = int((datetime.now() - start_time).total_seconds() / 60)
            send_telegram(f"""모니터링 중...

확인 횟수: {check_count}회
경과 시간: {elapsed_time}분
상태: 아직 재고 없음""")
        
        print(f"\n다음 확인: {check_interval}초 후")
        print("="*60)
        time.sleep(check_interval)