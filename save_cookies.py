from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import pickle

def save_yanolja_cookies():
    """야놀자 로그인 후 쿠키 저장"""
    
    options = webdriver.ChromeOptions()
    # 브라우저 보면서 수동 로그인
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    try:
        print("="*60)
        print("야놀자 쿠키 저장")
        print("="*60)
        print("\n1. 브라우저가 열립니다")
        print("2. 카카오(또는 원하는 방법)로 로그인하세요")
        print("3. 로그인 완료되면 아무 페이지나 이동해보세요")
        print("4. 로그인 확인되면 엔터를 누르세요\n")
        
        # 야놀자 페이지 열기
        driver.get("https://www.yanolja.com")
        time.sleep(3)
        
        input("로그인 완료 후 엔터를 누르세요... ")
        
        # 쿠키 저장
        cookies = driver.get_cookies()
        with open('yanolja_cookies.pkl', 'wb') as f:
            pickle.dump(cookies, f)
        
        print("\n✅ 쿠키 저장 완료: yanolja_cookies.pkl")
        print("이제 yanolja_stock_bot.py를 실행하세요!\n")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    save_yanolja_cookies()