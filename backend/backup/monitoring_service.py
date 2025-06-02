import cv2
import dlib
import numpy as np
import threading
from imutils import face_utils
from PIL import ImageFont, ImageDraw, Image
from dao.monitoring_dao import MonitoringDAO
from fastapi.responses import StreamingResponse
import time
import pygame
import os

class MonitoringService:
    def __init__(self):
        self.running = False  # 모니터링 상태 (켜짐/꺼짐), 기본적으로 실행상태
        self.detector = dlib.get_frontal_face_detector()  # 얼굴 검출기
        self.status = False # 기본값
        self.monitoring_dao = MonitoringDAO
        self.cap = None  # OpenCV VideoCapture 객체
        self.thread = None  # 실행 중인 모니터링 스레드
        self.predictor = dlib.shape_predictor("models/shape_predictor_68_face_landmarks.dat")  # 랜드마크
                
        # ✅ 시선 이탈 감지 변수
        self.GAZE_COUNT = 0  
        self.LAST_GAZE_TIME = None  
        self.NORMAL_GAZE_TIME = time.time()  
        self.GAZE_TIME_THRESH = 2  
        self.HEAD_ANGLE_THRESH_X = 0.08  
        self.HEAD_ANGLE_THRESH_Y = 0.1  

        self.BASE_HEAD_X = None  
        self.BASE_HEAD_Y = None  
        
        # ✅ 한글 폰트 설정
        font_path = "C:/Windows/Fonts/malgun.ttf"
        self.font = ImageFont.truetype(font_path, 30)
        
        # ✅ 경고음 설정
        pygame.mixer.init()
        self.ALERT_SOUND = "alert.mp3"
        try:
            pygame.mixer.music.load(self.ALERT_SOUND)
        except pygame.error:
            print("⚠️ 경고음 파일을 찾을 수 없습니다.")
            
        # ✅ 모델 파일의 절대 경로 설정
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 파일이 위치한 디렉토리
        # 모델 파일 경로 설정
        model_dir = os.path.join(base_dir, "..", "models")
        # 현재 스크립트의 디렉토리 기준으로 절대 경로 설정
        model_path = os.path.join(model_dir, "../models/shape_predictor_68_face_landmarks.dat")

        # ✅ dlib 랜드마크 모델 로드
        if os.path.exists(model_path):
            print(f"✅ dlib 모델 로드 성공: {model_path}")
            self.predictor = dlib.shape_predictor(model_path)
        else:
            raise FileNotFoundError(f"❌ dlib 모델 파일을 찾을 수 없습니다: {model_path}")
            
        print(f"📂 현재 실행 중인 디렉토리: {base_dir}")
        print(f"📂 모델 파일 예상 경로: {model_path}")
        print(f"📂 모델 파일 존재 여부: {os.path.exists(model_path)}")
            
            

    def put_text_korean(self, img, text, pos, color=(0, 0, 255)):
        """한글 텍스트를 화면에 출력하는 함수"""
        img_pil = Image.fromarray(img)
        draw = ImageDraw.Draw(img_pil)
        draw.text(pos, text, font=self.font, fill=color)
        return np.array(img_pil)
        
    def get_monitoring_status(self):
        # return self.monitoring_dao.get_status # 현재 상태 반환
        # not 제거 status 주소 반환값을 결정하는 함수라서 반대값을 보내면 안됨
        return self.status
    
    def toggle_monitoring(self):
        """모니터링 상태 ON/OFF 전환 및 OpenCV 실행/종료"""
        # 모니터링 초기값 변경에 따른 "on"/"off" => True/False 로 변경
        if self.status == False:
            self.start_monitoring()  # ✅ OpenCSV 실행
            self.status = True
            print("✅ [Monitoring] 모니터링 시작!")  # ✅ 로그 추가

        else:
            self.stop_monitoring()   # ✅ OpenCV 종료
            self.status = False
            print("⛔ [Monitoring] 모니터링 종료!")  # ✅ 로그 추가


        return self.status  # ✅ 변경된 상태 반환

    def start_monitoring(self):
        """ 모니터링 시작 (OpenCV 실행) """
        if not self.running:
            self.running = True
            self.cap = cv2.VideoCapture(0) # 웹캡
            self.monitoring_dao = MonitoringDAO()
            self.thread = threading.Thread(target=self.run_monitoring, daemon=True)
            self.thread.start()

    def stop_monitoring(self):
        """ 모니터링 종료 """
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def run_monitoring(self):
        """OpenCV 실행 (단순 카메라 영상 표시)"""
        while self.running:
            if self.cap is None:
                break

            ret, frame = self.cap.read()
            if not ret:
                print("⚠️ [Monitoring] 웹캠에서 프레임을 가져오지 못했습니다!")
                break

            # 프레임 그대로 표시 (주의 분산 감지 없음)
            cv2.imshow("Monitoring", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):  # 'q'를 누르면 종료
                break

        self.stop_monitoring()
        cv2.destroyAllWindows()

    # frame생성 함수 바꿈
    def generate_frames(self):
        """웹캠 프레임을 지속적으로 생성하는 제너레이터 (FastAPI 스트리밍용)"""
        # 카메라가 없으면 시작
        if self.cap is None or not self.cap.isOpened():
            print("카메라를 초기화합니다...")
            self.cap = cv2.VideoCapture(0)  # 인덱스 0 시도
            
            # 카메라가 여전히 열리지 않으면 인덱스 1 시도
            if not self.cap.isOpened():
                print("인덱스 0의 카메라를 열 수 없습니다. 인덱스 1을 시도합니다.")
                self.cap = cv2.VideoCapture(1)
        
        # 카메라가 여전히 열리지 않으면 오류 이미지 반환
        if not self.cap.isOpened():
            print("❌ 카메라를 열 수 없습니다!")
            # 오류 이미지 생성 (빨간색 배경)
            error_img = np.zeros((480, 640, 3), dtype=np.uint8)
            error_img[:] = (0, 0, 255)  # BGR, 빨간색
            cv2.putText(error_img, "Camera Error", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # 오류 이미지를 한 번 반환
            _, buffer = cv2.imencode('.jpg', error_img)
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            return
            
        print("✅ 카메라가 열렸습니다. 프레임 스트리밍을 시작합니다.")
        
        while self.running:
            try:
                success, frame = self.cap.read()
                if not success:
                    print("⚠️ 프레임을 읽을 수 없습니다.")
                    time.sleep(0.1)
                    continue
                
                # 프레임을 그대로 인코딩하여 전송 (주의 분산 감지 처리 없음)
                _, buffer = cv2.imencode(".jpg", frame)
                frame_bytes = buffer.tobytes()
                
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
                
                # 너무 빠르게 실행되지 않도록 
                time.sleep(0.03)
                
            except Exception as e:
                print(f"⚠️ 스트리밍 중 오류 발생: {e}")
                break
                
            
    def detect_distraction(self, frame):
        """주의 분산 감지"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray)

        for face in faces:
            shape = self.predictor(gray, face)
            shape = face_utils.shape_to_np(shape)

            # ✅ 머리 기울기 계산
            head_x = (np.mean(shape[36:42][:, 0]) - np.mean(shape[42:48][:, 0])) / (face.right() - face.left())
            head_y = (np.mean(shape[19:27][:, 1]) - np.mean(shape[0:17][:, 1])) / (face.bottom() - face.top())

            # ✅ 기준값 설정 (초기화)
            if self.BASE_HEAD_X is None or self.BASE_HEAD_Y is None:
                self.BASE_HEAD_X = head_x
                self.BASE_HEAD_Y = head_y

            # ✅ 시선 이탈 감지 로직
            delta_x = abs(head_x - self.BASE_HEAD_X)
            delta_y = abs(head_y - self.BASE_HEAD_Y)

            if delta_x > self.HEAD_ANGLE_THRESH_X or delta_y > self.HEAD_ANGLE_THRESH_Y:
                if self.LAST_GAZE_TIME is None:
                    self.LAST_GAZE_TIME = time.time()

                elapsed_time = time.time() - self.LAST_GAZE_TIME
                if elapsed_time >= self.GAZE_TIME_THRESH:
                    self.GAZE_COUNT += 1  
                    self.LAST_GAZE_TIME = None  

                    # 🚨 경고 표시
                    if self.GAZE_COUNT >= 5:
                        frame = self.put_text_korean(frame, "🚨 운전 집중 경고!", (10, 150), (0, 0, 255))
                        pygame.mixer.music.play()
                    elif self.GAZE_COUNT >= 2:
                        frame = self.put_text_korean(frame, "⚠️ 전방 주시 주의!", (10, 150), (0, 255, 255))
                        pygame.mixer.music.play()
            else:
                self.LAST_GAZE_TIME = None

        return frame
    
# def detect_distraction(self, frame):
#     print("🧐 [DEBUG] 주의 분산 감지 함수 실행됨")  # ✅ 디버깅 로그 추가
#     ...
