import os
from dotenv import load_dotenv

# LangChain 관련 모듈 임포트
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# .env 파일에서 환경 변수 로드
load_dotenv()

# API 키 유효성 검사
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "YOUR_API_KEY_HERE":
    raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았거나 유효하지 않습니다.")

CORPUS_PATH = "corpus/"
DB_FAISS_PATH = "db/faiss_index"

def main():
    """corpus 폴더의 문서를 로드, 분할, 임베딩하여 FAISS 벡터 저장소에 저장합니다."""
    
    # 1. 문서 로드 (Load)
    print(f"'{CORPUS_PATH}'에서 문서 로딩 중...")
    loader = DirectoryLoader(CORPUS_PATH, glob='*.txt', loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    documents = loader.load()
    if not documents:
        print("오류: corpus 폴더에 문서가 없습니다.")
        return
    print(f"총 {len(documents)}개의 문서를 로드했습니다.")

    # 2. 문서 분할 (Split)
    print("문서를 청크(Chunk) 단위로 분할 중...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)
    print(f"총 {len(docs)}개의 청크로 분할되었습니다.")

    # 3. 임베딩 및 벡터 저장소 생성 (Store)
    print("Google 임베딩 모델을 사용하여 문서를 임베딩하고 FAISS 벡터 저장소를 생성합니다...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
    
    # FAISS 벡터 저장소 생성 및 저장
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(DB_FAISS_PATH)
    
    print(f"\n벡터 데이터베이스 생성이 완료되었습니다.")
    print(f"'{DB_FAISS_PATH}' 폴더에 인덱스 파일이 저장되었습니다.")

if __name__ == "__main__":
    os.makedirs("db", exist_ok=True)
    main()