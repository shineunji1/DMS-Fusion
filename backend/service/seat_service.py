
from dao.seat_dao import SeatDAO
from model.seat_model import SeatSettings
from fastapi import Path
import urllib.parse # url 디코딩을 위한 라이브러리 추가

class SeatService:
    def __init__(self):
        # ✅ 사용자별 좌석 설정 저장 (기본값 포함)
        self.user_seat_positions = {
            1: {  # user_id 1번 사용자의 좌석 정보
                "머리": {"각도": 10},
                "등받이": {"각도": -5},
                "좌석": {"좌우": 0.2, "상하": 0.1, "전후": -0.1},
                "핸들": {"좌우": 0.5, "상하": 0.2, "전후": 0.3},
            },
            2: {  # user_id 2번 사용자의 좌석 정보
                "머리": {"각도": 3},
                "등받이": {"각도": 0},
                "좌석": {"좌우": -0.1, "상하": 0.0, "전후": 0.1},
                "핸들": {"좌우": 0.4, "상하": 0.0, "전후": 0.2},
            },
            3: {  # user_id 3번 사용자의 좌석 정보 (추가)
                "머리": {"각도": 7},
                "등받이": {"각도": 2},
                "좌석": {"좌우": 0.0, "상하": 0.0, "전후": 0.0},
                "핸들": {"좌우": 0.6, "상하": 0.1, "전후": -0.1},
            }
        }

    def get_seat_settings(self, user_id: int, position: str):
        """
        특정 프로필(user_id)의 특정 좌석 위치 설정 값 반환
        """
        
        position = urllib.parse.unquote(position)  # ✅ URL 디코딩 추가
        print(f"=== 요청된 user_id: {user_id}, position: {position} ===")  # 디버깅용



        # ✅ 사용자의 좌석 설정이 없으면 기본값 추가
        if user_id not in self.user_seat_positions:
            self.user_seat_positions[user_id] = {
                "머리": {"각도": 0},
                "등받이": {"각도": 0},
                "좌석": {"좌우": 0.2, "상하": -1, "전후": 0.0},
                "핸들": {"좌우": 0.2, "상하": 0.5, "전후": -0.5},
            }
            print(f"✅ user_id {user_id} 기본 좌석 설정 추가됨")

        # ✅ 존재하는 position인지 확인
        if position not in self.user_seat_positions[user_id]:
            print(f"🚨 ERROR: position '{position}' 없음")
            return {"error": f"Invalid position: {position}"}

        return self.user_seat_positions[user_id][position]


    def update_seat_settings(self, body):
        """
        ✅ 특정 좌석 위치의 설정 값을 업데이트 (버튼 입력값 반영)
        """
        print(body)

        return None