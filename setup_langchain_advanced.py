import os
from dotenv import load_dotenv

# LangChain 관련 모듈 임포트
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.storage import InMemoryStore
from langchain.retrievers import ParentDocumentRetriever

# .env 파일에서 환경 변수 로드
load_dotenv()

# API 키 유효성 검사
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "YOUR_API_KEY_HERE":
    raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았거나 유효하지 않습니다.")

CORPUS_PATH = "corpus/"
DB_VECTOR_PATH = "db/chroma_db"  # 벡터 저장소 (자식 조각)
DB_DOCSTORE_PATH = "db/docstore" # 원본 문서 저장소 (부모 조각)

def main():
    """'부모-자식' 조각을 생성하여 ParentDocumentRetriever를 위한 데이터베이스를 구축합니다."""
    
    # 1. 문서 로드
    print(f"'{CORPUS_PATH}'에서 문서 로딩 중...")
    loader = DirectoryLoader(CORPUS_PATH, glob='*.txt', loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    if not docs:
        print("오류: corpus 폴더에 문서가 없습니다.")
        return
    print(f"총 {len(docs)}개의 문서를 로드했습니다.")

    # 2. 부모-자식 분할기 정의
    # 부모 분할기 (LLM에게 전달될, 문맥이 풍부한 더 큰 조각)
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    # 자식 분할기 (검색의 정확도를 높이기 위한 더 작은 조각)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    # 3. 임베딩 모델 준비
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)

    # 4. 벡터 저장소 및 문서 저장소 설정
    # 벡터 저장소: 작은 '자식' 조각들의 벡터를 저장하여 검색에 사용
    vectorstore = Chroma(
        collection_name="split_parents", 
        embedding_function=embeddings,
        persist_directory=DB_VECTOR_PATH
    )
    # 문서 저장소: 큰 '부모' 조각들의 원본 텍스트를 저장
    store = InMemoryStore()

    # 5. ParentDocumentRetriever 설정 및 데이터 추가
    retriever = ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=store,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )
    
    print("문서를 부모/자식 조각으로 분할하고 데이터베이스에 추가하는 중...")
    # add_documents를 호출하면 내부적으로 알아서 분할, 임베딩, 저장을 모두 수행
    retriever.add_documents(docs, ids=None)
    
    # Chroma DB를 디스크에 저장
    print("벡터 데이터베이스를 디스크에 저장 중...")
    vectorstore.persist()

    # InMemoryStore는 직접 파일로 저장해야 함
    import pickle
    os.makedirs(DB_DOCSTORE_PATH, exist_ok=True)
    with open(os.path.join(DB_DOCSTORE_PATH, "docstore.pkl"), "wb") as f:
        pickle.dump(store, f)

    print("\n고급 RAG 데이터베이스 생성이 완료되었습니다.")
    print(f"벡터 저장소: '{DB_VECTOR_PATH}'")
    print(f"문서 저장소: '{DB_DOCSTORE_PATH}'")


if __name__ == "__main__":
    main()