import time
import cv2
import numpy as np
from py_orbbecsdk import Config, OBSensorType, Pipeline

ESC_KEY = 27
PRINT_INTERVAL = 1  # seconds
MIN_DEPTH = 20  # 20mm
MAX_DEPTH = 10000  # 10000mm

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

# 마우스 클릭 이벤트 핸들러
def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        depth_data = param
        depth_value = depth_data[y, x]
        print(f"Depth at ({x}, {y}): {depth_value} mm")

def main():
    config = Config()
    pipeline = Pipeline()
    temporal_filter = TemporalFilter(alpha=0.5)
    
    try:
        profile_list = pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
        depth_profile = profile_list.get_default_video_stream_profile()
        config.enable_stream(depth_profile)
    except Exception as e:
        print(e)
        return
    
    pipeline.start(config)
    last_print_time = time.time()
    
    cv2.namedWindow("Depth Viewer")

    while True:
        try:
            frames = pipeline.wait_for_frames(100)
            if frames is None:
                continue
            depth_frame = frames.get_depth_frame()
            if depth_frame is None:
                continue
            
            width = depth_frame.get_width()
            height = depth_frame.get_height()
            scale = depth_frame.get_depth_scale()

            depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
            depth_data = depth_data.reshape((height, width))
            depth_data = depth_data.astype(np.float32) * scale
            depth_data = np.where((depth_data > MIN_DEPTH) & (depth_data < MAX_DEPTH), depth_data, 0)
            depth_data_filtered = temporal_filter.process(depth_data.astype(np.uint16))

            # 여러 위치의 깊이 값 계산
            positions = [
                ("Center", int(height / 2), int(width / 2)),
                ("Top-Left", int(height / 4), int(width / 4)),
                ("Top-Right", int(height / 4), int(3 * width / 4)),
                ("Bottom-Left", int(3 * height / 4), int(width / 4)),
                ("Bottom-Right", int(3 * height / 4), int(3 * width / 4))
            ]

            # 깊이 이미지 생성
            depth_image = cv2.normalize(depth_data_filtered, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            depth_image_colored = cv2.applyColorMap(depth_image, cv2.COLORMAP_JET)

            # 깊이 값 출력 및 이미지에 텍스트 추가
            current_time = time.time()
            if current_time - last_print_time >= PRINT_INTERVAL:
                print("Depth values (mm):")
                for label, y, x in positions:
                    depth_value = depth_data_filtered[y, x]
                    print(f"{label}: {depth_value}")
                    # 이미지에 깊이 값 표시
                    cv2.putText(depth_image_colored, f"{label}: {depth_value} mm",
                                (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                last_print_time = current_time

            # 화면 표시 및 마우스 콜백 설정
            cv2.imshow("Depth Viewer", depth_image_colored)
            cv2.setMouseCallback("Depth Viewer", mouse_callback, depth_data_filtered)

            key = cv2.waitKey(1)
            if key == ord('q') or key == ESC_KEY:
                break
        except KeyboardInterrupt:
            break
    
    pipeline.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()