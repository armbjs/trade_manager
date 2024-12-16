import sys
import os

# 상위 디렉토리를 sys.path에 추가하여 configs.py를 import할 수 있게 합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trade_manager import configs

def main():
    # configs.py에서 정의된 환경 변수 사용 예시
    print(f"Current timezone: {configs.TIMEZONE}")
    
    # 여기에 메인 로직을 추가하세요
    print("trade_manager is running...")

if __name__ == "__main__":
    main()