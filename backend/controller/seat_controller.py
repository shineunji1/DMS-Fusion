
from fastapi import APIRouter, Body, Request
from service.seat_service import SeatService
from model.seat_model import SeatSettings

router = APIRouter(prefix="/seat-set", tags=["seat-set"])
seat_service = SeatService()

@router.get("/")
def get_all_seat_positions():
    """
    모든 좌석 위치의 설정 값을 반환하는 API
    """
    return {
        "message": "Seat positions fetched successfully",
        "positions": ["머리", "등받이", "좌석", "핸들"]
    }


@router.get("/{user_id}/{position}")
def get_seat_position(user_id: int):
    """
    특정 좌석 위치(머리, 등받이, 좌석, 핸들)의 설정 값을 가져오는 API
    """
    return seat_service.get_seat_settings(user_id)

@router.put("/{user_id}")
async def update_seat_position(user_id: int, request:Request):
    """
    특정 좌석 위치(머리, 등받이, 좌석, 핸들)의 설정 값을 업데이트하는 API
    """
    body = await request.json()
    
    return seat_service.update_seat_settings(body)
