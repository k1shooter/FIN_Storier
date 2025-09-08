# -*- coding: utf-8 -*-

import sqlite3
import os
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
from PIL import Image
import io
import time

# .env 파일에서 환경 변수 로드
load_dotenv()

# Gemini API 키 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "YOUR_API_KEY_HERE":
    raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았거나 유효하지 않습니다. .env 파일을 확인해주세요.")
genai.configure(api_key=api_key)


# --- 1. 데이터베이스 연결 및 정보 검색 ---
def get_product_description(product_name):
    """데이터베이스에서 금융 상품의 설명을 가져옵니다."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    db_path = os.path.join(project_root, 'db', 'financial_products.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT description FROM products WHERE name = ?", (product_name,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return None

# --- 2. 첫 번째 프롬프팅: 스토리라인 생성 ---
def generate_storyline(product_name, description):
    """Gemini를 사용하여 동화 스토리라인을 생성합니다."""
    print(f"\n'{product_name}'에 대한 스토리라인 생성 중... (Gemini API 호출)")
    
    # 텍스트 생성은 flash 모델을 사용
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    prompt = f"""
    당신은 금융 지식을 아이들이 이해하기 쉽게 동화로 각색하는 전문 동화 작가입니다.

    금융 개념: {product_name}
    핵심 설명: {description}

    위 금융 개념의 핵심 원리를 바탕으로, 5개의 장면으로 구성된 짧고 교훈적인 동화 시나리오를 만들어주세요.
    각 장면은 '장면 1:', '장면 2:' 와 같이 번호와 콜론으로 시작해야 합니다.
    이야기는 희망차고 긍정적인 분위기로 만들어주세요.
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace('`', '')
        return clean_text
    except Exception as e:
        print(f"오류: 스토리라인 생성 중 API 호출 실패: {e}")
        return None

# --- 3. 두 번째 프롬프팅: 일러스트 생성 (진짜 최종 수정) ---
def generate_illustrations(storyline):
    """이미지 생성 전용 모델을 사용하여 동화 일러스트를 생성합니다."""
    print("\n일러스트 생성 중... (이미지 생성 전용 모델 API 호출)")
    
    # [최종 수정] 사용자님이 제공해주신 목록에 있는 "이미지 생성 전용 모델"로 변경
    image_model = genai.GenerativeModel('models/gemini-2.5-flash-image-preview')

    scenes = [s.strip() for s in storyline.strip().split('장면') if s and ':' in s]
    if not scenes:
        print("  - 스토리라인에서 장면을 추출할 수 없습니다.")
        return

    for i, scene_text in enumerate(scenes):
        scene_number = i + 1
        print(f"  - 장면 {scene_number} 이미지 생성 중...")
        
        # 이미지 생성 모델을 위한 간단하고 명확한 프롬프트
        image_prompt = f"A cute and heartwarming children's storybook illustration of the following scene: {scene_text}"
        
        try:
            # 이미지 생성 요청
            response = image_model.generate_content(image_prompt)
            
            # 응답에 이미지 데이터(blob)가 있는지 확인
            if hasattr(response, 'parts') and response.parts and hasattr(response.parts[0], 'blob'):
                img_data = response.parts[0].blob.data
                img = Image.open(io.BytesIO(img_data))
                img.save(f"output/scene_{scene_number}_image.png")
            else:
                # 텍스트 응답이 올 경우의 에러 처리
                error_message = response.text if hasattr(response, 'text') else "알 수 없는 응답 포맷"
                print(f"  - 장면 {scene_number} 이미지 생성 실패. 모델이 텍스트를 반환했습니다:")
                print(f"    모델 응답: {error_message}")
                with open(f"output/scene_{scene_number}_error.txt", "w", encoding="utf-8") as f:
                    f.write(f"모델 응답:\n{error_message}")

        except Exception as e:
            print(f"  - 장면 {scene_number} 이미지 생성 중 오류 발생: {e}")
            with open(f"output/scene_{scene_number}_error.txt", "w", encoding="utf-8") as f:
                f.write(f"API 호출 오류:\n{e}")
        
        # API의 분당 요청 제한(RPM)을 피하기 위해 잠시 대기
        time.sleep(2)

    print("\n'output' 폴더에 일러스트 파일 생성이 완료되었습니다.")


# --- 4. 음성 및 자막 생성 ---
def generate_voice_and_subtitles(storyline):
    """gTTS를 사용하여 음성 파일을 생성하고, 자막 파일을 만듭니다."""
    print("\n음성 및 자막 생성 중...")
    scenes = [s.strip() for s in storyline.strip().split('장면') if s and ':' in s]
    if not scenes:
        print("  - 스토리라인에서 장면을 추출할 수 없습니다.")
        return

    for i, scene_text in enumerate(scenes):
        scene_number = i + 1
        clean_text = scene_text.split(":", 1)[1].strip() if ":" in scene_text else scene_text
        
        print(f"  - 장면 {scene_number} 음성/자막 생성 중...")
        
        try:
            tts = gTTS(text=clean_text, lang='ko')
            tts.save(f"output/scene_{scene_number}_audio.mp3")
        except Exception as e:
            print(f"  - 장면 {scene_number} 음성 생성 중 오류 발생: {e}")
            with open(f"output/scene_{scene_number}_audio_placeholder.txt", "w", encoding="utf-8") as f:
                f.write(f"음성 생성 오류: {clean_text}")

        with open(f"output/scene_{scene_number}_subtitle.txt", "w", encoding="utf-8") as f:
            f.write(clean_text)
            
    print("\n'output' 폴더에 음성 및 자막 파일이 생성되었습니다.")


# --- 메인 실행 로직 ---
def main():
    """프로그램의 메인 로직을 실행합니다."""
    product_to_explain = "복리" 
    print(f"--- '{product_to_explain}' 설명 프로세스 시작 ---")

    description = get_product_description(product_to_explain)
    if not description:
        print(f"오류: '{product_to_explain}'에 대한 정보를 DB에서 찾을 수 없습니다.")
        return

    storyline = generate_storyline(product_to_explain, description)
    if not storyline:
        print("\n스토리라인 생성에 실패하여 프로세스를 중단합니다.")
        return
        
    print("\n--- 생성된 스토리라인 ---")
    print(storyline)
    print("--------------------------")

    generate_illustrations(storyline)
    generate_voice_and_subtitles(storyline)

    print("\n--- 모든 프로세스 완료 ---")
    print("'output' 폴더에서 결과물을 확인하세요.")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    main()