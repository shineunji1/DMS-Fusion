from pydantic import BaseModel

class SeatSettings(BaseModel):
    position: str  # "머리", "등받이" 등
    angle: float
    좌우: float
    상하: float
    전후: float
