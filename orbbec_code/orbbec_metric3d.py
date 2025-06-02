import sys
import os
import cv2
import torch
import numpy as np
try:
    from mmcv.utils import Config
except:
    from mmengine import Config

from pyorbbecsdk import Config as OBConfig, OBError, OBSensorType, OBFormat, Pipeline, FrameSet, VideoStreamProfile
from utils import frame_to_bgr_image  # Orbbec SDK 유틸리티 함수

# Set metric3d_dir to the root directory of the Metric3D project
# User needs to set this path correctly
metric3d_dir = r'./Metric3D' # Replace with actual path, e.g., 'C:\Users\smhrd\Metric3D'
sys.path.append(metric3d_dir)

# 모델 타입 정의
MODEL_TYPE = {
    'ViT-Small': {
        'cfg_file': f'{metric3d_dir}/mono/configs/HourglassDecoder/vit.raft5.small.py',
        'ckpt_file': 'https://huggingface.co/JUGGHM/Metric3D/resolve/main/metric_depth_vit_small_800k.pth',
    },
}

# Metric3D 모델 로드 함수 (ViT-Small만 사용 예시)
def metric3d_vit_small(pretrain=True):
    cfg_file = MODEL_TYPE['ViT-Small']['cfg_file']
    ckpt_file = MODEL_TYPE['ViT-Small']['ckpt_file']
    
    # 설정 파일 로드 (mono/model/monodepth_model.py 필요)
    from mono.model.monodepth_model import get_configured_monodepth_model
    cfg = Config.fromfile(cfg_file)
    model = get_configured_monodepth_model(cfg)
    
    if pretrain:
        model.load_state_dict(
            torch.hub.load_state_dict_from_url(ckpt_file)['model_state_dict'], 
            strict=False,
        )
    return model

# 이미지 전처리 함수
def preprocess_image(image, input_size=(616, 1064)):
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    scale = min(input_size[0] / h, input_size[1] / w)
    rgb = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
    
    h, w = rgb.shape[:2]
    pad_h = input_size[0] - h
    pad_w = input_size[1] - w
    pad_h_half = pad_h // 2
    pad_w_half = pad_w // 2
    rgb = cv2.copyMakeBorder(rgb, pad_h_half, pad_h - pad_h_half, pad_w_half, pad_w - pad_w_half, 
                             cv2.BORDER_CONSTANT, value=[123.675, 116.28, 103.53])
    
    rgb = torch.from_numpy(rgb.transpose((2, 0, 1))).float()
    mean = torch.tensor([123.675, 116.28, 103.53]).float()[:, None, None]
    std = torch.tensor([58.395, 57.12, 57.375]).float()[:, None, None]
    rgb = torch.div((rgb - mean), std)
    rgb = rgb[None, :, :, :]
    
    return rgb, (pad_h_half, pad_h - pad_h_half, pad_w_half, pad_w - pad_w_half), scale

# 깊이 후처리 함수
def postprocess_depth(pred_depth, pad_info, original_size, scale, intrinsic=None):
    pred_depth = pred_depth.squeeze()
    pred_depth = pred_depth[pad_info[0]:pred_depth.shape[0] - pad_info[1], 
                            pad_info[2]:pred_depth.shape[1] - pad_info[3]]
    
    pred_depth = torch.nn.functional.interpolate(pred_depth[None, None, :, :], 
                                                 original_size, mode='bilinear').squeeze()
    
    # 카메라 내재 파라미터가 있다면 메트릭 단위로 변환
    if intrinsic:
        canonical_to_real_scale = intrinsic[0] / 1000.0  # 정규화된 초점 거리 기준
        pred_depth = pred_depth * canonical_to_real_scale
    pred_depth = torch.clamp(pred_depth, 0, 300)
    
    return pred_depth.cpu().numpy()

def main():
    # Metric3D 모델 로드
    model = metric3d_vit_small(pretrain=True).eval()
    
    # Orbbec 카메라 설정
    config = OBConfig()
    pipeline = Pipeline()
    try:
        profile_list = pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
        try:
            color_profile: VideoStreamProfile = profile_list.get_video_stream_profile(640, 0, OBFormat.RGB, 30)
        except OBError as e:
            print(e)
            color_profile = profile_list.get_default_video_stream_profile()
            print("color profile: ", color_profile)
        config.enable_stream(color_profile)
    except Exception as e:
        print(e)
        return
    
    # 파이프라인 시작
    pipeline.start(config)
    
    # 깊이 추정 활성화 플래그
    depth_enabled = False
    
    # Orbbec 카메라 내재 파라미터 (예시, 실제 값으로 교체 필요)
    intrinsic = [707.0493, 707.0493, 604.0814, 180.5066]  # [fx, fy, cx, cy]
    
    while True:
        try:
            # 프레임 가져오기
            frames: FrameSet = pipeline.wait_for_frames(500)
            if frames is None:
                print("Warning: Frames not received, continuing...")
                continue
            color_frame = frames.get_color_frame()
            if color_frame is None:
                print("Warning: Color frame not received, continuing...")
                continue
            
            # BGR 이미지로 변환
            color_image = frame_to_bgr_image(color_frame)
            if color_image is None:
                print("failed to convert frame to image")
                continue
            
            # 기본 뷰어 출력
            cv2.imshow("Color Viewer", color_image)
            
            # 키 입력 처리
            key = cv2.waitKey(1)
            if key == ord('q') or key == 27:  # 'q' 또는 ESC로 종료
                break
            elif key == ord('d'):  # 'd' 키로 깊이 추정 토글
                depth_enabled = not depth_enabled
                if depth_enabled:
                    print("Depth estimation enabled")
                else:
                    print("Depth estimation disabled")
                    cv2.destroyWindow("Depth Map")
            
            # 깊이 추정 활성화 시 처리
            if depth_enabled:
                original_size = color_image.shape[:2]
                input_tensor, pad_info, scale = preprocess_image(color_image)
                
                with torch.no_grad():
                    pred_depth, confidence, output_dict = model.inference({'input': input_tensor})
                
                # 내재 파라미터를 스케일에 맞게 조정
                scaled_intrinsic = [intrinsic[0] * scale, intrinsic[1] * scale, intrinsic[2] * scale, intrinsic[3] * scale]
                depth_map = postprocess_depth(pred_depth, pad_info, original_size, scale, scaled_intrinsic)
                
                # 깊이 맵 시각화
                depth_visual = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX)
                depth_visual = depth_visual.astype(np.uint8)
                depth_visual = cv2.applyColorMap(depth_visual, cv2.COLORMAP_JET)
                
                cv2.imshow("Depth Map", depth_visual)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error during processing: {e}")
            break
    
    # 파이프라인 종료
    pipeline.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()