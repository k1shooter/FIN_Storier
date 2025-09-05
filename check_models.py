import google.generativeai as genai
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# API 키 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "YOUR_API_KEY_HERE":
    print("오류: GEMINI_API_KEY가 .env 파일에 설정되지 않았거나 유효하지 않습니다.")
else:
    try:
        genai.configure(api_key=api_key)
        print("사용 가능한 콘텐츠 생성 모델 목록:")
        for m in genai.list_models():
            # 'generateContent'를 지원하는 모델만 필터링
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"모델 목록을 가져오는 중 오류가 발생했습니다: {e}")
