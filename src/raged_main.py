# -*- coding: utf-8 -*-
import os
import io
import re
from dotenv import load_dotenv
import pickle
import time
from google import genai
from google.genai import types
# --- Gemini 및 LangChain 모듈 ---
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.storage import InMemoryStore
from langchain.retrievers import ParentDocumentRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
# --- 기존 유틸리티 모듈 ---
from gtts import gTTS
from PIL import Image
import argparse  # argparse 모듈 추가

# .env 로드 및 API 키 설정
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "YOUR_API_KEY_HERE":
    raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았거나 유효하지 않습니다.")

# --- 1. 고급 RAG 검색기(Retriever) 로드 및 실행 ---
def get_context_with_parent_retriever(user_question: str) -> str:
    """
    ParentDocumentRetriever를 사용하여, 작은 조각으로 검색하고
    연결된 큰 부모 조각(전체 문맥)을 반환합니다.
    """
    print(f"\n'{user_question}'에 대한 참고 자료 검색 중... (Parent Document Retriever)")
    try:
        # DB 구축 시 사용했던 설정과 동일하게 로드
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
        
        # 1. 벡터 저장소(자식 조각) 로드
        vectorstore = Chroma(
            collection_name="split_parents", 
            embedding_function=embeddings,
            persist_directory="db/chroma_db"
        )
        
        # 2. 문서 저장소(부모 조각) 로드
        with open("db/docstore/docstore.pkl", "rb") as f:
            store = pickle.load(f)

        child_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

        # 3. Retriever 재구성
        retriever = ParentDocumentRetriever(
            vectorstore=vectorstore,
            docstore=store,
            child_splitter=child_splitter, # 로드 시에는 splitter가 필요 없음
            #search_type="mmr",  # <--- 이 부분을 추가합니다!
            search_kwargs={'k': 1}

        )

        # 4. 질문에 해당하는 '부모' 문서 검색
        retrieved_docs = retriever.invoke(user_question)
        
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        return context

    except Exception as e:
        raise RuntimeError(f"문서 검색 중 오류 발생: {e}. setup_advanced_rag_db.py를 먼저 실행했는지 확인해주세요.")


# --- 2. 스토리라인 생성 (기존 main.py의 함수와 100% 동일) ---
def generate_storyline(client, user_question, context):
    print(f"\n스토리라인 생성 중... (기존 Gemini API 호출 방식 사용)")
    prompt = f"""
    당신은 금융 지식을 이해하기 쉽게 동화로 각색하는 전문 동화 작가입니다.
    아래 '참고 자료'를 바탕으로, '사용자 질문'에 대한 동화 시나리오를 만들어주세요.

    --- 참고 자료 ---
    {context}
    -----------------

    사용자 질문: {user_question}

    시나리오 시작 부분에 '등장인물:' 섹션을 만들고 주인공 이름과 특징을 명시해주세요.
    그 다음 '---' 구분선을 넣고, 7개의 장면으로 구성된 동화 시나리오를 만들어주세요.
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

# --- 이하 코드는 기존 main.py와 동일 ---
def parse_storyline(storyline_text):
    """스토리라인 텍스트에서 등장인물 설명과 장면들을 분리합니다."""
    try:
        parts = re.split(r'\n---\n', storyline_text, 1)
        if len(parts) == 2:
            character_part = parts[0]
            scene_part = parts[1]
            character_description = character_part.replace("등장인물:", "").strip()
            return character_description, scene_part
        else:
            return None, storyline_text
    except Exception as e:
        print(f"오류: 스토리라인 파싱 중 오류 발생: {e}")
        return None, storyline_text
    
def generate_illustrations(client, scenes_text, character_description):
    """표지 이미지를 생성하고, 이를 참조하여 각 장면의 일러스트를 생성합니다."""
    print("\n일러스트 생성 중... (Gemini Image Preview API 호출)")

    if not character_description:
        print("  - 등장인물 정보가 없어 일러스트 생성을 건너<binary data, 2 bytes, 1 bytes>니다.")
        return

    # 1. 표지 이미지 생성
    cover_image = None
    print("  - 동화책 표지 이미지 생성 중...")
    cover_prompt = f"""
    Create a cover illustration for a children's storybook with a sci-fi vibe and style featuring all the following characters in a cute and heartwarming style, without any text, captions, or speech balloons.

    Characters:
    {character_description}
    """
    for attempt in range(3):
        try:
            generate_content_config = types.GenerateContentConfig(response_modalities=["IMAGE"])
            response = client.models.generate_content(
                model="gemini-2.5-flash-image-preview",
                contents=[cover_prompt],
                config=generate_content_config,
            )
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        img_data = part.inline_data.data
                        cover_image = Image.open(io.BytesIO(img_data))
                        cover_image.save("output/cover_image.png")
                        print("  - 표지 이미지 생성 성공!")
                        break
            if cover_image:
                break
            else:
                print(f"  - 표지 이미지 생성 실패 (시도 {attempt + 1}/3). 재시도합니다.")
                time.sleep(5)
        except Exception as e:
            print(f"  - 표지 이미지 생성 중 오류 발생 (시도 {attempt + 1}/3): {e}")
            time.sleep(5)

    if not cover_image:
        print("  - 최종적으로 표지 이미지 생성에 실패하여 일러스트 생성을 중단합니다.")
        return

    # 2. 장면별 일러스트 생성
    scenes = [s.strip() for s in scenes_text.strip().split('장면') if s and ':' in s]

    for i, scene_text in enumerate(scenes):
        scene_number = i + 1
        print(f"  - 장면 {scene_number} 이미지 생성 중...")

        clean_text = scene_text.split(":", 1)[1].strip() if ":" in scene_text else scene_text
        clean_text = clean_text.replace('**', '')

        scene_prompt = f"""
        Reference the characters and art style from the provided cover image.
        
        Characters for reference:
        {character_description}

        Now, draw the following scene without any text, captions, or speech balloons:
        {clean_text}
        """
        contents_for_api = [cover_image, scene_prompt]

        image_generated = False
        for attempt in range(3):
            try:
                generate_content_config = types.GenerateContentConfig(response_modalities=["IMAGE"])
                response = client.models.generate_content(
                    model="gemini-2.5-flash-image-preview",
                    contents=contents_for_api,
                    config=generate_content_config,
                )
                if response.candidates:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            img = Image.open(io.BytesIO(part.inline_data.data))
                            img.save(f"output/scene_{scene_number}_image.png")
                            image_generated = True
                            break
                if image_generated:
                    break
                else:
                    print(f"  - 장면 {scene_number} 이미지 생성 실패 (시도 {attempt + 1}/3). 재시도합니다.")
                    time.sleep(5)
            except Exception as e:
                print(f"  - 장면 {scene_number} 이미지 생성 중 오류 발생 (시도 {attempt + 1}/3): {e}")
                time.sleep(5)

        if not image_generated:
            print(f"  - 장면 {scene_number} 이미지 생성에 최종적으로 실패했습니다.")
            with open(f"output/scene_{scene_number}_error.txt", "w", encoding="utf-8") as f:
                f.write("최대 재시도 횟수 초과")

    print("\n'output' 폴더에 일러스트 파일 생성이 완료되었습니다.")

def generate_voice_and_subtitles(scenes_text):
    """gTTS를 사용하여 음성 파일을 생성하고, 자막 파일을 만듭니다."""
    print("\n음성 및 자막 생성 중...")
    
    scenes = [s.strip() for s in scenes_text.strip().split('장면') if s and ':' in s]
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
    parser = argparse.ArgumentParser(description="RAG를 사용하여 질문에 대한 동화를 생성합니다.")
    parser.add_argument("--question", type=str, required=True, help="동화로 만들고 싶은 질문")
    args = parser.parse_args()

    client = genai.Client(api_key=api_key)

    user_question = args.question # 하드코딩된 값을 인자로 대체
    
    print(f"--- 고급 RAG 프로세스 시작 ---")
    print(f"사용자 질문: {user_question}")

    # 1. (고급 RAG) ParentDocumentRetriever로 문맥이 풍부한 내용 검색
    context = get_context_with_parent_retriever(user_question)
    
    if not context:
        print("오류: 질문과 관련된 참고 자료를 찾을 수 없습니다.")
        return

    print("\n--- 검색된 참고 자료 (전체 문맥) ---")
    print(context)
    print("------------------------------------")
        
    # 2. (기존 방식) 검색된 내용을 바탕으로 스토리라인 생성
    full_storyline_text = generate_storyline(client, user_question, context)

    # ... (이하 로직은 기존과 동일) ...
    
    print("\n--- 생성된 스토리라인 ---")
    print(full_storyline_text)
    print("--------------------------")

    character_description, scenes_text = parse_storyline(full_storyline_text)

    generate_illustrations(client, scenes_text, character_description)
    
    generate_voice_and_subtitles(scenes_text)

    print("\n--- 모든 프로세스 완료 ---")
    print("'output' 폴더에서 결과물을 확인하세요.")


if __name__ == "__main__":
    main()