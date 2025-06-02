import numpy as np
import cv2
import os
import time
import dlib
import queue

import sys
import os

# 현재 파일의 상위 디렉토리(moca 폴더가 있는 디렉토리)를 시스템 경로에 추가
# 노트북에서는 __file__ 대신 현재 작업 디렉토리 사용
current_dir = os.getcwd()
parent_dir = os.path.dirname(current_dir)

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(parent_dir)

# 이제 moca 폴더의 파일을 직접 임포트할 수 있음
from moca.moca_validation import DepthValidator
from moca.utils import frame_to_rgb_frame

class AntiSpoofingService:
    def __init__(self):
        # 임계값 설정
        self.depth_threshold = 0.65  # 깊이 점수 임계값
        
        # 현재 프레임 저장 변수
        self.current_frame = None
        
        # 깊이 처리 객체 초기화 (한 번만 초기화)
        self.depth_validator = DepthValidator()
        
        # 폐이스 마스크 저장 디렉토리
        self.MASK_SAVE_DIR = "./face_mask_values"
        os.makedirs(self.MASK_SAVE_DIR, exist_ok=True)
        
        # dlib 모델 로드
        RECOGNITION_MODEL_PATH = "models/dlib_face_recognition_resnet_model_v1.dat"
        
        print(f"모델 경로 확인: {os.path.exists(RECOGNITION_MODEL_PATH)}")
        
        self.detector = dlib.get_frontal_face_detector()
        self.face_rec_model = dlib.face_recognition_model_v1(RECOGNITION_MODEL_PATH)
        
        self.pipeline = self.depth_validator.pipeline
        
    def start(self):
        """깊이 센서와 관련 서비스 시작"""
        self.depth_validator.start()
    
    def stop(self):
        """깊이 센서와 관련 서비스 중지"""
        self.depth_validator.stop()
    
    def update_frame(self, frame):
        """현재 프레임 업데이트"""
        self.current_frame = frame
    
    def check_real_face(self):
        """실시간 얼굴 스푸핑 감지"""
        try:
            print("얼굴 스푸핑 감지 시작...")
            
            # Orbbec 카메라에서 프레임 먼저 획득
            try:
                # 최대 2초 대기
                self.current_frame = self.depth_validator.color_image_queue.get(timeout=2)
                
                print("받은 프레임:" ,self.current_frame)
                
                if self.current_frame is None:
                    print("프레임이 없습니다.")
                    return False
                
            except queue.Empty:
                print("프레임 큐에서 이미지를 가져오지 못했습니다.")
                return False
            
            # 프레임이 없으면 바로 종료
            if self.current_frame is None:
                print("현재 프레임이 없습니다.")
                return False
            
            # 나머지 기존 로직 유지 (얼굴 마스크, 깊이 분석 등)
            face_mask = self._create_face_mask(self.current_frame)
            if face_mask is None:
                print("얼굴을 감지할 수 없습니다")
                return False

            
            # 2. 깊이 데이터 가져오기
            try:
                raw_depth = self.depth_validator.raw_depth_queue.get(timeout=2)
                predicted_depth = self.depth_validator.predicted_depth_queue.get(timeout=2)
                calibrated_depth_mm = self.depth_validator.calibrate_depth(raw_depth, predicted_depth)
                
                if calibrated_depth_mm is None:
                    print("깊이 데이터 보정 실패")
                    return False
                else:
                    print("보정된 깊이 데이터:", calibrated_depth_mm)
                    
            except Exception as e:
                print(f"깊이 데이터 처리 오류: {e}")
                return False
            
            # 3. 깊이 분석으로 진짜 얼굴인지 확인
            depth_variance = self._check_depth_variance(calibrated_depth_mm, face_mask)
            edge_score = self._check_depth_edges(calibrated_depth_mm, face_mask)
            profile_score = self._check_depth_profile(calibrated_depth_mm, face_mask)
            
            depth_score = 0.4 * depth_variance + 0.3 * edge_score + 0.3 * profile_score
            is_real_face = depth_score > self.depth_threshold
            
            
            print(f"안티 스푸핑 결과: {depth_score:.2f} (기준값: {self.depth_threshold}) 스푸핑여부 : {is_real_face}")
            return is_real_face
            
        finally:
            self.stop()
            
    def _create_face_mask(self, frame):
        """얼굴 영역 마스크 생성 (dlib 버전)"""
        if frame is None:
            return None

        # 그레이 스케일로 변환
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # dlib 얼굴 탐지기 초기화 (한 번만 로드)
        if not hasattr(self, '_dlib_detector'):
            self._dlib_detector = dlib.get_frontal_face_detector()

        # 얼굴 탐지
        faces = self._dlib_detector(gray, 0)

        if len(faces) == 0:
            return None

        # 가장 큰 얼굴 선택
        max_area = 0
        max_face = None
        for face in faces:
            x, y = face.left(), face.top()
            w, h = face.width(), face.height()
            if w * h > max_area:
                max_area = w * h
                max_face = (x, y, w, h)

        # 얼굴 마스크 생성
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        x, y, w, h = max_face
        mask[y:y+h, x:x+w] = 255

        return mask
    
    def _check_depth_variance(self, depth_map, face_mask):
        """얼굴 영역의 깊이 분산 확인 (실제 얼굴은 3D 구조로 분산이 큼)"""
        if depth_map is None or face_mask is None:
            return 0.0
        
        # 얼굴 영역만 추출
        masked_depth = cv2.bitwise_and(depth_map, depth_map, mask=face_mask)
        
        # 마스크 내 0이 아닌 값만 고려
        valid_depths = masked_depth[masked_depth > 0]
        
        if len(valid_depths) == 0:
            return 0.0
        
        # 분산 계산
        depth_std = np.std(valid_depths)
        depth_range = np.max(valid_depths) - np.min(valid_depths)
        
        # 분산이 너무 작으면 평면 (사진, 화면)
        # 분산이 적절하면 실제 얼굴
        normalized_std = min(1.0, depth_std / 50.0)  # 표준 편차 정규화
        normalized_range = min(1.0, depth_range / 200.0)  # 범위 정규화
        
        # 최종 점수 (0~1)
        variance_score = 0.6 * normalized_std + 0.4 * normalized_range
        
        return variance_score
    
    def _check_depth_edges(self, depth_map, face_mask):
        """깊이 맵에서 얼굴 경계의 선명도 확인 (실제 얼굴은 배경과 경계가 선명)"""
        if depth_map is None or face_mask is None:
            return 0.0
        
        # 얼굴 마스크 경계 추출
        face_contours, _ = cv2.findContours(face_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not face_contours:
            return 0.0
        
        # 경계 마스크 생성
        edge_mask = np.zeros_like(face_mask)
        cv2.drawContours(edge_mask, face_contours, -1, 255, 2)
        
        # 경계 주변 깊이 값 추출
        boundary_depth = cv2.bitwise_and(depth_map, depth_map, mask=edge_mask)
        
        # 경계 내부와 외부 깊이 대비 계산
        valid_boundary = boundary_depth[boundary_depth > 0]
        
        if len(valid_boundary) == 0:
            return 0.0
        
        # 경계 깊이 대비 계산
        edge_gradient = np.gradient(valid_boundary)
        edge_gradient_mag = np.abs(edge_gradient).mean()
        
        # 경계 선명도 점수 (0~1)
        edge_score = min(1.0, edge_gradient_mag / 50.0)
        
        return edge_score
    
    def _check_depth_profile(self, depth_map, face_mask):
        """얼굴 깊이 프로파일 확인 (실제 얼굴은 특정 깊이 패턴을 가짐)"""
        if depth_map is None or face_mask is None:
            return 0.0
        
        # 얼굴 영역만 추출
        masked_depth = cv2.bitwise_and(depth_map, depth_map, mask=face_mask)
        
        # 마스크 내 0이 아닌 값만 고려
        valid_depths = masked_depth[masked_depth > 0]
        
        if len(valid_depths) == 0:
            return 0.0
        
        # 깊이 히스토그램 분석
        hist, bins = np.histogram(valid_depths, bins=10, range=(0, 2000))
        normalized_hist = hist / np.sum(hist)
        
        # 실제 얼굴의 깊이 분포 특성 확인
        # 1. 연속적인 깊이 분포 (히스토그램의 연속성)
        continuity = 1.0 - np.std(normalized_hist) / np.mean(normalized_hist) if np.mean(normalized_hist) > 0 else 0.0
        continuity = max(0.0, min(1.0, continuity))
        
        # 2. 깊이 중앙값 확인 (적절한 거리에 얼굴이 있는지)
        median_depth = np.median(valid_depths)
        depth_score = 1.0 if 400 <= median_depth <= 1500 else max(0.0, 1.0 - abs(median_depth - 800) / 800)
        
        # 최종 프로파일 점수
        profile_score = 0.5 * continuity + 0.5 * depth_score
        
        return profile_score
    
    def check_real_face_from_vector(self, face_vector):
        """얼굴 벡터로부터 스푸핑 감지"""
        # 현재 프레임 기반 체크 (실제 구현에서는 벡터와 깊이 데이터 함께 분석)
        return self.check_real_face()
    
    def __del__(self):
        """소멸자: 리소스 해제"""
        try:
            self.stop()
        except:
            pass