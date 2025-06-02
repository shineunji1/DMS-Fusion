# moca_mde_metric.py
# 경로: C:\Users\smhrd\orbbec\pyorbbecsdk\examples\moca_mde_metric.py
import sys
import threading
import queue
import cv2
import torch
import numpy as np
import os

from orbbec_code.pyorbbecsdk import Config as OBConfig, OBSensorType, OBFormat, Pipeline, FrameSet, VideoStreamProfile, OBError
from .utils import frame_to_bgr_image
from torchvision.transforms import Compose
import time

# 경로 설정
from mde_depthAnythingV2.Depth_Anything_V2.depth_anything_v2.util.transform import Resize, NormalizeImage, PrepareForNet
from mde_depthAnythingV2.Depth_Anything_V2.metric_depth.depth_anything_v2.dpt import DepthAnythingV2

# 깊이 맵 저장 디렉토리
DEPTH_SAVE_DIR = r'.\moca\mde_viewer_values'
os.makedirs(DEPTH_SAVE_DIR, exist_ok=True)


class DepthMetricPredictor:
    def __init__(self, pipeline=None):
        # 모델 설정
        self.DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.MODEL_CHECKPOINT = None
        self.INPUT_SIZE = None
        self.MAX_DEPTH = 20.0  # m 단위

        # 모델 로드
        self.model = self.load_depth_anything_v2()

        # Orbbec 카메라 설정 (외부에서 전달된 Pipeline 사용)
        self.pipeline = pipeline
        self.config = OBConfig()
        if self.pipeline is None:
            self.pipeline = Pipeline()
            try:
                profile_list = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
                try:
                    color_profile = profile_list.get_video_stream_profile(640, 0, OBFormat.RGB, 30)
                except OBError:
                    color_profile = profile_list.get_default_video_stream_profile()
                self.config.enable_stream(color_profile)
            except Exception:
                pass

        # 큐 설정
        self.frame_queue = queue.Queue(maxsize=100)
        self.depth_queue = queue.Queue(maxsize=100)
        self.result_queue = queue.Queue(maxsize=50)
        self.save_queue = queue.Queue(maxsize=50)
        self.running = False

        # 전처리 파이프라인
        self.transform = Compose([
            Resize(
                width=self.INPUT_SIZE,
                height=self.INPUT_SIZE,
                resize_target=False,
                keep_aspect_ratio=True,
                ensure_multiple_of=14,
                resize_method='lower_bound',
                image_interpolation_method=cv2.INTER_CUBIC,
            ),
            NormalizeImage(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            PrepareForNet(),
        ])

        # 최신 깊이 값 저장용 변수
        self.latest_depth = None
        self.latest_color_image = None

    def load_depth_anything_v2(self):

        # 모델별 설정
        model_configs = {
            'vits': {
                'encoder': 'vits', 
                'features': 64, 
                'out_channels': [48, 96, 192, 384]
            },
            'vitb': {
                'encoder': 'vitb', 
                'features': 128, 
                'out_channels': [96, 192, 384, 768]
            },
            'vitl': {
                'encoder': 'vitl', 
                'features': 256, 
                'out_channels': [256, 512, 1024, 1024]
            }
        }

        encoder = 'vits'  # 'vits', 'vitb' 가능
        dataset = 'hypersim'  # 'hypersim' (실내), 'vkitti' (실외)
        max_depth = 80 if dataset == "vkitti" else 20  # 실내/실외에 따라 max depth 설정

        checkpoint_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'mde_depthAnythingV2', 
            'checkpoints', 
            f'depth_anything_v2_metric_{dataset}_{encoder}.pth'
        )

        self.MODEL_CHECKPOINT = checkpoint_path
        model = DepthAnythingV2(
            **model_configs[encoder]
            ,max_depth = max_depth
        )
        state_dict = torch.load(self.MODEL_CHECKPOINT, map_location=self.DEVICE)
        model.load_state_dict(state_dict, strict=False)
        
        # 여기서 명시적으로 모델을 GPU로 이동
        print(f"모델을 {self.DEVICE}로 이동합니다.")
        model = model.to(self.DEVICE)

        # 모델별 적절한 input_size 설정
        if encoder == 'vits' or encoder == 'vitb':
            self.INPUT_SIZE = 384
        elif encoder == 'vitl':
            self.INPUT_SIZE = 518
        
        # GPU 메모리 최적화 설정
        if self.DEVICE == 'cuda':
            torch.backends.cudnn.benchmark = True
        
        return model.eval()  # 평가 모드로 설정하고 반환

    def image2tensor(self, raw_image):
        h, w = raw_image.shape[:2]
        image = cv2.cvtColor(raw_image, cv2.COLOR_BGR2RGB) / 255.0
        image = self.transform({'image': image})['image']
        image = torch.from_numpy(image).unsqueeze(0).to(self.DEVICE)
        return image, (h, w)

    def save_and_print_depth(self, raw_depth, frame_count):
        npy_path = os.path.join(DEPTH_SAVE_DIR, f'depth_frame_{frame_count}.npy')
        np.save(npy_path, raw_depth)

        depth = (raw_depth - raw_depth.min()) / (raw_depth.max() - raw_depth.min() + 1e-6) * 255.0
        depth = depth.astype(np.uint8)
        depth_colored = cv2.applyColorMap(depth, cv2.COLORMAP_JET)
        img_path = os.path.join(DEPTH_SAVE_DIR, f'depth_frame_{frame_count}_visualized.png')
        cv2.imwrite(img_path, depth_colored)

        h, w = raw_depth.shape
        center_h, center_w = h // 2, w // 2
        region_size = 2
        for i in range(center_h - region_size, center_h + region_size + 1):
            for j in range(center_w - region_size, center_w + region_size + 1):
                if 0 <= i < h and 0 <= j < w:
                    print(f"Depth at ({i}, {j}): {raw_depth[i, j]:.2f}")

    def depth_estimation_thread(self):
        frame_count = 0
        
        # CUDA 성능 최적화 설정
        if self.DEVICE == 'cuda':
            print("🚀 GPU 모드 활성화")
            torch.backends.cudnn.benchmark = True
        else:
            print("⚠️ CPU 모드 실행 중 - 성능이 저하될 수 있습니다")
        
        # 입력 크기 감소 (성능 향상용)
        resize_factor = 0.5  # 이미지 크기를 절반으로 줄임
        
        while self.running:
            try:
                color_image = self.frame_queue.get(timeout=1)
                if color_image is None:
                    break
                    
                # 성능 타이머 시작
                start_time = time.time()
                
                # 이미지 크기 줄이기 (성능 향상)
                if resize_factor < 1.0:
                    h, w = color_image.shape[:2]
                    resized_image = cv2.resize(color_image, 
                                            (int(w * resize_factor), int(h * resize_factor)))
                else:
                    resized_image = color_image
                    
                # 모델 입력용 RGB 변환
                rgb_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
                
                # GPU 추론
                with torch.no_grad():
                    # 이미지 텐서로 변환 (GPU로 전송)
                    input_tensor, (h, w) = self.image2tensor(resized_image)
                    
                    # 모델 추론 실행
                    prediction = self.model(input_tensor)
                    
                    # 원본 크기로 복원
                    prediction = torch.nn.functional.interpolate(
                        prediction.unsqueeze(1),
                        size=color_image.shape[:2],  # 원본 크기로 복원
                        mode="bicubic",
                        align_corners=False,
                    ).squeeze()
                    
                    # GPU에서 CPU로 데이터 이동
                    depth = prediction.cpu().numpy()
                
                # 성능 측정 종료
                inference_time = time.time() - start_time
                if frame_count % 30 == 0:  # 30프레임마다 출력
                    print(f"추론 시간: {inference_time*1000:.1f}ms (GPU: {self.DEVICE == 'cuda'})")

                # 결과 저장
                self.latest_depth = depth
                self.latest_color_image = color_image

                # 깊이 큐에 결과 추가
                while self.depth_queue.full():
                    self.depth_queue.get_nowait()  # 오래된 데이터 제거
                self.depth_queue.put(depth)

                # 시각화 결과 생성
                depth_colored = cv2.applyColorMap(
                    ((depth / self.MAX_DEPTH) * 255).astype(np.uint8), 
                    cv2.COLORMAP_JET
                )
                
                # 결합된 결과 이미지 생성
                h, w = color_image.shape[:2]
                split_region = np.ones((h, 10, 3), dtype=np.uint8) * 255  # 구분선 너비 줄임
                combined_result = cv2.hconcat([color_image, split_region, depth_colored])

                # 결과 큐에 추가
                if not self.result_queue.full():
                    self.result_queue.put(combined_result)

                # 저장 요청 확인
                try:
                    save_request = self.save_queue.get_nowait()
                    if save_request:
                        self.save_and_print_depth(depth, frame_count)
                except queue.Empty:
                    pass

                frame_count += 1

            except queue.Empty:
                continue
            except Exception as e:
                print(f"깊이 추정 오류: {e}")
                continue

    def capture_frames_thread(self):
        while self.running:
            try:
                frames = self.pipeline.wait_for_frames(5000)
                if frames is None:
                    continue

                color_frame = frames.get_color_frame()
                if color_frame is None:
                    continue

                color_image = frame_to_bgr_image(color_frame)
                if color_image is None:
                    continue

                if not self.frame_queue.full():
                    self.frame_queue.put(color_image)

            except Exception:
                continue

    def start(self):
        if self.pipeline is None:
            self.pipeline.start(self.config)
        self.running = True
        self.depth_thread = threading.Thread(target=self.depth_estimation_thread)
        self.depth_thread.daemon = True
        self.depth_thread.start()
        self.capture_thread = threading.Thread(target=self.capture_frames_thread)
        self.capture_thread.daemon = True
        self.capture_thread.start()

    def stop(self):
        self.running = False
        self.frame_queue.put(None)
        self.depth_thread.join()
        self.capture_thread.join()
        if self.pipeline is None:
            self.pipeline.stop()

    def get_depth_metric(self):
        try:
            depth_metric = self.depth_queue.get(timeout=2)
            return depth_metric
        except queue.Empty:
            return None

    def on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.latest_depth is not None:
                h, w = self.latest_depth.shape
                if 0 <= y < h and 0 <= x < w:
                    depth_value = self.latest_depth[y, x]
                    print(f"Depth at ({x}, {y}): {depth_value:.2f} m")

if __name__ == "__main__":
    predictor = DepthMetricPredictor()
    predictor.start()

    try:
        frame_counter = 0
        skip_frames = 5

        cv2.namedWindow("Depth Viewer")
        cv2.setMouseCallback("Depth Viewer", predictor.on_mouse)

        while True:
            key = cv2.waitKey(1)
            if key == ord('q') or key == 27:
                break
            elif key == ord('s'):
                predictor.save_queue.put(True)

            frame_counter += 1
            if frame_counter % skip_frames == 0:
                try:
                    combined_result = predictor.result_queue.get_nowait()
                    cv2.imshow("Depth Viewer", combined_result)
                except queue.Empty:
                    pass

    except KeyboardInterrupt:
        pass
    finally:
        predictor.stop()
        cv2.destroyAllWindows()