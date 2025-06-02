
# 비즈니스 로직 계층(서비스 처리) : controller와 dao 사이에서 데이터를 처리
from dao.profile_dao import ProfileDAO
from model.profile_model import Profile

"""
DB를 사용하지 않고 self.profiles에 데이터를 저장
"""
class ProfileService:
    def __init__(self):
        # 사용자 프로필을 저장하는 딕셔너리 (DB 대신 임시 저장)
        self.profiles = {}
        
    # 프로필 정보를 저장하는 함수
    def create_profile(self, profile):
        self.profiles[profile.user_id] = {
            "user_name": profile.user_name,
            "profile_name": profile.profile_name,
            "profile_color": profile.profile_color
        }
        return {"message": "Profile saved successfully", "data": self.profiles[profile.user_id]}


    # 서비스 (profile_service.py)
    def get_profile(self, user_id: int):
        print(f"서비스: user_id={user_id} 데이터 요청 받음")
        
        mock_profiles = {
            1: {"user_name": "김보라", "profile_name": "bora", "profile_color": "blue"},
            2: {"user_name": "이준혁", "profile_name": "jh", "profile_color": "yellow"}
        }
        
        profile = mock_profiles.get(user_id, None)
        print(profile)
        
        if profile is None:
            print(f"===== 서비스: user_id={user_id} 프로필 없음 =====")
        
        print(f"===== 서비스: 반환할 데이터={profile} =====")
        
        return profile, []  # 두 번째 값은 빈 리스트 반환
