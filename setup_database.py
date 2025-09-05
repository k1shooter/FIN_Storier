import sqlite3
import os

# db 폴더가 없으면 생성
os.makedirs("db", exist_ok=True)

# SQLite 데이터베이스에 연결 (없으면 파일 생성)
conn = sqlite3.connect('db/financial_products.db')
cursor = conn.cursor()

# 'products' 테이블 생성
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
)
''')

# 샘플 데이터
products_to_insert = [
    ('복리', '복리는 원금뿐만 아니라 이자에도 이자가 붙는 방식입니다. 시간이 지날수록 돈이 눈덩이처럼 불어나는 마법과 같아서, 장기 저축이나 투자에서 매우 중요한 원리입니다.'),
    ('주식', '주식은 회사의 소유권의 일부를 나타내는 증서입니다. 주식을 사면 그 회사의 작은 주인이 되는 것이고, 회사가 성장하면 주식의 가치도 함께 오를 수 있습니다.'),
    ('인플레이션', '인플레이션은 물가가 전반적으로 꾸준히 오르는 현상입니다. 시간이 지나면서 같은 돈으로 살 수 있는 물건의 양이 줄어드는 것을 의미합니다. 예를 들어, 어제 1000원이었던 과자가 오늘 1100원이 되는 것과 같습니다.')
]

# 샘플 데이터 삽입 (이미 존재하면 무시)
for name, description in products_to_insert:
    cursor.execute("INSERT OR IGNORE INTO products (name, description) VALUES (?, ?)", (name, description))

# 변경사항 저장 및 연결 종료
conn.commit()
conn.close()

print("데이터베이스 설정 및 샘플 데이터 추가 완료.")
