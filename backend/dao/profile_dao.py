# 데이터베이스 접근 계층(데이터 읽기/쓰기)
from model.profile_model import Profile

class ProfileDAO:
    def __init__(self):
        # 간단한 In-Memory 데이터 저장소 (추후 DB로 대체 가능)
        self.users = {}

    # 특정 유저 조회
    def get_profile(self, user_id: int):
        return self.profiles.get(user_id, {"error": "Profile not found"})
    
    # 새로운 유저 저장
    def update_profile(self, profile):
        self.profiles[profile.id] = profile.dict()
        finish = "다했음"
        return {"message": "Profile updated successfully", "profile": self.profiles[profile.id]}