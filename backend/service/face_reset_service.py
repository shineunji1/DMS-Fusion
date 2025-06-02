from pymilvus import connections, Collection
from dao.face_reset_dao import FaceResetDAO
import numpy as np
import cv2
import dlib
import os
import time
import glob
from dao.face_reset_dao import FaceResetDAO


# 얼굴벡터가 저장된 경로
TEMP_FACE_DIR = "../temp_faces"

class FaceResetService:
    def __init__(self):
        self.face_reset_dao = FaceResetDAO()
        self.user_id = 0
        self.face_vectors = {}  # 여러 얼굴 벡터 저장을 위한 딕셔너리
        
        # dlib 모델 로드 (웹캠 캡처 추가)
        LANDMARK_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/shape_predictor_68_face_landmarks.dat"))
        RECOGNITION_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/dlib_face_recognition_resnet_model_v1.dat"))
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(LANDMARK_MODEL_PATH)
        self.face_rec_model = dlib.face_recognition_model_v1(RECOGNITION_MODEL_PATH)


    # 웹캠을 실행하여 얼굴을 감지하고 벡터값을 추출하는 함수
    def capture_face(self):
        # cap = cv2.VideoCapture(0)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # DirectShow 강제 사용
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) 

        if not cap.isOpened():
            print("❌ 웹캠을 열 수 없습니다.")
            return None

        ret, frame = cap.read()
        cap.release()
        if not ret:
            print("❌ 웹캠에서 프레임을 가져올 수 없습니다.")
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray)

        if len(faces) == 0:
            print("❌ 얼굴을 찾을 수 없습니다.")
            return None

        face = faces[0]  # 첫 번째 얼굴만 처리
        shape = self.predictor(gray, face)
        face_descriptor = self.face_rec_model.compute_face_descriptor(frame, shape)
        face_vector = np.array(face_descriptor)
        
        return face_vector

    # 얼굴 벡터를 임시저장 파일로 저장
    def save_temp_face(self, face_vector):
        file_name = f"user_face_{int(time.time())}.npy"
        file_path = os.path.join(TEMP_FACE_DIR, file_name)
        np.save(file_path, face_vector)
        print(f"얼굴 벡터값-> {file_path}에 저장")
        return file_path
    
 
    # 정면, 좌측, 우측 얼굴 벡터값 저장 실패시 그 전까지 촬영해서 저장한 정면, 좌측 벡터 삭제    
    def delete_register_face(delf, user_id):
        pattern = os.path.join(TEMP_FACE_DIR, f"{user_id}_*.npy")
        for file in glob.glob(pattern):
            os.remove(file)
            print(f"저장된 {user_id}의 얼굴 벡터 삭제: {file}")
            
    def register_face_front(self, user_id):
        print(f"📷 USER ID {user_id} : 얼굴 정면 촬영을 시작합니다", flush=True)
        
        face_vector = self.capture_face()  # ✅ face_vector 값을 가져오기
        
        if face_vector is not None:
            file_path = os.path.join(TEMP_FACE_DIR, f"{user_id}_front.npy")
            np.save(file_path, face_vector)
            self.face_vectors["front"] = face_vector.tolist()
        else:
            raise Exception("얼굴 정면 촬영 실패")
        
    def register_face_left(self, user_id):
        print(f"📷 USER ID {user_id} :  얼굴 좌측 촬영을 시작합니다", flush=True)
        time.sleep(0.5)
        face_vector = self.capture_face()
        if face_vector is not None:
            file_path = os.path.join(TEMP_FACE_DIR, f"{user_id}_left.npy")
            np.save(file_path, face_vector)
            self.face_vectors["left"] = face_vector.tolist()
        else:
            self.delete_register_face(user_id)
            raise Exception("좌측 얼굴 촬영 실패")
               
    def register_face_right(self, user_id):
        print(f"📷USER ID {user_id} : 얼굴 우측 촬영을 시작합니다", flush=True)
        time.sleep(0.5)
        face_vector = self.capture_face()
        if face_vector is not None:
            file_path = os.path.join(TEMP_FACE_DIR, f"{user_id}_right.npy")
            np.save(file_path, face_vector)
            self.face_vectors["right"] = face_vector.tolist()
        else:
            self.delete_register_face(user_id)
            raise Exception("우측 얼굴 촬영 실패")                

        # 최종적으로 모든 방향 얼굴 벡터가 저장되었는지 확인
        if len(self.face_vectors) == 3:
            print(f"✅USER ID {user_id} : 얼굴 벡터 저장 완료")
            user_id += 1
            return {"message": "얼굴 초기화 완료", "user_id": user_id}
        else:
            raise Exception("얼굴 촬영 데이터 부족")