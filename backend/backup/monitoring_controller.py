from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from service.monitoring_service import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
monitoring_service = MonitoringService()

@router.get("/status")
def get_monitoring_status():
    return monitoring_service.get_monitoring_status()

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
    new_status = monitoring_service.toggle_monitoring()
    print("변화된 상태:", new_status)
    return {"message": f"Monitoring status changed to {new_status}", "status" : new_status}

@router.get("/video")
def video_feed():
    """📡 OpenCV 스트리밍 API"""
    return StreamingResponse(monitoring_service.generate_frames(),
                             media_type="multipart/x-mixed-replace; boundary=frame")

# 이 부분 수정 => 아래 주석 부분 추가
@router.get("/video_feed")
def video_feed():
    """웹캠 스트리밍 API"""
    # 카메라 시작 여부 확인
    if not monitoring_service.running or monitoring_service.cap is None:
        monitoring_service.start_monitoring()
        
    return StreamingResponse(
        monitoring_service.generate_frames(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/distraction")
def get_distraction_status():
    """현재 주의분산 감지 상태 반환"""
    status = monitoring_service.get_monitoring_status()
    print(status)
    return {"status": status}
