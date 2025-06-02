from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse
from fastapi.responses import StreamingResponse
import cv2
import dlib
import numpy as np
from service.face_reset_service import FaceResetService
from model.face_reset_model import FaceResetRequest
from model.face_data import FaceData
from model.face_reset_model import FaceIDRequest
from model.face_reset_model import FaceRegistrationRequest, FaceDirection

router = APIRouter(prefix="/face-reset", tags=["face-reset"])
face_reset_service = FaceResetService()

# 얼굴 벡터값이 저장된 폴더
TEMP_FACE_DIR = "../temp_faces"  

@router.post("/")
def reset_face(request: FaceResetRequest):
    print(f"📥 얼굴 초기화 요청 수신: {request}")
    return  {"message": "face reset API is active.", "user_id": request.user_id}

# 웹캠 스트리밍 API
def generate_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    detector = dlib.get_frontal_face_detector()  # 얼굴 감지기 로드

    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # ✅ 그레이스케일 변환 후 얼굴 감지
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray, 1)

        # ✅ 감지된 얼굴마다 바운딩 박스 추가
        for face in faces:
            x, y, w, h = face.left(), face.top(), face.width(), face.height()
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)  # 초록색 사각형
        
        # ✅ 프레임을 웹 브라우저로 전송
        _, buffer = cv2.imencode(".jpg", frame)
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

    cap.release()

# 웹캠 스트리밍을 제공하는 API   
@router.get("/stream")
def stream_video(): 
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# 얼굴 촬영 및 벡터 출력 API
@router.get("/capture-face")
def capture_face():
    face_vector = face_reset_service.capture_face()
    if face_vector is None:
        raise HTTPException(status_code=400, detail="얼굴을 찾을 수 없습니다.")
    return {"embedding" : face_vector.tolist()}


@router.post("/capture/{user_id}")
def capture_images(user_id: int):
    """
    웹캠을 실행하여 사용자의 얼굴 사진을 촬영하고 저장
    """
    return face_reset_service.capture_images(user_id)


# FaceID 인증 API
@router.post("/face-id")
def verify_face(face_data: FaceIDRequest):  
    print("얼굴 벡터값을 받았어요!")
    user_id = face_reset_service.verify_face(face_data) 
    
    if user_id: 
        return {"message": "Login successful", "user_num": user_id}
    return {"message": "User not found", "options": ["register", "retry", "password_login"]}

@router.post("/register")
def register_face(request: FaceRegistrationRequest):
    try:
        direction = request.direction
        user_id = request.user_id

        if direction == FaceDirection.front:
            face_reset_service.register_face_front(user_id)
            return {"message": "정면 얼굴 촬영 완료"}
        
        elif direction == FaceDirection.left:
            face_reset_service.register_face_left(user_id)
            return {"message": "좌측 얼굴 촬영 완료"}

        elif direction == FaceDirection.right:
            result = face_reset_service.register_face_right(user_id)
            return {"message": "우측 얼굴 촬영 완료", "result": result}

        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 얼굴 방향입니다.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    