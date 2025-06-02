import sys
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import logging
from typing import List
import json

# 로그 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 컨트롤러 임포트
from controller import (
    face_reset_controller,
    monitoring_controller,
    profile_controller,
    seat_controller,
    login_contoller,
)

# 웹소켓 설정 가져오기
from config.websocket import get_manager

app = FastAPI()


origins = ["http://localhost:3000", "http://127.0.0.1:3000"]  # 기본 허용 출처

@app.middleware("http")
async def add_cors_header(request, call_next):
    origin = request.headers.get("origin", "")
    # ngrok-free.app으로 도메인 확인
    if origin and "ngrok-free.app" in origin:
        origins.append(origin)
    
    response = await call_next(request)
    
    if origin in origins or "ngrok-free.app" in origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,  # React 앱의 주소
    allow_credentials=True,
    allow_methods=["*"],  # 명시적인 메서드 지정
    allow_headers=["*"],  # 필요한 헤더 지정
)

app.add_middleware(
    SessionMiddleware,
    secret_key="my-secret-key",  # Express의 secret과 동일
    session_cookie="moca",  # Express의 name과 동일
    max_age=None,  # 세션 만료 시간 (None은 브라우저 세션 동안만 유효)
    same_site="lax",  # Express의 sameSite와 동일
    https_only=False,  # Express의 secure와 동일
    path="/",  # Express의 path와 동일
)

# 기본 WebSocket 엔드포인트
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, manager=Depends(get_manager)):
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"메세지 받음: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("클라이언트 종료")

# 라우터 등록
app.include_router(face_reset_controller.router)
app.include_router(monitoring_controller.router)
app.include_router(profile_controller.router)
app.include_router(seat_controller.router)
app.include_router(login_contoller.router)

@app.get("/session-chk")
def session_chk(request:Request):
    
    print("요청 쿠키:", request.cookies)  # 쿠키 내용을 확인
    print("세션 데이터:", request.session)  # 세션 데이터 확인
    
    if "user_data" in request.session:
        return {"item": request.session["user_data"], "authenticated": True}
    else:
        return {"authenticated": False}

@app.get("/logout")
def session_chk(request:Request):
    request.session.clear()
    return {"message": "로그아웃 성공!", "authenticated": False}


# 애플리케이션 시작 시 로그 출력
@app.on_event("startup")
async def startup_event():
    logger.info("애플리케이션 시작")
    logger.info("WebSocket 관리자 초기화 완료")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        access_log=True,
        log_config=None  # 기본 uvicorn 로그 설정 사용
    )