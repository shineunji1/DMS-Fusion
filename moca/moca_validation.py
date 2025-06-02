import os
import time
import cv2
import numpy as np
import threading
import queue

# 기존 임포트 유지
from .moca_depth_metric import DepthSensor
from .moca_mde_metric import DepthMetricPredictor
from orbbec_code.pyorbbecsdk import Config, OBError, OBSensorType, OBFormat, Pipeline, FrameSet, VideoStreamProfile
from .utils import frame_to_bgr_image

# 저장 디렉토리 설정
VALIDATION_SAVE_DIR = r'\moca_validation_values'
os.makedirs(VALIDATION_SAVE_DIR, exist_ok=True)

class DepthValidator:
    def __init__(self):
        # Pipeline 초기화
        self.pipeline = Pipeline()
        
        # 두 센서 초기화
        self.depth_sensor = DepthSensor()
        self.depth_predictor = DepthMetricPredictor(pipeline=self.pipeline)
        
        self.running = False
        
        # 보정 파라미터
        self.scale_factor = 1000.0  # m -> mm 단위 변환
        self.calibration_factor = 1.0  # 단일 보정 계수
        
        # 최신 깊이 값 저장용 변수
        self.latest_raw_depth_mm = None
        self.latest_predicted_depth_m = None
        self.latest_calibrated_depth_mm = None
        self.latest_color_image = None
        
        # 스레드 간 데이터 공유를 위한 큐
        self.raw_depth_queue = queue.Queue(maxsize=2)
        self.predicted_depth_queue = queue.Queue(maxsize=2)
        self.color_image_queue = queue.Queue(maxsize=2)
        
        # 스레드 객체
        self.depth_thread = None
        self.prediction_thread = None
        self.color_thread = None

        self.frame_timeout = 200  # 타임아웃을 200ms로 증가
        
    def start(self):
        """모든 센서와 스레드를 시작"""
        self.depth_sensor.start()
        self.depth_predictor.start()
        
        # RGB 스트림 설정
        config = Config()
        try:
            profile_list = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
            try:
                color_profile: VideoStreamProfile = profile_list.get_video_stream_profile(640, 0, OBFormat.RGB, 30)
            except OBError:
                color_profile = profile_list.get_default_video_stream_profile()
            config.enable_stream(color_profile)
        except Exception as e:
            print(f"RGB 스트림 설정 실패: {e}")
            pass
        
        self.pipeline.start(config)
        self.running = True
        
        # 스레드 시작
        self.depth_thread = threading.Thread(target=self._depth_worker)
        self.prediction_thread = threading.Thread(target=self._prediction_worker)
        self.color_thread = threading.Thread(target=self._color_worker)
        
        self.depth_thread.daemon = True
        self.prediction_thread.daemon = True
        self.color_thread.daemon = True
        
        self.depth_thread.start()
        self.prediction_thread.start()
        self.color_thread.start()
        
    def stop(self):
        """모든 센서와 스레드를 종료"""
        self.running = False
        
        # 스레드 종료 대기
        if self.depth_thread and self.depth_thread.is_alive():
            self.depth_thread.join(timeout=1.0)
        if self.prediction_thread and self.prediction_thread.is_alive():
            self.prediction_thread.join(timeout=1.0)
        if self.color_thread and self.color_thread.is_alive():
            self.color_thread.join(timeout=1.0)
        
        self.depth_sensor.stop()
        self.depth_predictor.stop()
        self.pipeline.stop()
    
    def _depth_worker(self):
        """깊이 센서 데이터를 읽는 워커 스레드"""
        while self.running:
            raw_depth_mm = self.depth_sensor.get_depth_values()
            if raw_depth_mm is not None:
                try:
                    # 새 데이터만 유지하기 위해 큐 비우기
                    while not self.raw_depth_queue.empty():
                        self.raw_depth_queue.get_nowait()
                    self.raw_depth_queue.put(raw_depth_mm, block=False)
                except queue.Full:
                    pass  # 큐가 가득 차면 넘어감
            time.sleep(0.001)  # CPU 사용량 줄이기
    
    def _prediction_worker(self):
        """깊이 예측 데이터를 읽는 워커 스레드"""
        first_inference = True
        while self.running:
            try:
                # get_depth_metric() 내부의 추론 시간 출력

                if first_inference:
                    time.sleep(2)  # 첫 추론 시 2초 대기
                    first_inference = False

                start_time = time.time()
                predicted_depth_m = self.depth_predictor.get_depth_metric()
                inference_time = time.time() - start_time
                
                if predicted_depth_m is not None:
                    try:
                        # 큐에 데이터 추가
                        while not self.predicted_depth_queue.empty():
                            self.predicted_depth_queue.get_nowait()
                        self.predicted_depth_queue.put(predicted_depth_m, block=False)
                    except queue.Full:
                        pass
            
            except Exception as e:
                print(f"깊이 예측 워커 오류: {e}")
            
            time.sleep(0.1)  # 대기 시간 증가
    
    def _color_worker(self):
        """컬러 프레임을 가져오는 워커 스레드"""
        while self.running:
            try:
                # 타임아웃을 늘림
                frames = self.pipeline.wait_for_frames(self.frame_timeout)  
                if frames is not None:
                    color_frame = frames.get_color_frame()
                    if color_frame is not None:
                        color_image = frame_to_bgr_image(color_frame)
                        if color_image is not None:  # None 체크 추가
                            try:
                                while not self.color_image_queue.empty():
                                    self.color_image_queue.get_nowait()
                                self.color_image_queue.put(color_image, block=False)
                            except queue.Full:
                                pass
            except Exception as e:
                print(f"컬러 프레임 처리 실패: {e}")
                time.sleep(0.1)  # 오류 시 대기 시간 증가
            time.sleep(0.01)  # CPU 사용량 최적화
            
    def calibrate_depth(self, raw_depth_mm, predicted_depth_m):
        """0인 부분에 predicted 값을 채운 후 실시간 보정, 나머지는 유지."""
        if raw_depth_mm is None or predicted_depth_m is None:
            print("❌ 입력 데이터 없음")
            return None
        
        # 단위 변환: m -> mm
        predicted_depth_mm = predicted_depth_m * self.scale_factor
        
        # 해상도 맞추기
        h, w = min(raw_depth_mm.shape[0], predicted_depth_mm.shape[0]), min(raw_depth_mm.shape[1], predicted_depth_mm.shape[1])
        raw_depth_mm = raw_depth_mm[:h, :w]
        predicted_depth_mm = predicted_depth_mm[:h, :w]
        
        # 0인 부분 식별
        zero_mask = (raw_depth_mm == 0)
        
        # 유효한 값으로 보정 계수 계산
        valid_mask = (raw_depth_mm > 0) & (predicted_depth_mm > 0)
        
        # 핵심: 보정 계수 계산 시 안전한 방법 사용
        if np.sum(valid_mask) > 0:
            # 비율 계산 시 np.divide로 0 나누기 방지
            scale_factors = np.divide(raw_depth_mm[valid_mask], predicted_depth_mm[valid_mask], 
                                    out=np.zeros_like(raw_depth_mm[valid_mask], dtype=float), 
                                    where=predicted_depth_mm[valid_mask]!=0)
            scale = np.median(scale_factors)
        else:
            scale = self.calibration_factor
        
        # 결과 배열 초기화
        updated_depth_mm = raw_depth_mm.copy()
        
        # 0인 부분에만 보정된 predicted 값 삽입
        updated_depth_mm[zero_mask] = predicted_depth_mm[zero_mask] * scale
        
        return updated_depth_mm

    def save_calibrated_depth(self, raw_depth_mm, predicted_depth_m, calibrated_depth_mm, frame_count):
        """보정된 최종 깊이 값과 원본 데이터를 저장 (별도 스레드에서 실행)."""
        thread = threading.Thread(
            target=self._save_data_thread,
            args=(raw_depth_mm.copy(), predicted_depth_m.copy(), calibrated_depth_mm.copy(), frame_count)
        )
        thread.daemon = True
        thread.start()
    
    def _save_data_thread(self, raw_depth_mm, predicted_depth_m, calibrated_depth_mm, frame_count):
        """별도 스레드에서 파일 저장 작업 수행"""
        timestamp_str = f"{frame_count}_{int(time.time() * 1000)}"
        
        # 1. 최종 Calibrated 데이터 저장
        npy_path = os.path.join(VALIDATION_SAVE_DIR, f'calibrated_depth_{timestamp_str}.npy')
        np.save(npy_path, calibrated_depth_mm)
        txt_path = os.path.join(VALIDATION_SAVE_DIR, f'calibrated_depth_{timestamp_str}.txt')
        np.savetxt(txt_path, calibrated_depth_mm, fmt='%.2f')
        depth_normalized = (calibrated_depth_mm - calibrated_depth_mm.min()) / \
                          (calibrated_depth_mm.max() - calibrated_depth_mm.min() + 1e-6) * 255.0
        depth_normalized = depth_normalized.astype(np.uint8)
        depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
        img_path = os.path.join(VALIDATION_SAVE_DIR, f'calibrated_depth_{timestamp_str}_visualized.png')
        cv2.imwrite(img_path, depth_colored)

        # 2. Raw 데이터 저장
        raw_npy_path = os.path.join(VALIDATION_SAVE_DIR, f'raw_depth_{timestamp_str}.npy')
        np.save(raw_npy_path, raw_depth_mm)
        raw_txt_path = os.path.join(VALIDATION_SAVE_DIR, f'raw_depth_{timestamp_str}.txt')
        np.savetxt(raw_txt_path, raw_depth_mm, fmt='%.2f')
        raw_normalized = (raw_depth_mm - raw_depth_mm.min()) / \
                         (raw_depth_mm.max() - raw_depth_mm.min() + 1e-6) * 255.0
        raw_normalized = raw_normalized.astype(np.uint8)
        raw_colored = cv2.applyColorMap(raw_normalized, cv2.COLORMAP_JET)
        raw_img_path = os.path.join(VALIDATION_SAVE_DIR, f'raw_depth_{timestamp_str}_visualized.png')
        cv2.imwrite(raw_img_path, raw_colored)

        # 3. Predicted 데이터 저장
        predicted_depth_mm = predicted_depth_m * self.scale_factor
        predicted_npy_path = os.path.join(VALIDATION_SAVE_DIR, f'predicted_depth_{timestamp_str}.npy')
        np.save(predicted_npy_path, predicted_depth_mm)
        predicted_txt_path = os.path.join(VALIDATION_SAVE_DIR, f'predicted_depth_{timestamp_str}.txt')
        np.savetxt(predicted_txt_path, predicted_depth_mm, fmt='%.2f')
        predicted_normalized = (predicted_depth_mm - predicted_depth_mm.min()) / \
                               (predicted_depth_mm.max() - predicted_depth_mm.min() + 1e-6) * 255.0
        predicted_normalized = predicted_normalized.astype(np.uint8)
        predicted_colored = cv2.applyColorMap(predicted_normalized, cv2.COLORMAP_JET)
        predicted_img_path = os.path.join(VALIDATION_SAVE_DIR, f'predicted_depth_{timestamp_str}_visualized.png')
        cv2.imwrite(predicted_img_path, predicted_colored)
        
        print(f"프레임 {frame_count} 저장 완료")

    def on_mouse(self, event, x, y, flags, param):
        """마우스 클릭 이벤트 처리 - 다중 이미지에서 깊이값 표시"""
        if event == cv2.EVENT_LBUTTONDOWN:  # 왼쪽 버튼 클릭 시
            h_image = None
            w_image = None
            
            if self.latest_raw_depth_mm is not None:
                h_image, w_image = self.latest_raw_depth_mm.shape
            
            if h_image is not None and w_image is not None:
                # 클릭 위치가 어느 이미지에 해당하는지 결정
                total_width = w_image * 3  # RGB, Raw Depth, MDE 3개의 이미지
                
                if 0 <= y < h_image:  # y 좌표는 모든 이미지에서 동일
                    if 0 <= x < w_image:  # RGB 이미지 영역
                        print(f"RGB 이미지 클릭 위치: ({x}, {y})")
                        # RGB 이미지의 해당 위치에 대한 깊이값도 표시
                        if self.latest_raw_depth_mm is not None:
                            raw_value = self.latest_raw_depth_mm[y, x]
                            print(f"해당 위치의 Raw Depth 값: {raw_value:.2f} mm")
                        if self.latest_predicted_depth_m is not None:
                            pred_value = self.latest_predicted_depth_m[y, x] * self.scale_factor
                            print(f"해당 위치의 MDE Depth 값: {pred_value:.2f} mm")
                        if self.latest_calibrated_depth_mm is not None:
                            calib_value = self.latest_calibrated_depth_mm[y, x]
                            print(f"해당 위치의 보정된 Depth 값: {calib_value:.2f} mm")
                    
                    elif w_image <= x < w_image*2:  # Raw Depth 이미지 영역
                        x_adj = x - w_image  # 원본 이미지 내 x 좌표로 조정
                        print(f"Raw Depth 이미지 클릭 위치: ({x_adj}, {y})")
                        if self.latest_raw_depth_mm is not None:
                            raw_value = self.latest_raw_depth_mm[y, x_adj]
                            print(f"Raw Depth 값: {raw_value:.2f} mm")
                    
                    elif w_image*2 <= x < w_image*3:  # MDE 이미지 영역
                        x_adj = x - w_image*2  # 원본 이미지 내 x 좌표로 조정
                        print(f"MDE 이미지 클릭 위치: ({x_adj}, {y})")
                        if self.latest_predicted_depth_m is not None:
                            pred_value = self.latest_predicted_depth_m[y, x_adj] * self.scale_factor
                            print(f"MDE Depth 값: {pred_value:.2f} mm")


    def validate_depth(self):
        """실시간 깊이 값 호출 및 보정 - 2x2 바둑판 형태로 표시"""
        frame_count = 0
        skip_frames = 1

        # 창 설정
        cv2.namedWindow("Depth Visualization", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Depth Visualization", 1280, 960)  # 거의 정사각형에 가깝게
        cv2.setMouseCallback("Depth Visualization", self.on_mouse)

        start_time = time.time()
        fps_count = 0
        fps = 0

        while self.running:
            # 데이터 가져오기 (생략)
            raw_depth_mm = None
            predicted_depth_m = None
            color_image = None
            
            try:
                raw_depth_mm = self.raw_depth_queue.get(timeout=1)
                predicted_depth_m = self.predicted_depth_queue.get(timeout=1)
                
                try:
                    color_image = self.color_image_queue.get(timeout=0.5)
                except queue.Empty:
                    pass
            
                if raw_depth_mm is not None and predicted_depth_m is not None:
                    calibrated_depth = self.calibrate_depth(raw_depth_mm, predicted_depth_m)
                    if calibrated_depth is not None:
                        self.latest_calibrated_depth_mm = calibrated_depth
            
            except queue.Empty:
                print("데이터 대기 중 타임아웃")
                continue

            if raw_depth_mm is not None and predicted_depth_m is not None:
                # 보정 계산
                calibrated_depth_mm = self.calibrate_depth(raw_depth_mm, predicted_depth_m)
                
                if calibrated_depth_mm is not None:
                    # 최신 값 저장
                    self.latest_raw_depth_mm = raw_depth_mm
                    self.latest_predicted_depth_m = predicted_depth_m
                    self.latest_calibrated_depth_mm = calibrated_depth_mm
                    if color_image is not None:
                        self.latest_color_image = color_image

                    # FPS 계산
                    fps_count += 1
                    elapsed_time = time.time() - start_time
                    if elapsed_time >= 1.0:
                        fps = fps_count / elapsed_time
                        fps_count = 0
                        start_time = time.time()
                        print(f"FPS: {fps:.2f}")
                    
                    # 디스플레이 업데이트
                    if frame_count % skip_frames == 0:
                        try:
                            images = []
                            
                            # 1. RGB 이미지
                            if self.latest_color_image is not None:
                                rgb_img = self.latest_color_image.copy()
                                cv2.putText(rgb_img, "RGB", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                cv2.putText(rgb_img, f"FPS: {fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                images.append(rgb_img)
                            
                            # 2. Raw Depth 이미지
                            if raw_depth_mm is not None:
                                raw_depth = raw_depth_mm.copy()
                                raw_min = raw_depth.min() if raw_depth.max() > raw_depth.min() else 0
                                raw_max = raw_depth.max() if raw_depth.max() > raw_depth.min() else 1
                                raw_normalized = np.clip((raw_depth - raw_min) / (raw_max - raw_min + 1e-6) * 255.0, 0, 255)
                                raw_normalized = raw_normalized.astype(np.uint8)
                                raw_depth_colored = cv2.applyColorMap(raw_normalized, cv2.COLORMAP_JET)
                                cv2.putText(raw_depth_colored, "Raw Depth", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                                images.append(raw_depth_colored)

                            # 3. MDE Depth 이미지
                            if predicted_depth_m is not None:
                                mde_depth = predicted_depth_m.copy() * self.scale_factor
                                mde_min = mde_depth.min() if mde_depth.max() > mde_depth.min() else 0
                                mde_max = mde_depth.max() if mde_depth.max() > mde_depth.min() else 1
                                mde_normalized = np.clip((mde_depth - mde_min) / (mde_max - mde_min + 1e-6) * 255.0, 0, 255)
                                mde_normalized = mde_normalized.astype(np.uint8)
                                mde_depth_colored = cv2.applyColorMap(mde_normalized, cv2.COLORMAP_JET)
                                cv2.putText(mde_depth_colored, "MDE Depth", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                                images.append(mde_depth_colored)
                            
                            # 4. 보정된 Depth 이미지
                            if calibrated_depth_mm is not None:
                                calib_depth = calibrated_depth_mm.copy()
                                calib_min = calib_depth.min() if calib_depth.max() > calib_depth.min() else 0
                                calib_max = calib_depth.max() if calib_depth.max() > calib_depth.min() else 1
                                calib_normalized = np.clip((calib_depth - calib_min) / (calib_max - calib_min + 1e-6) * 255.0, 0, 255)
                                calib_normalized = calib_normalized.astype(np.uint8)
                                calibrated_colored = cv2.applyColorMap(calib_normalized, cv2.COLORMAP_JET)
                                cv2.putText(calibrated_colored, "Calibrate Depth", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                                images.append(calibrated_colored)
                                
                            # 이미지 크기 통일 (모두 같은 크기로)
                            if len(images) == 4:
                                # 기준 해상도 설정 (중간 크기로)
                                target_height = 400
                                target_width = 500
                                
                                # 모든 이미지 크기 통일
                                for i in range(len(images)):
                                    images[i] = cv2.resize(images[i], (target_width, target_height))
                                
                                # 2x2 그리드로 배치
                                top_row = cv2.hconcat([images[0], images[1]])
                                bottom_row = cv2.hconcat([images[2], images[3]])
                                combined_view = cv2.vconcat([top_row, bottom_row])
                                
                                # 출력
                                cv2.imshow("Depth Visualization", combined_view)
                        except Exception as e:
                            print(f"디스플레이 오류: {e}")
                            import traceback
                            traceback.print_exc()

            frame_count += 1
            
            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 종료
                break
            elif key == ord('s'):  # 저장
                if raw_depth_mm is not None and predicted_depth_m is not None and calibrated_depth_mm is not None:
                    print("프레임 저장 중...")
                    self.save_calibrated_depth(raw_depth_mm, predicted_depth_m, calibrated_depth_mm, frame_count)
                    
if __name__ == "__main__":
    validator = DepthValidator()
    validator.start()

    try:
        validator.validate_depth()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        validator.stop()
        cv2.destroyAllWindows()