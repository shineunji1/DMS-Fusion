# config/websocket.py
from fastapi import WebSocket
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket 연결 성공: 현재 {len(self.active_connections)}개 연결")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"WebSocket 연결 종료: 현재 {len(self.active_connections)}개 연결")

    async def broadcast(self, message: str):
        """모든 연결된 클라이언트에 메시지 브로드캐스트"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"메시지 전송 중 오류: {e}")
                disconnected.append(connection)
        
        # 연결 끊긴 클라이언트 제거
        for conn in disconnected:
            self.disconnect(conn)

# 싱글톤 인스턴스 생성
manager = ConnectionManager()

def get_manager():
    """WebSocket 연결 관리자 인스턴스 반환"""
    return manager