from datetime import datetime  # datetime 모듈에서 datetime 클래스만 임포트
from pydantic import BaseModel, ConfigDict
from typing import Optional

class User(BaseModel):
    user_id: int
    user_name: str
    profile_name: str
    profile_color: str
    signup_date: datetime  # datetime.datetime이 아닌 datetime 클래스 사용
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat()
        }
    )
    
    @classmethod
    def from_tuple(cls, result):
        if not result:
            return None
        
        return cls(
            user_id=result[0],
            user_name=result[1],
            profile_name=result[2],
            profile_color=result[3],
            signup_date=result[4]
        )