import cv2
import dlib
import numpy as np
import threading
from imutils import face_utils
from PIL import ImageFont, ImageDraw, Image
from dao.monitoring_dao import MonitoringDAO
from fastapi.responses import StreamingResponse
from scipy.spatial import distance as dist

import time
import pygame
import os
import json

from config.websocket import get_manager



class MonitoringService:
    def __init__(self):
        self.running = False  # 모니터링 상태 (켜짐/꺼짐), 기본적으로 실행상태
        self.detector = dlib.get_frontal_face_detector()  # 얼굴 검출기
        self.status = False # 기본값
        self.monitoring_dao = MonitoringDAO
        self.cap = None  # OpenCV VideoCapture 객체
        self.thread = None  # 실행 중인 모니터링 스레드

        # 최적화용 수치
        self.frame_count = 0
        self.current_rects = []
        self.current_gray = None
        
        # self.predictor = dlib.shape_predictor("models/shape_predictor_68_face_landmarks.dat")  # 랜드마크 => 아래에서 호출 중 필요없음
                
        # ✅ 시선 이탈 감지 변수
        self.GAZE_COUNT = 0  
        self.LAST_GAZE_TIME = None  
        self.NORMAL_GAZE_TIME = 0 # 현재시간에서 값이 추가되는 것 같아서 0으로 수정
        self.GAZE_TIME_THRESH = 2  
        self.HEAD_ANGLE_THRESH_X = 0.08  
        self.HEAD_ANGLE_THRESH_Y = 0.1  
        self.RESET_TIME_THRESH = 60  # 1분 동안 정상 시선 유지 시 초기화

        self.BASE_HEAD_X = 0.0  # 기본값을 0으로 설정 
        self.BASE_HEAD_Y = 0.0  
        
                # 졸음 감지 관련 변수 추가
        self.EYE_CLOSED_TIME = 0  # 눈 감고 있는 누적 시간 (초)
        self.DROWSY_WARNING_ACTIVE = False  # 졸음 주의 상태 여부
        self.SLEEPY_WARNING_ACTIVE = False  # 졸음 경고 상태 여부
        self.LAST_DROWSY_TIME = None  # 마지막 졸음 상태 기록
        self.LAST_WARNING_TIME = None  # 마지막 경고 상태 기록
        
        # 졸음 감지 기준 변수 추가
        self.EYE_AR_THRESH = 0.20  # 눈 감은 상태 기준
        self.MOUTH_AR_THRESH = 0.75  # 하품 기준
        self.DROWSY_DISPLAY_TIME = 10  # 주의 상태 표시 시간
        self.WARNING_DISPLAY_TIME = 60  # 경고 상태 표시 시간 (1분간 유지)
        
        # 카운트 변수 추가
        self.EYE_COUNTER = 0  # 눈 감은 시간 카운트
        self.MOUTH_COUNTER = 0  # 하품 지속 카운트
        self.BLINK_COUNTER = 0  # 눈 깜빡임 횟수 (1분 내)
        self.YAWN_COUNTER = 0  # 하품 횟수 (1분 내)
        self.RESET_TIME = time.time()  # 1분 기준 초기화 시간
        self.LAST_YAWN_TIME = 0  # 마지막 하품 감지 시간 초기화

        # 졸음 텍스트 유지용
        self.text_display_state = None  # 'none', 'drowsy', 'sleepy' 중 하나의 상태만 유지
        self.text_state_change_time = 0  # 상태 변경 시간
        
        # 졸음 감지 상태 관리 변수 추가
        self.DROWSY_WARNING_ACTIVE = False
        self.SLEEPY_WARNING_ACTIVE = False
        self.LAST_DROWSY_TIME = None
        self.LAST_WARNING_TIME = None
        
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

        try:
            # 모델 파일의 절대 경로 확인 (디버깅용)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_dir, "..", "models", "shape_predictor_68_face_landmarks.dat")
            model_path = os.path.abspath(model_path)
            
            print(f"📂 모델 파일 절대 경로: {model_path}")
            print(f"📂 모델 파일 존재 여부: {os.path.exists(model_path)}")
            
            if os.path.exists(model_path):
                self.predictor = dlib.shape_predictor(model_path)
                print(f"✅ dlib 모델 로드 성공")
            else:
                print(f"⚠️ 모델 파일이 없어 기능이 제한됩니다: {model_path}")
                self.predictor = None  # 모델이 없어도 서버는 동작
        except Exception as e:
            print(f"⚠️ 모델 로드 중 오류 발생: {e}")
            self.predictor = None
                    
            

    async def broadcast_status(self):
        """현재 모니터링 상태를 WebSocket으로 브로드캐스트"""
        try:
            manager = get_manager()
            status_data = {
                # 시선 이탈과 졸음 상태 분리
                "distraction_state": self.get_distraction_status(),
                "drowsiness_state": self.get_drowsiness_status(),
            }
            await manager.broadcast(json.dumps(status_data))
        except Exception as e:
            print(f"상태 브로드캐스트 오류: {e}")
        
    def put_text_korean(self, img, text, pos, color=(0, 0, 255)):
        """한글 텍스트를 화면에 출력하는 함수"""
        img_pil = Image.fromarray(img)
        draw = ImageDraw.Draw(img_pil)
        draw.text(pos, text, font=self.font, fill=color)
        return np.array(img_pil)
        
    def get_monitoring_status(self):
        # return self.monitoring_dao.get_status # 현재 상태 반환
        return self.status
    
    def toggle_monitoring(self):
        """모니터링 상태 ON/OFF 전환 및 OpenCV 실행/종료"""
        # toggle 누르면 기존에 "on"/"off"에서 True/False로 변경
        # try / except로 오류 탐지 더 강화
        # threading을 유연하게 변경
        try:
            if self.status == False:
                # 비동기적으로 시작 => 쓰레드 설정
                threading.Thread(target=self.start_monitoring, daemon=True).start()
                self.status = True
                print("✅ [Monitoring] 모니터링 시작 요청!")
            else:
                # running 플래그만 변경하고 즉시 반환
                self.running = False
                self.status = False
                print("⛔ [Monitoring] 모니터링 종료 요청!")
                
            return {"message": f"Monitoring status changed to {self.status}", "status": self.status}
        except Exception as e:
            print(f"❌ 토글 처리 중 오류: {e}")
            return {"message": f"Error: {str(e)}", "status": self.status}

    def find_camera(self):
        """사용 가능한 카메라를 자동으로 찾는 함수"""
        for index in range(10):  # 0부터 9까지 카메라 인덱스 확인
            temp_cap = cv2.VideoCapture(index)
            if temp_cap.isOpened():
                temp_cap.release()  # 테스트 후 즉시 해제
                print(f"✅ 사용 가능한 카메라 발견: 인덱스 {index}")
                return index
        
        print("❌ 사용 가능한 카메라를 찾을 수 없습니다")
        return None

    def start_monitoring(self):
        """모니터링 시작 (OpenCV 실행)"""
        if not self.running:
            self.running = True
            
            # 이전 카메라가 있으면 해제
            if self.cap is not None:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
                time.sleep(0.5)  # 잠시 대기
            
            # 사용 가능한 카메라 찾기
            camera_index = self.find_camera()
            
            if camera_index is not None:
                try:
                    self.cap = cv2.VideoCapture(camera_index)
                    
                    if not self.cap.isOpened():
                        print(f"❌ 카메라 {camera_index}를 열 수 없습니다")
                        self.running = False
                        self.status = False
                        return
                    
                    print(f"✅ 카메라 {camera_index} 시작됨")
                except Exception as e:
                    print(f"❌ 카메라 초기화 오류: {e}")
                    self.running = False
                    self.status = False
                    return
            else:
                print("❌ 카메라를 찾을 수 없어 모니터링을 시작할 수 없습니다")
                self.running = False
                self.status = False
                return
            
            # 스레드 시작 부분은 기존과 동일
            if self.thread and self.thread.is_alive():
                try:
                    self.thread.join(timeout=0.5)
                except:
                    pass
                    
            self.thread = threading.Thread(target=self.run_monitoring, daemon=True)
            self.thread.start()


    # 중지코드 변경 => 카메라 객체가 살아서 다음 실행 될 때 안되는 버그 발생
    # thread 해제 안정화 코드 추가 (맨위 if문)
    def stop_monitoring(self):
        """ 모니터링 종료 - 카메라 자원 완전히 해제 """
        self.running = False
        
        # 스레드가 끝날 때까지 약간 대기 (블로킹 방지)
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=0.5)  # 최대 0.5초만 대기
            except:
                pass

        # 카메라 객체 정리
        if self.cap:
            print("📷 카메라 자원 해제 중...")
            # 윈도우 닫기
            cv2.destroyAllWindows()
            # 비디오 캡처 해제 시도
            try:
                self.cap.release()
            except Exception as e:
                print(f"⚠️ 카메라 해제 중 오류: {e}")
            finally:
                self.cap = None

            # 추가 정리 (꺼지면 초기화 되야하는 것들)
            self.LAST_GAZE_TIME = None
            self.NORMAL_GAZE_TIME = 0
            self.BASE_HEAD_X = 0.0
            self.BASE_HEAD_Y = 0.0
            self.frame_count = 0
            self.current_gray = None
            self.current_rects = []
            
                
        print("✅ 모니터링이 완전히 종료되었습니다.")

    def run_monitoring(self):
        # """OpenCV를 사용해 영상 캡처"""
        # while self.running:
        #     ret, frame = self.cap.read()
        #     if not ret:
        #         break
        #     time.sleep(0.03)  # 너무 빠르게 루프 돌지 않도록 추가
        # self.cap.release()
        # print("📌 [Monitoring] OpenCV 프로세스 종료")
        #     def run_monitoring(self):
        """OpenCV 실행 (Jupyter 감지 로직 호출)"""
        # self.cap = cv2.VideoCapture(0) # start에서 호출 중이라 카메라가 중복호출로 에러 발생
        
        self.show_cv_window = False

        while self.running:
            if self.cap is None:
                break

            ret, frame = self.cap.read()
            if not ret:
                print("⚠️ [Monitoring] 웹캠에서 프레임을 가져오지 못했습니다!")
                break

            # ✅ Jupyter에서 만든 감지 함수 사용
            # frame = self.detect_distraction(frame)  # detect_distraction 함수 호출

            # OpenCV 창 표시 (옵션)
            # 모니터링 실행 됐을 때 창 뜨는것 방지
            if self.show_cv_window:
                cv2.imshow("Monitoring", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):  # 'q'를 누르면 종료
                    break
            
            else:
                time.sleep(0)  # 30초 대기

        self.stop_monitoring()
        if self.show_cv_window:
            cv2.destroyAllWindows()



    # 맨 위에 카메라 초기화 되지 않았을 경우 초기화 코드 추가
    def generate_frames(self):
        """웹캠 프레임을 지속적으로 생성하는 제너레이터"""

        # 카메라가 초기화되지 않았거나 열려있지 않으면 초기화
        if self.cap is None or not self.cap.isOpened():
            try:
                # 기존 카메라 객체 정리
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                    time.sleep(0.5)  # 잠시 대기
                    
                # 새 카메라 객체 생성
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    yield self._error_frame("카메라를 열 수 없습니다")
                    return
            except Exception as e:
                yield self._error_frame(f"카메라 초기화 오류: {str(e)}")
                return


        # while문을 video탐지와 video오픈 및 모니터링 러닝까지 다 될경우 실행
        while self.running and self.cap and self.cap.isOpened():
            # try / except로 예외처리 추가
            try:
                success, frame = self.cap.read()
                if not success:
                    yield self._error_frame("프레임을 가져올 수 없습니다")
                    continue
                    
                # 주의 분산 감지 로직 적용
                detected_frame = self.detect_distraction(frame)
                    
                # 졸음 감지
                detected_frame = self.detect_drowsiness(detected_frame)

                if detected_frame is None:
                    detected_frame = frame

                # 프레임을 JPG로 변환
                _, buffer = cv2.imencode(".jpg", detected_frame)
                frame_bytes = buffer.tobytes()
                
                yield (b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
                    
                    
            except Exception as e:
                print(f"❌ [Streaming] 프레임 처리 중 오류 발생: {e}")
                yield self._error_frame(f"오류: {str(e)}")

    # 오류 메시지 표시용 헬퍼 함수 추가
    def _error_frame(self, error_message):
        """오류 메시지가 포함된 프레임 생성"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)  # 검은 프레임 생성
        print("에러 메세지:", error_message)
        cv2.putText(frame, error_message, (50, 240), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        _, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()
        return (b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        
    def eye_aspect_ratio(self, eye):
        """눈의 EAR(눈 감김 비율) 계산"""
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])
        C = dist.euclidean(eye[0], eye[3])
        return (A + B) / (2.0 * C)

    def mouth_aspect_ratio(self, mouth):
        """입의 MAR(입 벌림 비율) 계산"""
        A = dist.euclidean(mouth[2], mouth[10])
        B = dist.euclidean(mouth[4], mouth[8])
        C = dist.euclidean(mouth[0], mouth[6])
        return (A + B) / (2.0 * C)

    def detect_drowsiness(self, frame):
            """
            졸음 감지 메서드 - 눈 감김과 하품을 기반으로 졸음 상태를 감지
            """
            # 전체 함수를 try-except로 감싸서 어떤 예외가 발생해도 프레임 반환
            try:
                
                # 상태 변수가 없는 경우 초기화
                if not hasattr(self, 'DROWSY_WARNING_ACTIVE'):
                    self.DROWSY_WARNING_ACTIVE = False
                if not hasattr(self, 'SLEEPY_WARNING_ACTIVE'):
                    self.SLEEPY_WARNING_ACTIVE = False
                
                # 현재 시간 기록 (여러 타이머에 사용)
                current_time = time.time()
                
                # 그레이스케일로 변환 (얼굴 탐지에 필요)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # 얼굴 탐지 실행
                rects, _, _ = self.detector.run(gray, 0, 0)
                
                # 얼굴 처리 로직
                if len(rects) > 0:  # 얼굴이 감지된 경우에만 처리
                    for rect in rects:
                        try:
                            # 얼굴 랜드마크 추출
                            shape = self.predictor(gray, rect)
                            shape = face_utils.shape_to_np(shape)

                            # ✅ 얼굴 바운딩 박스 및 랜드마크 표시
                            (x, y, w, h) = face_utils.rect_to_bb(rect)  
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            for (px, py) in shape:
                                cv2.circle(frame, (px, py), 1, (0, 255, 255), -1)
                                    
                            # 눈 및 입 영역 설정
                            leftEye = shape[42:48]  # 오른쪽 눈
                            rightEye = shape[36:42]  # 왼쪽 눈
                            mouth = shape[48:68]  # 입 영역

                            # EAR(눈 감김 비율) & MAR(입 벌림 비율) 계산
                            leftEAR = self.eye_aspect_ratio(leftEye)
                            rightEAR = self.eye_aspect_ratio(rightEye)
                            ear = (leftEAR + rightEAR) / 2.0
                            mar = self.mouth_aspect_ratio(mouth)

                            # 1분마다 눈 깜빡임과 하품 카운트 초기화
                            if current_time - self.RESET_TIME >= 60:
                                self.BLINK_COUNTER = 0
                                self.YAWN_COUNTER = 0
                                self.RESET_TIME = current_time
                                print("✅ 1분 경과: 눈 깜빡임/하품 카운트 초기화")

                            # ===== 눈 감김 상태 처리 =====
                            if ear < self.EYE_AR_THRESH:
                                # 눈 감은 시간 누적
                                self.EYE_CLOSED_TIME += 1/30  # 30FPS 가정
                                
                                # 1단계: 졸음 주의 (참조 코드와 동일한 조건 사용)
                                if (self.BLINK_COUNTER <= 12 or self.BLINK_COUNTER >= 22 or self.YAWN_COUNTER >= 2) \
                                and self.EYE_CLOSED_TIME >= 1 \
                                and not self.SLEEPY_WARNING_ACTIVE:  # 경고 상태가 아닐 때만
                                    if not self.DROWSY_WARNING_ACTIVE:
                                        self.DROWSY_WARNING_ACTIVE = True
                                        self.LAST_DROWSY_TIME = current_time
                                        print("⚠️ 졸음 주의!")
                                
                                # 2단계: 졸음 경고 (참조 코드와 동일한 조건 사용)
                                if (self.BLINK_COUNTER <= 10 or self.BLINK_COUNTER >= 24 or self.YAWN_COUNTER >= 3) \
                                and self.EYE_CLOSED_TIME >= 2:
                                    if not self.SLEEPY_WARNING_ACTIVE:
                                        self.SLEEPY_WARNING_ACTIVE = True
                                        self.LAST_WARNING_TIME = current_time
                                        # pygame.mixer.music.play()
                                        print("🚨 졸음 경고! 운전 중지!")
                            
                            else:
                                # 눈을 뜬 상태에서 상태 유지 시간 확인 (참조 코드와 유사하게 구현)
                                
                                # 졸음 주의 유지 (3초)
                                if self.DROWSY_WARNING_ACTIVE:
                                    elapsed_drowsy = current_time - self.LAST_DROWSY_TIME
                                    if elapsed_drowsy >= self.DROWSY_DISPLAY_TIME:
                                        self.DROWSY_WARNING_ACTIVE = False
                                        self.LAST_DROWSY_TIME = None
                                
                                # 졸음 경고 유지 (60초)
                                if self.SLEEPY_WARNING_ACTIVE:
                                    elapsed_warning = current_time - self.LAST_WARNING_TIME
                                    if elapsed_warning >= self.WARNING_DISPLAY_TIME:
                                        self.SLEEPY_WARNING_ACTIVE = False
                                        self.LAST_WARNING_TIME = None
                                        self.EYE_CLOSED_TIME = 0
                                
                                # 경고 상태가 아닐 때만 EYE_CLOSED_TIME 초기화
                                if not self.SLEEPY_WARNING_ACTIVE:
                                    self.EYE_CLOSED_TIME = 0
                            
                            # ===== 하품 감지 =====
                            if mar > self.MOUTH_AR_THRESH:
                                self.MOUTH_COUNTER += 1
                                if self.MOUTH_COUNTER >= 30 and (current_time - self.LAST_YAWN_TIME > 1):
                                    self.YAWN_COUNTER += 1
                                    # 하품 감지 시 알림 (하지만 화면 출력은 루프 밖에서 처리)
                                    print(f"😴 하품 감지됨! (총 {self.YAWN_COUNTER}회)")
                                    self.LAST_YAWN_TIME = current_time
                                    self.MOUTH_COUNTER = 0
                            else:
                                self.MOUTH_COUNTER = 0

                            # ===== 눈 깜빡임 감지 =====
                            if ear < self.EYE_AR_THRESH:
                                self.EYE_COUNTER += 1
                            else:
                                if self.EYE_COUNTER > 0:
                                    self.BLINK_COUNTER += 1
                                self.EYE_COUNTER = 0

                        except Exception as e:
                            print(f"❌ 눈/입 측정 중 오류 발생: {e}")
                            continue
            
                # ===== 텍스트 표시 부분 (for 루프 바깥) =====
                # 중요: 얼굴 인식 여부와 상관없이 상태 변수에 따라 텍스트 표시
                # 이렇게 하면 얼굴 인식이 불안정해도 텍스트가 깜빡이지 않음

                if len(rects) > 0 :
                    # 졸음 경고 텍스트 (상태에 따라 표시)
                    if self.SLEEPY_WARNING_ACTIVE:
                        frame = self.put_text_korean(frame, "🚨 졸음 경고! 운전 중지!", (10, 220), (0, 0, 255))
                    elif self.DROWSY_WARNING_ACTIVE:
                        frame = self.put_text_korean(frame, "⚠️ 졸음 주의!", (10, 200), (0, 255, 255))
                        
                    # 하품 표시는 시간 기반으로 표시 (최근 3초간만 표시)
                    if current_time - self.LAST_YAWN_TIME < 3:
                        frame = self.put_text_korean(frame, f"하품 감지됨! (총 {self.YAWN_COUNTER}회)", (10, 260), (0, 0, 255))
                        
                    # 항상 표시할 정보 (깜빡임 없이 표시)
                    display_text = f"눈 깜빡임: {self.BLINK_COUNTER}회 | 하품: {self.YAWN_COUNTER}회"
                    frame = self.put_text_korean(frame, display_text, (10, 160), (255, 120, 0))
                        
                # 항상 프레임 반환
                return frame

            except Exception as e:
                print(f"❌ 졸음 감지 메서드 전체 오류: {e}")
                return frame  # 어떤 경우에도 원본 프레임 반환
            
    # try / except 넣어서 버그등 예외상황 탐지하게 수정정        
    def detect_distraction(self, frame):
        """주의 분산 감지"""
        try:
            self.frame_count += 1

            # 실시간 탐지가 안되서 15프레임당 탐지되게끔 설정 => 조금 버벅임
            if self.frame_count % 15 == 0:
                self.current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # run(img, 업샘플링 => 얼굴 여러개 탐지 1로 갈수록 더많이 탐지, 민감도 -1로 갈수록 유연 1로 갈수록 탐지가 잘 안됨)
                rects, _, _  = self.detector.run(self.current_gray, 0, 0) # 임계값(0) 수정 => 비정상 탐지 너무 많음
                self.current_rects = rects
            

            if len(self.current_rects) == 0:
                self.IS_NORMAL_GAZE = False
                self.NORMAL_GAZE_TIME = time.time()  # 정상 시선 타이머 리셋
                frame = self.put_text_korean(frame, "⚠️ 얼굴 감지 안됨", (10, 110), (0, 0, 255))

            # 이곳도 try except문 추가해서 버그 탐지 및 서버 리셋 막기 
            for (i, rect) in enumerate(self.current_rects):
                try:
                    (x, y, w, h) = face_utils.rect_to_bb(rect)  

                    shape = self.predictor(self.current_gray, rect)
                    shape = face_utils.shape_to_np(shape)

                    # ✅ 머리 기울기 계산 (정규화된 값)
                    head_x = (np.mean(shape[36:42][:, 0]) - np.mean(shape[42:48][:, 0])) / w  
                    head_y = (np.mean(shape[19:27][:, 1]) - np.mean(shape[0:17][:, 1])) / h  

                    # ✅ 기준값 설정 (한 번만 저장)
                    if self.BASE_HEAD_X == 0.0 or self.BASE_HEAD_Y == 0.0:
                        self.BASE_HEAD_X = head_x
                        self.BASE_HEAD_Y = head_y

                    # ✅ 시선 이탈 감지
                    delta_x = abs(head_x - self.BASE_HEAD_X)
                    delta_y = abs(head_y - self.BASE_HEAD_Y)
                    
                    # 🚀 **(수정) 시선 이탈이 2초 지속되었을 때만 카운트 증가**
                    if delta_x > self.HEAD_ANGLE_THRESH_X or delta_y > self.HEAD_ANGLE_THRESH_Y:
                        if self.LAST_GAZE_TIME is None:  # 시선 이탈 시작 시간 기록
                            self.LAST_GAZE_TIME = time.time()

                        elapsed_time = time.time() - self.LAST_GAZE_TIME

                        if elapsed_time >= self.GAZE_TIME_THRESH:  # 🚨 **이탈이 2초 지속되었을 때만 증가**
                            self.GAZE_COUNT += 1  # 🚨 시선 이탈 횟수 증가
                            self.LAST_GAZE_TIME = None  # 초기화하여 중복 감지 방지
                            self.NORMAL_GAZE_TIME = time.time()  # ✅ **이탈 후 정상 시선 유지 시간 초기화**
                    else:
                        self.LAST_GAZE_TIME = None  # 기준 이하로 돌아오면 리셋

                    # ✅ 정상 시선 유지 시간 표시
                    normal_time = int(time.time() - self.NORMAL_GAZE_TIME)
                    normal_text = f"정상 시선 유지: {normal_time}초/{self.RESET_TIME_THRESH}초"
                    frame = self.put_text_korean(frame, normal_text, (10, 70), (0, 255, 0))

                    # ✅ 주의 단계 & 경고 단계 표시
                    if self.GAZE_COUNT >= 5:
                        frame = self.put_text_korean(frame, "🚨 운전 집중 경고!", (10, 120), (0, 0, 255))
                        # pygame.mixer.music.play()
                    elif self.GAZE_COUNT >= 2:
                        frame = self.put_text_korean(frame, "⚠️ 전방 주시 주의!", (10, 120), (0, 255, 255))
                        # pygame.mixer.music.play()

                    # ✅ 시선 이탈 횟수 화면 표시 (흰색)
                    gaze_text = f"시선 이탈 횟수: {self.GAZE_COUNT}회"
                    frame = self.put_text_korean(frame, gaze_text, (10, 30), (255, 120, 0))

                except Exception as e:
                    print(f"⚠️ 얼굴 랜드마크 처리 중 오류: {e}")
                    continue  # 이 얼굴 건너뛰고 다음 얼굴 처리

            # 🚀 **(추가) 전방 주시 1분간 유지 시 초기화**
            if (time.time() - self.NORMAL_GAZE_TIME) >= self.RESET_TIME_THRESH:
                print("🕒 1분간 정상 시선 유지: 시선 이탈 횟수 초기화")
                self.GAZE_COUNT = 0
                self.NORMAL_GAZE_TIME = time.time()  # 타이머 리셋

            return frame

        except Exception as e:
            print(f"❌ 주의 분산 감지 중 심각한 오류 발생: {e}")
            # 오류 발생 시 기본 프레임에 오류 메시지 표시 후 반환
            try:
                height, width = frame.shape[:2]
                cv2.putText(frame, f"Error: {str(e)}", (10, height//2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            except:
                # 프레임 처리도 안 되는 경우 빈 프레임 생성
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                
            return frame
        
    # 시선 이탈 상태만 확인
    def get_distraction_status(self):
        if self.GAZE_COUNT >= 5:
            return "danger"
        elif self.GAZE_COUNT >= 2:
            return "warn"
        else:
            return "normal"

    # 졸음 상태만 확인
    def get_drowsiness_status(self):
        if self.DROWSY_WARNING_ACTIVE:
            return "danger"
        elif self.SLEEPY_WARNING_ACTIVE:
            return "warn"
        else:
            return "normal"
# def detect_distraction(self, frame):
#     print("🧐 [DEBUG] 주의 분산 감지 함수 실행됨")  # ✅ 디버깅 로그 추가
#     ...




