# 데이터 모델 정의 (Pydantic을 이용해 데이터 검증) : 유저 데이터를 검증하는 역할을 함.
from pydantic import BaseModel

class Profile(BaseModel):
    user_id: int
    user_name: str
    user_pwd: str
    profile_name: str
    profile_color: str  # 색상은 HEX 코드 (예: "#ff5733")