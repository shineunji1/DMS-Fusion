# API 요청을 처리하는 라우터 : FastAPI 엔드포인트 정의
from fastapi import APIRouter
from fastapi.logger import logger
from service.profile_service import ProfileService
from model.profile_model import Profile
from service import profile_service
from model.profile_model import Profile

router = APIRouter(prefix="/profile", tags=["profile"])
profile_service = ProfileService()

# 이제 GET /profile/ 요청이 가능하므로 Next.js에서 기존 fetch(url)을 그대로 사용해도 됨.
@router.get("/")
def get_all_profiles():
    print("프로필 전체 조회")
    return {"message":"All profile fetched successfull","profiles":[]}


# 컨트롤러 (profile_controller.py)
@router.get("/{user_id}")
def get_profile(user_id: int):
    print("프로필 접속")
    logger.info(f"user_id: {user_id}")
    profiles, _ = profile_service.get_profile(user_id)  # 여기서 두 값을 언패킹합니다
    if profiles:
        return {"message":"프로필 조회 성공", "item": profiles}
    else:
        raise HTTPException(status_code=404, detail={"message": "프로필 조회 실패", "item": {"error": "Profile not found"}})



# 새로운 유저 생성 API
@router.post("/")
def create_profile(profile: Profile):
    return profile_service.create_profile(profile)

