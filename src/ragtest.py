# --- RAG(문서 검색)를 위해 LangChain 모듈 추가 ---
# -*- coding: utf-8 -*-
import os
import io
import re
from dotenv import load_dotenv
import pickle

# --- Gemini 및 LangChain 모듈 ---
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.storage import InMemoryStore
from langchain.retrievers import ParentDocumentRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter # <- 이 부분을 추가합니다.

# --- 기존 유틸리티 모듈 ---
from gtts import gTTS
from PIL import Image

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
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
    
print(get_context_with_parent_retriever("가장 수익률이 좋은 예금 상품 골라서 정보 줘"))