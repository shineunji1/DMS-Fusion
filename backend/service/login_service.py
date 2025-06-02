from pymilvus import connections, Collection
from dao.login_dao import LoginDAO
import numpy as np
import cv2
import dlib
import os
import time
import glob
import asyncio
import json
import logging
from typing import List, Dict, Optional, Generator, AsyncGenerator

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 얼굴벡터 임시저장 경로
TEMP_FACE_DIR = "../temp_faces"
if not os.path.exists(TEMP_FACE_DIR):
    os.makedirs(TEMP_FACE_DIR)

# WebSocket 연결 관리를 위한 전역 변수
manager = None

def set_websocket_manager(websocket_manager):
    """WebSocket 매니저를 설정하는 함수"""
    global manager
    manager = websocket_manager
    logger.info("WebSocket 매니저가 LoginService에 설정되었습니다")

class LoginService:
    def __init__(self):
        self.login_dao = LoginDAO()
        self.user_id = None
        self.face_vectors = {}
        self.cap = None
        
        # 벡터 추출 관련 변수
        self.last_vector_time = 0
        self.vector_cooldown = 2.0
        
        # 얼굴 감지 상태 관련 변수
        self._face_detected = False
        self._last_detection_time = time.time()
        self._capturing_right_face = False
        
        # 등록 상태 플래그 (얼굴 등록 중에만 캡처 허용)
        self.registration_in_progress = False
        
        # dlib 모델 로드
        LANDMARK_MODEL_PATH = "models/shape_predictor_68_face_landmarks.dat"
        RECOGNITION_MODEL_PATH = "models/dlib_face_recognition_resnet_model_v1.dat"
        
        if not os.path.exists(LANDMARK_MODEL_PATH) or not os.path.exists(RECOGNITION_MODEL_PATH):
            logger.error("dlib 모델 파일이 존재하지 않습니다")
            raise FileNotFoundError("dlib 모델 파일을 확인해주세요")
        
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(LANDMARK_MODEL_PATH)
        self.face_rec_model = dlib.face_recognition_model_v1(RECOGNITION_MODEL_PATH)
        
        # 카메라 초기화
        self._initialize_camera()
        
        # 프레임 처리 변수
        self.face_detected = False
        self.last_frame_time = time.time()
        self.frame_interval = 1/15  # 15fps
    
    def _initialize_camera(self) -> bool:
        """최소한의 카메라 초기화 함수"""
        try:
            # 이미 열려있고 작동 중이면 다시 초기화하지 않음
            if self.cap and self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    logger.info("카메라가 이미 작동 중입니다")
                    return True
                    
            # 기존 카메라 해제
            self.release_camera()
            
            # 카메라 연결 시도 (여러 번 시도)
            for attempt in range(3):  # 최대 3번 시도
                logger.info(f"카메라 연결 시도 {attempt+1}/3")
                self.cap = cv2.VideoCapture(0)
                
                if self.cap and self.cap.isOpened():
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None:
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        logger.info("카메라 연결 성공")
                        return True
                    else:
                        self.cap.release()
                        self.cap = None
                        logger.warning(f"카메라 열렸으나 프레임 읽기 실패 ({attempt+1}/3)")
                        time.sleep(0.5)
                else:
                    logger.warning(f"카메라 열기 실패 ({attempt+1}/3)")
                    time.sleep(0.5)
                    
            logger.error("모든 카메라 연결 시도 실패")
            return False
        except Exception as e:
            logger.error(f"카메라 초기화 오류: {e}")
            return False
    
    def release_camera(self):
        """카메라 리소스를 명시적으로 해제"""
        if self.cap is not None and self.cap.isOpened():
            try:
                self.cap.release()
                self.cap = None
                logger.info("카메라 리소스 해제 완료")
            except Exception as e:
                logger.error(f"카메라 해제 오류: {e}")
    
    def __del__(self):
        """소멸자: 리소스 정리"""
        self.release_camera()

    async def update_face_detection_status(self, detected: bool):
        if self._face_detected != detected:
            self._face_detected = detected
            self._last_detection_time = time.time()
            if manager:
                message = json.dumps({"face_detected": detected})
                await manager.broadcast(message)
        return self._face_detected

    async def broadcast_face_status(self):
        """WebSocket 클라이언트에 얼굴 감지 상태 브로드캐스트"""
        if manager is None:
            logger.warning("WebSocket 매니저가 설정되지 않았습니다")
            return
        try:
            message = json.dumps({"face_detected": self._face_detected})
            await manager.broadcast(message)
            logger.debug(f"얼굴 감지 상태 브로드캐스트: {self._face_detected}")
        except Exception as e:
            logger.error(f"브로드캐스트 오류: {e}")

    def is_face_detected(self) -> bool:
        """현재 얼굴 감지 상태 반환"""
        return self.face_detected

    def generate_frames_with_face_vectors(self) -> Generator[bytes, None, None]:
        """얼굴 벡터 추출 및 프레임 생성"""
        try:
            # 카메라 초기화
            if not self._initialize_camera():
                logger.error("카메라 초기화 실패")
                # 카메라 없이 임시 이미지 반환
                empty_img = np.zeros((240, 320, 3), dtype=np.uint8)
                cv2.putText(empty_img, "Camera Error", (50, 120), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                _, buffer = cv2.imencode('.jpg', empty_img, encode_param)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                return
            
            while True:
                current_time = time.time()
                if current_time - self.last_frame_time < self.frame_interval:
                    time.sleep(max(0, self.frame_interval - (current_time - self.last_frame_time)))
                
                success, frame = self.cap.read()
                if not success:
                    logger.warning("카메라 프레임 읽기 실패, 재연결 시도")
                    self._initialize_camera()
                    time.sleep(1)
                    continue
                
                processed_frame, self.face_detected = self.process_frame(frame)
                
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                success, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
                if not success:
                    logger.error("JPEG 인코딩 실패")
                    continue
                
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                self.last_frame_time = time.time()
        
        except Exception as e:
            logger.error(f"스트림 생성 오류: {e}")
        finally:
            self.release_camera()

    def process_frame(self, frame):
        """프레임 처리 및 얼굴 감지"""
        try:
            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            start_time = time.time()
            faces = self.detector(small_frame, 0)
            
            if time.time() - start_time > 0.5:
                logger.warning("얼굴 감지 타임아웃")
                return frame, False
            
            face_detected = len(faces) > 0
            for face in faces:
                x, y, w, h = face.left()*2, face.top()*2, face.width()*2, face.height()*2
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            self._face_detected = face_detected
            return frame, face_detected
        
        except Exception as e:
            logger.error(f"프레임 처리 오류: {e}")
            return frame, False
    
    # capture_face 메소드도 수정
    def capture_face(self, release_camera=True):
        """얼굴 캡처 및 벡터 추출 - 등록 과정 중에만 허용"""
        logger.info("얼굴 캡처 시도 중...")
        
        # 등록 과정 중인지 확인
        if not self.registration_in_progress:
            try:
                # 이미 저장된 얼굴 있는지 확인
                collection = self.login_dao.get_face_collection()
                count = collection.num_entities
                
                if count > 0:
                    logger.warning("⚠️ 등록 진행 중이 아닌 상태에서는 캡처할 수 없습니다")
                    return None
                else:
                    logger.info("✅ 등록된 얼굴이 없어 캡처를 허용합니다")
            except Exception as e:
                logger.error(f"❌ Milvus 확인 중 오류: {e}")
                # 오류 발생 시에도 계속 진행 (없는 것으로 처리)
                logger.info("✅ Milvus 확인 오류로 캡처를 허용합니다")
        
        # 카메라 상태 확인
        if not self.cap or not self.cap.isOpened():
            if not self._initialize_camera():
                logger.error("카메라 초기화 실패")
                return None
        
        face_vector = None
        try:
            # 여러 번 시도
            max_attempts = 10
            for attempt in range(max_attempts):
                success, frame = self.cap.read()
                if not success:
                    logger.warning(f"프레임 읽기 실패 ({attempt+1}/{max_attempts})")
                    time.sleep(0.3)
                    continue
                
                # 얼굴 감지
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.detector(gray, 0)
                
                if len(faces) > 0:
                    try:
                        shape = self.predictor(gray, faces[0])
                        face_vector = np.array(self.face_rec_model.compute_face_descriptor(frame, shape))
                        logger.info("얼굴 벡터 추출 성공")
                        break
                    except Exception as e:
                        logger.error(f"벡터 추출 실패: {e}")
                
                logger.debug(f"얼굴 감지 중... ({attempt+1}/{max_attempts})")
                time.sleep(0.3)
            
            if face_vector is None:
                logger.error("얼굴 감지 시간 초과")
                return None
            
            return face_vector
        
        except Exception as e:
            logger.error(f"캡처 오류: {e}")
            return None
        
        finally:
            # 등록 과정 중에는 카메라 해제하지 않음
            if release_camera and not self.registration_in_progress:
                logger.info("카메라 리소스 해제")
                self.release_camera()

    def save_temp_face(self, face_vector):
        """얼굴 벡터를 임시 파일로 저장"""
        file_name = f"user_face_{int(time.time())}.npy"
        file_path = os.path.join(TEMP_FACE_DIR, file_name)
        np.save(file_path, face_vector)
        logger.info(f"얼굴 벡터 저장: {file_path}")
        return file_path

    def find_face_in_temp_db(self, query_vector):
        """Milvus에서 유사한 얼굴 벡터 검색"""
        logger.info("Milvus에서 얼굴 벡터 확인 중")
        user_id = self.login_dao.find_face_by_vector(query_vector, threshold=0.2)
        
        if user_id:
            logger.info(f"얼굴 인증 성공! 사용자 ID: {user_id}")
            return user_id
        logger.info("일치하는 얼굴 벡터 없음")
        return None

    def verify_face(self, face_data):
        """얼굴 벡터 검증"""
        query_vector = np.array(face_data)
        user_id = self.find_face_in_temp_db(query_vector)
        if user_id:
            return user_id
        
        logger.info("얼굴 벡터 추가 확인 중...")
        start_time = time.time()
        while time.time() - start_time < 1:
            user_id = self.find_face_in_temp_db(query_vector)
            if user_id:
                return user_id
        logger.info("일치하는 얼굴을 찾지 못했습니다")
        return None
    
    
    def register_face_front(self):
        """정면 얼굴 등록 - 등록 플래그 설정"""
        try:
            # 등록 시작
            self.registration_in_progress = True
            logger.info("얼굴 등록 시작: 정면")

            # 카메라가 이미 열려있는지 확인, 없으면 초기화
            if not self.cap or not self.cap.isOpened():
                if not self._initialize_camera():
                    logger.error("정면 촬영 전 카메라 초기화 실패")
                    self.registration_in_progress = False
                    return False
                    
            # 사용자 ID 설정
            last_user_id = self.login_dao.get_last_user_id()
            self.user_id = int(last_user_id) + 1 if last_user_id is not None else 1
            logger.info(f"사용자 ID 설정: {self.user_id}")
            
            # 얼굴 캡처 및 저장
            max_tries = 3
            for attempt in range(max_tries):
                try:
                    face_vector = self.capture_face(release_camera=False)
                    if face_vector is not None:
                        # 딥 카피 사용하여 데이터 복사 문제 방지
                        vector_copy = face_vector.copy()
                        self.face_vectors["front"] = vector_copy.tolist()
                        collection = self.login_dao.get_face_collection()
                        data = [[vector_copy.tolist()], [str(self.user_id)], ["front"], [int(time.time())]]
                        collection.insert(data)
                        logger.info(f"USER ID {self.user_id} : 정면 얼굴 벡터 저장 완료")
                        return True
                    else:
                        if attempt < max_tries - 1:
                            logger.warning(f"정면 얼굴 촬영 실패, 재시도 ({attempt+1}/{max_tries})")
                            time.sleep(1)
                        else:
                            raise Exception("얼굴 정면 촬영 실패")
                except Exception as e:
                    if attempt < max_tries - 1:
                        logger.warning(f"오류 발생, 재시도 ({attempt+1}/{max_tries}): {e}")
                        time.sleep(1)
                    else:
                        logger.error(f"정면 얼굴 등록 실패: {e}")
                        self.release_camera()
                        self.registration_in_progress = False  # 실패 시 등록 플래그 해제
                        return False
            # 모든 시도 실패
            self.release_camera()
            self.registration_in_progress = False
            return False
            
        except Exception as e:
            logger.error(f"정면 얼굴 등록 실패: {e}")
            self.release_camera()  # 예외 발생시 카메라 자원 해제
            self.registration_in_progress = False
            return False

    # 좌측 얼굴 등록 함수 간소화
    def register_face_left(self):
        """좌측 얼굴 등록 - 최대한 간소화"""
        logger.info(f"USER ID {self.user_id} : 얼굴 좌측 촬영 시작")
        
        # 카메라 확인
        if not self.cap or not self.cap.isOpened():
            try:
                self._initialize_camera()
            except:
                logger.error("카메라 초기화 실패")
                return False
        
        # 단순화된 캡처 로직
        try:
            face_vector = None
            # 최대 3회 시도
            for i in range(3):
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.5)
                    continue
                    
                # 얼굴 감지
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.detector(gray, 0)
                
                if len(faces) > 0:
                    shape = self.predictor(gray, faces[0])
                    face_vector = np.array(self.face_rec_model.compute_face_descriptor(frame, shape))
                    break
                    
                time.sleep(0.5)
                
            # 얼굴 벡터 추출 실패
            if face_vector is None:
                logger.error("좌측 얼굴 벡터 추출 실패")
                return False
                
            # 벡터 저장
            self.face_vectors["left"] = face_vector.tolist()
            collection = self.login_dao.get_face_collection()
            data = [[face_vector.tolist()], [str(self.user_id)], ["left"], [int(time.time())]]
            collection.insert(data)
            logger.info(f"USER ID {self.user_id} : 좌측 얼굴 벡터 저장 완료")
            return True
            
        except Exception as e:
            logger.error(f"좌측 얼굴 등록 오류: {e}")
            return False

    # 우측 얼굴 등록 함수 간소화
    def register_face_right(self):
        """우측 얼굴 등록 - 최대한 간소화"""
        logger.info(f"USER ID {self.user_id} : 얼굴 우측 촬영 시작")
        
        # 카메라 확인
        if not self.cap or not self.cap.isOpened():
            try:
                self._initialize_camera()
            except:
                logger.error("카메라 초기화 실패")
                self.registration_in_progress = False
                return False
        
        # 단순화된 캡처 로직
        try:
            face_vector = None
            # 최대 3회 시도
            for i in range(3):
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.5)
                    continue
                    
                # 얼굴 감지
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.detector(gray, 0)
                
                if len(faces) > 0:
                    shape = self.predictor(gray, faces[0])
                    face_vector = np.array(self.face_rec_model.compute_face_descriptor(frame, shape))
                    break
                    
                time.sleep(0.5)
                
            # 얼굴 벡터 추출 실패
            if face_vector is None:
                logger.error("우측 얼굴 벡터 추출 실패")
                self.registration_in_progress = False
                return False
                
            # 벡터 저장
            self.face_vectors["right"] = face_vector.tolist()
            collection = self.login_dao.get_face_collection()
            data = [[face_vector.tolist()], [str(self.user_id)], ["right"], [int(time.time())]]
            collection.insert(data)
            logger.info(f"USER ID {self.user_id} : 우측 얼굴 벡터 저장 완료")
            
            # 최종 확인
            self.registration_in_progress = False
            if len(self.face_vectors) == 3:
                return self.user_id
            else:
                return False
            
        except Exception as e:
            logger.error(f"우측 얼굴 등록 오류: {e}")
            self.registration_in_progress = False
            return False

    
    def register_user(self, user_id):
        """사용자 등록"""
        try:
            result = self.login_dao.register_user(user_id)
            return bool(result)
        except Exception as e:
            logger.error(f"사용자 등록 실패: {e}")
            return False

    def delete_register_face(self, user_id):
        """사용자 얼굴 등록 취소"""
        try:
            for direction in ["front", "left", "right"]:
                file_path = os.path.join(TEMP_FACE_DIR, f"{user_id}_{direction}.npy")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"임시 파일 삭제: {file_path}")
            
            collection = self.login_dao.get_face_collection()
            expr = f'user_id == "{user_id}"'
            collection.delete(expr)
            self.face_vectors = {}
            logger.info(f"USER ID {user_id}의 등록 정보 삭제 완료")
        except Exception as e:
            logger.error(f"등록 정보 삭제 오류: {e}")
        finally:
            # 어떤 경우든 등록 플래그 해제
            self.registration_in_progress = False

    def profile_add(self, item):
        """프로필 추가"""
        try:
            result = self.login_dao.profile_add(item)
            return bool(result)
        except Exception as e:
            logger.error(f"프로필 추가 실패: {e}")
            return False
    
    def find_user(self, user_id):
        """사용자 조회"""
        try:
            result = self.login_dao.find_user(user_id)
            return result if result else False
        except Exception as e:
            logger.error(f"사용자 조회 실패: {e}")
            return False
    
    def manual_login(self, user_pwd):
        """수동 로그인"""
        try:
            result = self.login_dao.manual_login(user_pwd)
            return result if result else None
        except Exception as e:
            logger.error(f"수동 로그인 실패: {e}")
            return None