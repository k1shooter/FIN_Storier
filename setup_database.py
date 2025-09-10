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
    ('인플레이션', '인플레이션은 물가가 전반적으로 꾸준히 오르는 현상입니다. 시간이 지나면서 같은 돈으로 살 수 있는 물건의 양이 줄어드는 것을 의미합니다. 예를 들어, 어제 1000원이었던 과자가 오늘 1100원이 되는 것과 같습니다.'),
    ('채권', '채권은 정부나 기업이 돈을 빌리기 위해 발행하는 일종의 IOU(차용증서)입니다. 채권을 사면 일정 기간 후에 원금과 이자를 돌려받을 수 있습니다. 주식보다 안정적인 투자 수단으로 여겨집니다.'),
    ('펀드', '펀드는 여러 투자자들이 모은 돈을 한데 모아 전문가가 다양한 자산에 투자하는 금융 상품입니다. 이를 통해 개인 투자자는 적은 금액으로도 다양한 자산에 분산 투자할 수 있습니다.'),
    ('현대카드_제로_에디션', '현대카드 ZERO Edition3(할인형)은 복잡한 할인 조건이나 전월 실적 요구 없이 모든 가맹점에서 0.8%의 기본 할인을 제공하는 직관적인 신용카드입니다. 여러 카드의 혜택을 비교하고 사용처에 맞춰 카드를 변경하는 번거로움 없이, 카드 한 장으로 꾸준한 할인 혜택을 누리고 싶은 고객에게 유리합니다. 특히, 생활 필수 영역인 온라인 간편결제, 대형마트, 편의점, 음식점, 커피전문점, 대중교통 이용 시에는 1.6%의 특별 할인율이 적용되어 일상생활 속에서 더 큰 혜택을 체감할 수 있습니다.')
]

# 샘플 데이터 삽입 (이미 존재하면 무시)
for name, description in products_to_insert:
    cursor.execute("INSERT OR IGNORE INTO products (name, description) VALUES (?, ?)", (name, description))

# 변경사항 저장 및 연결 종료
conn.commit()
conn.close()

print("데이터베이스 설정 및 샘플 데이터 추가 완료.")
