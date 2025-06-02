from fastapi import APIRouter,WebSocket, WebSocketDisconnect

from fastapi.responses import StreamingResponse
from service.monitoring_service import MonitoringService
import json
import asyncio

from config.websocket import get_manager

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
monitoring_service = MonitoringService()

manager = get_manager()

@router.websocket("/ws")
async def monitoring_websocket(websocket: WebSocket):
    """모니터링 정보를 실시간으로 전송하는 WebSocket 엔드포인트"""

    await manager.connect(websocket)
    
    try:
        # 초기 상태 전송
        initial_status = {
            "distraction_state": monitoring_service.get_distraction_status(),
            "drowsiness_state": monitoring_service.get_drowsiness_status(),
        }
        await websocket.send_text(json.dumps(initial_status))
        
        # 클라이언트와 통신 유지
        while True:
            # 클라이언트로부터 메시지 수신 (비동기 대기)
            data = await websocket.receive_text()
            
            if data == "ping":
                # 핑-퐁 메시지로 연결 유지
                await websocket.send_text("pong")
            elif data == "get_status":
                # 최신 상태 요청 처리
                current_status = {
                    "distraction_state": monitoring_service.get_distraction_status(),
                    "drowsiness_state": monitoring_service.get_drowsiness_status(),
                }
                await websocket.send_text(json.dumps(current_status))
    
    except WebSocketDisconnect:
        # 연결이 끊어지면 매니저에서 제거
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 통신 오류: {e}")
        manager.disconnect(websocket)

@router.get("/status")
def get_monitoring_status():
    """✅ 현재 모니터링 상태 조회 (True/False)"""
    return {"status": monitoring_service.status}

@router.post("/start")
def start_monitoring():
    """모니터링 시작"""
    monitoring_service.start_monitoring()
    return {"status": "monitoring started"}

@router.post("/stop")
def stop_monitoring():
    """모니터링 중지"""
    monitoring_service.stop_monitoring()
    return {"status": "monitoring stopped"}

@router.get("/toggle")
def toggle_monitoring():
    """✅ 모니터링 상태 ON/OFF 토글"""
    # new_status = monitoring_service.toggle_monitoring()
    return monitoring_service.toggle_monitoring()

# 중복 함수 라우팅 하나 삭제 => /video
# 카메라 실행 안되면 예외처리 추가 
@router.get("/video_feed")
def video_feed():
    """웹캠 스트리밍 API"""
    try:
        # 모니터링 서비스가 초기화되었는지 확인
        if monitoring_service.status is False:
            return {"error": "모니터링 서비스가 초기화되지 않았습니다"}
        
        # 스트리밍 응답 반환
        return StreamingResponse(
            monitoring_service.generate_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        print(f"❌ [API] 비디오 피드 처리 중 오류: {str(e)}")
        return {"error": f"비디오 스트리밍 중 오류 발생: {str(e)}"}
    
# @router.get("/distraction")
# def get_distraction_status():
#     """현재 주의분산 감지 상태 반환"""
#     status = monitoring_service.get_monitoring_status()
#     print(status)
#     return {"status": status}

@router.get("/distraction")
def get_distraction_status():
    """✅ 주의 분산 감지 실행"""
    if monitoring_service.status:  # ✅ True면 실행
        monitoring_service.start_monitoring()
    else:
        monitoring_service.stop_monitoring()
        return {"status": False}
        
    # return {"status": monitoring_service.status == "on"} # 상태비교해서 Boolean 반환
    
@router.get("/drowsiness")
def get_drowsiness_status():
    """졸음 감지 상태 반환 API"""
    return {"status": monitoring_service.get_monitoring_status()}

# 주기적으로 모든 클라이언트에게 상태 업데이트를 보내는 백그라운드 작업
async def background_status_update():
    while True:
        if manager.active_connections:  # 연결된 클라이언트가 있을 때만 실행    
            current_status = {
                "distraction_state": monitoring_service.get_distraction_status(),
                "drowsiness_state": monitoring_service.get_drowsiness_status(),
            }
            await manager.broadcast(json.dumps(current_status))
        await asyncio.sleep(1)  # 1초마다 업데이트
        
# 라우터 초기화 부분에 추가
@router.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(background_status_update())
