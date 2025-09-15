# -*- coding: utf-8 -*-

import sqlite3
import os
import io
import time
from dotenv import load_dotenv

from google import genai
from google.genai import types

from gtts import gTTS
from PIL import Image

# .env 파일에서 환경 변수 로드
load_dotenv()

# Gemini API 키 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "YOUR_API_KEY_HERE":
    raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았거나 유효하지 않습니다. .env 파일을 확인해주세요.")

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
def generate_storyline(client, product_name, description):
    """Gemini를 사용하여 동화 스토리라인을 생성합니다."""
    print(f"\n'{product_name}'에 대한 스토리라인 생성 중... (Gemini API 호출)")

    prompt = f"""
    당신은 금융 지식을 아이들이 이해하기 쉽게 동화로 각색하는 전문 동화 작가입니다.

    금융 개념: {product_name}
    핵심 설명: {description}

    위 금융 개념의 핵심 원리를 바탕으로, '갈색 털에 동그란 눈을 가진 아기 다람쥐'가 주인공인 5개의 장면으로 구성된 짧고 교훈적인 동화 시나리오를 만들어주세요.
    각 장면은 '장면 1:', '장면 2:' 와 같이 번호와 콜론으로 시작해야 합니다.
    이야기는 희망차고 긍정적인 분위기로 만들어주세요.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[prompt]
        )
        clean_text = response.text.replace('`', '')
        return clean_text
    except Exception as e:
        print(f"오류: 스토리라인 생성 중 API 호출 실패: {e}")
        return None

# --- 3. 두 번째 프롬프팅: 일러스트 생성 (안정적인 Imagen 모델 사용) ---
def generate_illustrations(client, storyline):
    """안정적인 Imagen 모델을 사용하여 동화 일러스트를 생성합니다."""
    print("\n일러스트 생성 중... (Imagen API 호출)")

    scenes = [s.strip() for s in storyline.strip().split('장면') if s and ':' in s]
    if not scenes:
        print("  - 스토리라인에서 장면을 추출할 수 없습니다.")
        return

    for i, scene_text in enumerate(scenes):
        scene_number = i + 1
        print(f"  - 장면 {scene_number} 이미지 생성 중...")

        clean_text = scene_text.split(":", 1)[1].strip() if ":" in scene_text else scene_text
        clean_text = clean_text.replace('**', '')

        # [수정] 캐릭터 일관성을 위해 주인공 외모를 프롬프트에 명시
        image_prompt = f"A cute and heartwarming children's storybook illustration of the following scene without any captions or speech balloons. The main character is a baby squirrel with brown fur and round eyes: {clean_text}"

        image_generated = False
        for attempt in range(3):
            try:
                # [수정] 안정적인 Imagen 모델 호출
                result = client.models.generate_images(
                    model="models/imagen-3.0-generate-002",
                    prompt=image_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/png",
                        #person_generation=types.PersonGeneration.ALLOW_ALL,
                        aspect_ratio="1:1",
                    ),
                )

                if result.generated_images:
                    for generated_image in result.generated_images:
                        img = Image.open(io.BytesIO(generated_image.image.image_bytes))
                        img.save(f"output/scene_{scene_number}_image.png")
                        image_generated = True
                        break
                
                if image_generated:
                    break
                else:
                    print(f"  - 장면 {scene_number} 이미지 생성 실패 (시도 {attempt + 1}/3). 모델이 이미지를 반환하지 않았습니다. 재시도합니다.")
                    time.sleep(5)

            except Exception as e:
                print(f"  - 장면 {scene_number} 이미지 생성 중 오류 발생 (시도 {attempt + 1}/3): {e}")
                time.sleep(5)

        if not image_generated:
            error_message = "최대 재시도 횟수(3회)를 초과하였으나 이미지 생성에 실패했습니다."
            print(f"  - {error_message}")
            with open(f"output/scene_{scene_number}_error.txt", "w", encoding="utf-8") as f:
                f.write(error_message)

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
        clean_text = clean_text.replace('**', '')

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
    
    client = genai.Client(api_key=api_key)

    product_to_explain = "펀드"
    print(f"--- '{product_to_explain}' 설명 프로세스 시작 ---")

    description = get_product_description(product_to_explain)
    if not description:
        print(f"오류: '{product_to_explain}'에 대한 정보를 DB에서 찾을 수 없습니다.")
        return

    storyline = generate_storyline(client, product_to_explain, description)
    if not storyline:
        print("\n스토리라인 생성에 실패하여 프로세스를 중단합니다.")
        return

    print("\n--- 생성된 스토리라인 ---")
    print(storyline)
    print("--------------------------")

    generate_illustrations(client, storyline)
    generate_voice_and_subtitles(storyline)

    print("\n--- 모든 프로세스 완료 ---")
    print("'output' 폴더에서 결과물을 확인하세요.")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    main()