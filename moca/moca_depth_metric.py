# moca_depth_metric.py
# 경로: C:\Users\smhrd\orbbec\pyorbbecsdk\examples\moca_depth_viewer.py
import time
import cv2
import numpy as np
import os
import queue
import threading
import sys

from orbbec_code.pyorbbecsdk import Config as OBConfig, OBError, OBSensorType, OBFormat, Pipeline, FrameSet, VideoStreamProfile

ESC_KEY = 27
PRINT_INTERVAL = 1  # seconds (출력 간격)
MIN_DEPTH = 20  # 20mm
MAX_DEPTH = 10000  # 10000mm

# 깊이 맵 저장 디렉토리
DEPTH_SAVE_DIR = r'.\moca\depth_viewer_values'

# 디렉토리 생성 시 예외 처리
try:
    os.makedirs(DEPTH_SAVE_DIR, exist_ok=True)
except Exception as e:
    print(f"Failed to create directory {DEPTH_SAVE_DIR}: {e}")
    raise

# TemporalFilter 클래스
class TemporalFilter:
    def __init__(self, alpha):
        self.alpha = alpha
        self.previous_frame = None

    def process(self, frame):
        if self.previous_frame is None:
            result = frame
        else:
            result = cv2.addWeighted(frame, self.alpha, self.previous_frame, 1 - self.alpha, 0)
        self.previous_frame = result
        return result

# DepthSensor 클래스
class DepthSensor:
    def __init__(self):
        self.config = OBConfig()
        self.pipeline = Pipeline()
        self.temporal_filter = TemporalFilter(alpha=0.5)
        self.running = False
        self.depth_queue = queue.Queue(maxsize=1)  # 깊이 값 반환용 큐
        self.result_queue = queue.Queue(maxsize=1)  # 뷰어용 결과 큐
        self.latest_raw_depth = None  # 최신 깊이 값을 저장할 변수

        try:
            profile_list = self.pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
            assert profile_list is not None
            depth_profile = profile_list.get_default_video_stream_profile()
            assert depth_profile is not None
            print("depth profile: ", depth_profile)
            self.config.enable_stream(depth_profile)
        except Exception as e:
            print(e)
            raise

    def save_and_print_depth(self, raw_depth, depth_image, frame_count):
        """깊이 맵과 관련 파일 저장"""
        try:
            # 타임스탬프와 프레임 카운트 조합으로 파일 이름 생성
            timestamp_str = f"{frame_count}_{int(time.time() * 1000)}"  # 고유성 보장

            # .npy 파일로 저장
            npy_path = os.path.join(DEPTH_SAVE_DIR, f'depth_frame_{timestamp_str}.npy')
            np.save(npy_path, raw_depth)
            print(f"Depth map saved to {npy_path}")

            # 텍스트 파일로 저장
            txt_path = os.path.join(DEPTH_SAVE_DIR, f'depth_frame_{timestamp_str}.txt')
            np.savetxt(txt_path, raw_depth, fmt='%.2f')
            print(f"Depth map saved as text to {txt_path}")

            # 깊이 이미지로 저장
            img_path = os.path.join(DEPTH_SAVE_DIR, f'depth_frame_{timestamp_str}.png')
            cv2.imwrite(img_path, depth_image)
            print(f"Depth image saved to {img_path}")

            # 중앙 픽셀 주변의 깊이 값 출력 (5x5 영역)
            h, w = raw_depth.shape
            center_h, center_w = h // 2, w // 2
            region_size = 2  # 5x5 영역
            print(f"\nDepth values around center ({center_h}, {center_w}):")
            for i in range(center_h - region_size, center_h + region_size + 1):
                for j in range(center_w - region_size, center_w + region_size + 1):
                    if 0 <= i < h and 0 <= j < w:
                        print(f"Depth at ({i}, {j}): {raw_depth[i, j]:.2f}")
        except Exception as e:
            print(f"Error during saving depth data: {e}")

    def depth_capture_thread(self):
        frame_count = 0
        frame_counter = 0
        skip_frames = 5  # 5프레임마다 시각화 (CPU 부하 감소)
        while self.running:
            try:
                frames = self.pipeline.wait_for_frames(5000)
                if frames is None:
                    print("Warning: Frames not received, continuing...")
                    continue
                depth_frame = frames.get_depth_frame()
                if depth_frame is None:
                    print("Warning: Depth frame not received, continuing...")
                    continue
                
                width = depth_frame.get_width()
                height = depth_frame.get_height()
                scale = depth_frame.get_depth_scale()

                depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
                depth_data = depth_data.reshape((height, width))

                # raw_depth 저장 (정규화 전)
                raw_depth = depth_data.astype(np.float32) * scale
                raw_depth = np.where((raw_depth > MIN_DEPTH) & (raw_depth < MAX_DEPTH), raw_depth, 0)

                # 최신 깊이 값 저장
                self.latest_raw_depth = raw_depth

                # Temporal filtering 적용
                depth_data = self.temporal_filter.process(raw_depth.astype(np.uint16))

                # 깊이 이미지 정규화 및 컬러 맵 적용
                depth_image = cv2.normalize(depth_data, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                depth_image = cv2.applyColorMap(depth_image, cv2.COLORMAP_JET)

                # 깊이 값 큐에 추가
                if not self.depth_queue.full():
                    self.depth_queue.put((raw_depth, depth_image))

                # 시각화 (프레임 스킵 적용)
                frame_counter += 1
                if frame_counter % skip_frames == 0:
                    if not self.result_queue.full():
                        self.result_queue.put(depth_image)

            except Exception as e:
                print(f"Error during depth capture: {e}")
                break

    def start(self):
        """카메라와 스레드를 시작."""
        self.pipeline.start(self.config)
        self.running = True
        self.depth_thread = threading.Thread(target=self.depth_capture_thread)
        self.depth_thread.daemon = True
        self.depth_thread.start()

    def stop(self):
        """카메라와 스레드를 종료."""
        self.running = False
        self.depth_thread.join()
        self.pipeline.stop()

    def get_depth_values(self):
        """최신 깊이 값을 반환 (mm 단위)."""
        try:
            try:
                raw_depth, depth_image = self.depth_queue.get_nowait()
                return raw_depth  # mm 단위 numpy 배열
            except queue.Empty:
                return None
        except Exception as e:
            print(f"Error in get_depth_values: {e}")
            return None

    def on_mouse(self, event, x, y, flags, param):
        """마우스 클릭 이벤트 처리."""
        if event == cv2.EVENT_LBUTTONDOWN:  # 왼쪽 버튼 클릭 시
            if self.latest_raw_depth is not None:
                h, w = self.latest_raw_depth.shape
                if 0 <= y < h and 0 <= x < w:
                    depth_value = self.latest_raw_depth[y, x]
                    print(f"Depth at ({x}, {y}): {depth_value:.2f} mm")

if __name__ == "__main__":
    sensor = DepthSensor()
    sensor.start()

    try:
        # 마우스 이벤트 콜백 설정
        cv2.namedWindow("Depth Viewer")
        cv2.setMouseCallback("Depth Viewer", sensor.on_mouse)

        while True:
            # 뷰어 표시
            try:
                depth_image = sensor.result_queue.get_nowait()
                cv2.imshow("Depth Viewer", depth_image)
            except queue.Empty:
                pass

            # 's' 키로 저장 요청 처리
            if cv2.waitKey(1) == ord('s'):
                print("Save key pressed...")
                try:
                    # 최신 깊이 값과 이미지를 가져오기
                    raw_depth, depth_image = sensor.depth_queue.get_nowait()
                    sensor.save_and_print_depth(raw_depth, depth_image, time.time())
                except queue.Empty:
                    print("No depth data available to save.")
                except Exception as e:
                    print(f"Error saving depth data: {e}")

            # 'q' 키로 종료
            if cv2.waitKey(1) == ord('q'):
                break
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        sensor.stop()
        cv2.destroyAllWindows()