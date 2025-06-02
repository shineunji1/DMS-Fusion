import sys
import os
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display, clear_output

# 현재 스크립트 위치
current_dir = os.path.dirname(os.path.abspath(__file__))

# metric_depth 경로를 명확히 지정
metric_depth_path = os.path.join(current_dir, "Depth-Anything-V2/metric_depth")

# 기존 경로들을 모두 무시하고 metric_depth 내의 depth_anything_v2 모듈 경로만 추가
sys.path.insert(0, metric_depth_path)  # 0 번째에 삽입하여 다른 경로보다 우선순위를 높임

from Depth_Anything_V2.metric_depth.depth_anything_v2.dpt import DepthAnythingV2
print("metric_depth 내의 depth_anything_v2.dpt 모듈 임포트 성공")
        
def get_depth(event,x,y,flags,param) :
    if event == cv2.EVENT_LBUTTONDOWN:
        if 0 <= x < depth.shape[1] and 0 <= y < depth.shape[0]:
            depth_value = depth[y, x]
            print(f"Clicked at ({x}, {y}) -> Depth: {depth_value:.2f} meters")


# GPU 설정 (xFormers 지원 여부 확인)
use_xformers = torch.cuda.is_available()
device = torch.device("cuda" if use_xformers else "cpu")
print(f"Using device: {device}")

if not use_xformers:
    print("⚠️ CUDA가 없으므로 xformers memory-efficient attention을 비활성화합니다.")

# 모델 설정값
model_configs = {
    'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
    'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
    'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]}
}

encoder = 'vitl'  # 'vits', 'vitb' 가능
dataset = 'hypersim'  # 'hypersim' (실내), 'vkitti' (실외)
max_depth = 80 if dataset == "vkitti" else 20  # 실내/실외에 따라 max depth 설정

# 모델 로드 (GPU/CPU)
try:
    model = DepthAnythingV2(**model_configs[encoder])  # xFormers 사용 여부 전달
    model.max_depth = max_depth
    model.load_state_dict(torch.load(f'checkpoints/depth_anything_v2_metric_{dataset}_{encoder}.pth', map_location=device))
    model.eval()
    
except Exception as e:
    print(f"모델 로드 중 오류 발생: {e}")
    sys.exit(1)

# 이미지 로드 및 전처리
raw_img = cv2.imread("images/color35.png")
if raw_img is None:
    raise ValueError("이미지를 불러올 수 없습니다. 경로를 확인하세요.")

raw_img = cv2.cvtColor(raw_img, cv2.COLOR_BGR2RGB)

with torch.no_grad():
    depth = model.infer_image(raw_img)  # 모델 예측
print("Depth prediction completed!")
print(depth)

cv2.imshow("img",raw_img)
cv2.setMouseCallback("img",get_depth)
cv2.waitKey(0)
cv2.destroyAllWindows()
