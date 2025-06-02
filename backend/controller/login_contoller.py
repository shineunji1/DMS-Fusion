from fastapi import APIRouter, HTTPException, Response, Body, WebSocket, WebSocketDisconnect, Request, logger
from starlette.responses import StreamingResponse
from fastapi.responses import StreamingResponse
import asyncio
import json

import os
import numpy as np
import time


from service.login_service import LoginService, set_websocket_manager
from service.anti_spoofing_service import AntiSpoofingService
from model.login_model import FaceIDRequest, FaceRegistrationRequest, FaceDirection
from model.profile_model import Profile
from model.face_data import FaceData 

from config.websocket import get_manager, ConnectionManager

router = APIRouter(prefix="/login", tags=["login"])
login_service = LoginService()
anti_spoofing_service = AntiSpoofingService()

# manager 가져오기
manager = get_manager()  # 또는 main에서 직접 import한 manager 사용
set_websocket_manager(manager)

# 얼굴 벡터값 임시 저장 폴더
TEMP_FACE_DIR = "../temp_faces"  
if not os.path.exists(TEMP_FACE_DIR):
    os.makedirs(TEMP_FACE_DIR)

# 로그인 페이지 API
@router.get("/stream")
def login_page():
    return StreamingResponse(login_service.generate_frames_with_face_vectors(),
                             media_type="multipart/x-mixed-replace; boundary=frame")
    
@router.websocket("/ws/face-status")
async def face_status_ws(websocket: WebSocket):
    await manager.connect(websocket)
    print("WebSocket 연결됨: 현재", len(manager.active_connections), "개 연결")
    
    # 마지막 상태와 시간 추적
    last_status = None
    last_update_time = time.time()
    
    try:
        while True:
            # 클라이언트로부터 메시지 받기 (비동기로 짧은 타임아웃 설정)
            try:
                # 클라이언트 연결 상태 확인 (ping/pong)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0
                )
                
                # 'close' 메시지를 받으면 정상적으로 연결 종료
                if data == "close":
                    print("클라이언트에서 연결 종료 요청")
                    break
                    
            except asyncio.TimeoutError:
                # 타임아웃은 정상, 상태 업데이트 계속 진행
                pass
            except Exception as e:
                # 다른 예외는 연결 문제로 간주
                print(f"WebSocket 수신 오류: {e}")
                break
            
            # 얼굴 감지 상태 확인 및 전송
            current_time = time.time()
            if current_time - last_update_time >= 1.0:
                current_status = login_service.is_face_detected()
                print(f"보내는 얼굴 감지 상태: {current_status}, 타입: {type(current_status)}")
                
                # 상태가 변경됐을 때만 전송
                if current_status != last_status:
                    message = json.dumps({"face_detected": current_status})
                    print(f"WebSocket으로 전송: {message}")
                    await websocket.send_text(message)
                    last_status = current_status
            
            # 비동기 대기 (CPU 부하 감소)
            await asyncio.sleep(0.2)
            
    except WebSocketDisconnect:
        print("WebSocket 연결 끊김")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 오류: {str(e)[:100]}")
        manager.disconnect(websocket)
    finally:
        # 연결 종료 시 항상 disconnect 호출
        manager.disconnect(websocket)
        print("WebSocket 연결 해제됨: 현재", len(manager.active_connections), "개 연결")
        
@router.get("/face-status")
def get_face_status():
    face_detected = login_service.is_face_detected()
    return {"face_detected": face_detected}

# 얼굴 촬영 및 벡터 출력 API
@router.get("/capture-face")
def capture_face():
    try:
        # 안티 스푸핑 시작
        anti_spoofing_service.start()
        
        # 안티 스푸핑 확인 (최대 3회 시도)
        is_real_face = False
        for attempt in range(3):
            is_real_face = anti_spoofing_service.check_real_face()
            if is_real_face:
                break
            time.sleep(0.5)  # 짧은 대기 시간
            
        if not is_real_face:
            raise HTTPException(status_code=401, detail={"message":"위조된 얼굴이 감지되었습니다!", "success": False})
        
        # 얼굴 벡터 추출 (최대 3회 시도)
        face_vector = None
        for attempt in range(3):
            try:
                # 명시적으로 안티스푸핑 서비스 중지 후 로그인 서비스 시작
                anti_spoofing_service.stop()  # 안티스푸핑 중지
                time.sleep(0.2)  # 리소스 전환 시간
                
                # 얼굴 벡터 캡처 시도
                face_vector = login_service.capture_face(release_camera=False)
                if face_vector is not None:
                    break
            except Exception as e:
                print(f"얼굴 벡터 추출 시도 {attempt+1}/3 실패: {e}")
            time.sleep(0.5)  # 재시도 전 대기
        
        # 얼굴 벡터 추출 실패
        if face_vector is None:
            raise HTTPException(status_code=401, detail={"message":"얼굴을 찾을 수 없습니다!", "success": False})
        
        # 성공적으로 벡터 반환
        return {"embedding": face_vector.tolist(), "success": True}
        
    except Exception as e:
        print(f"캡처 과정 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail={"message": f"서버 오류가 발생했습니다: {str(e)}", "success": False})
    
    finally:
        # 항상 카메라 리소스 정리
        try:
            login_service.release_camera()
        except:
            pass

# FaceID 인증 API
@router.post("/face-id")
def verify_face(face_data: FaceIDRequest, request: Request): 
    print("얼굴 벡터값을 받았어요!",face_data.embedding)

    user_id = login_service.verify_face(face_data.embedding) 
    if user_id:
        result = login_service.find_user(user_id)
        print(result)
        if(result) :
            request.session["user_data"] = {
                "user_id": result["user_id"],
                "user_name": result["user_name"],
                "profile_name": result["profile_name"],
                "profile_color": result["profile_color"],
                "signup_date": result["signup_date"].isoformat()  # datetime을 문자열로 변환
            }
            print(request.session)
            return {"message":"login success", "item":result, "success": True}
        else:
            return {"message":"login fail", "success": False}
    else :
        return {"message":"login fail", "success": False}



@router.post("/signup")
def register_face(request: FaceRegistrationRequest):
    try:
        direction = request.direction

        if direction == FaceDirection.front:
            front_res = login_service.register_face_front()
            print(front_res)
            return {"message": "정면 얼굴 촬영 완료" , "status" : front_res}
        
        elif direction == FaceDirection.left:
            left_res = login_service.register_face_left()
            return {"message": "좌측 얼굴 촬영 완료", "status" : left_res}

        elif direction == FaceDirection.right:
            result = login_service.register_face_right()
            print("결과 값:", result)
            if result :
                res = login_service.register_user(result)
                if res:
                    return {"message":"유저 생성완료!", "success": True, "userId": result}

        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 얼굴 방향입니다.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-profile")
def add_profile(request: Profile):
    
    result = login_service.profile_add(request)
    
    if(result) :
        return {"message": "프로필 등록완료!", "success": result}
    else:
        return None
    
@router.post("/manual")
async def manual_login(request: Request):
    data = await request.body()
    data = json.loads(data.decode("utf-8"))
    result = login_service.manual_login(data["user_pwd"])
    if(result) :
            request.session["user_data"] = {
                "user_id": result["user_id"],
                "user_name": result["user_name"],
                "profile_name": result["profile_name"],
                "profile_color": result["profile_color"],
                "signup_date": result["signup_date"].isoformat()  # datetime을 문자열로 변환
            }
            print(request.session)
            return {"message":"login success", "item":result, "success": True}
    else:
        return {"message":"login fail", "success": False}
    