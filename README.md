# DMS_Fusion
RGB-D 카메라를 활용한 DMS 구현(스마트인재개개발원 프로젝트)

# 개발 기간
2025.03.04 ~ 2025.03.20 (총 16일)

# 맡은 역할
FrontEnd로 UI/UX개발 및 구현, 화면 디자인 설계, 화면 설계서 제작 및 딥러닝 모델을 개발 하였습니다.

# 사용기술
- 언어 : <img src="https://img.shields.io/badge/javascript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black"> <img src="https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white">
- 백엔드 : <img src="https://img.shields.io/badge/fastapi-009688?style=for-the-badge&logo=fastapi&logoColor=white">
- 프론트엔드: <img src="https://img.shields.io/badge/nextjs-000000?style=for-the-badge&logo=nextdotjs&logoColor=white">
- DB : <img src="https://img.shields.io/badge/milvus-00A1EA?style=for-the-badge&logo=milvus&logoColor=white"> <img src="https://img.shields.io/badge/mysql-4479A1?style=for-the-badge&logo=mysql&logoColor=white">
- 딥러닝 개발 : <img src="https://img.shields.io/badge/pytorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white">
- 비전 모듈 : <img src="https://img.shields.io/badge/opencv-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white"> , ORBBEC SDK

# 라이브러리
Three.js / React-three-fiber / Swiper.js

# 주요 기술 채용목적
- FastAPI : DeepLearing 기술과 OpenCV의 사용목적 때문에 Python 기반 중 비동기 통신이 가능한 이유로 채용하였습니다.
- Next.js : SSR(서버 사이드 렌더링)이 가능한 Node.js의 풀스택 기반 프레임워크로 <b>빠른 로딩과 React의 장점을 그대로 가져가</b> 화면 구현하는데 <br/> 어려움이 없을것 같아 채용하였습니다.
- Milvus : 얼굴 인식을 할 때 기존 RDB에 적용시키면 인증의 어려움과 큰 배열의 값은 RDB와는 적합하지 않다고 생각하여 들어온 벡터 데이터의 <br/> 근사값으로 데이터를 조회하는 기능인 VectorDB중 자체적으로 DBMS시스템을 제공해주는 이유 때문에 채용하였습니다.
- Pytorch : tensorflow 대비 다양한 기능과 연구목적인 모델로 제작 하였기 때문에 pytorch로 구현하였습니다.
- Three.js : 메모리 시트 구현시 실제 차량 과 비슷하게 하기 위해 좌석과 핸들 3D 모델을 불러와서 움직임을 보이도록 하기 위해서 사용하였습니다.

# 시스템 아키텍처
![image](https://github.com/user-attachments/assets/43646a11-43ff-4d9b-a895-ff76f7badff0)

# 딥러닝 모델
![image](https://github.com/user-attachments/assets/6b61ba83-8dd7-4989-a5bf-ff967f527f71)
- U-Net 아키텍처를 활용하여 CBAM(Convolutional Block Attention)으로 제작된 모델
- 특징 : 기존의 ToF나 광구조학 카메라가 찍지 못하는 공간을 MDE(Metric Depth Estimation)의 값으로 대체하고 대체 된 값을 기존 Depth와 비슷하게 하여 저비용 RGB-D카메라로 고비용 급의 정보를 낼 수있음
- 연구 목적으로 실제 개발에는 채용이 안됨
- 학습데이터 : MDE값 (3채널), 신뢰도 값 (1채널)
- 정답 데이터 : 깊이센서 Depth 값

- 결과

![image](https://github.com/user-attachments/assets/f1be940a-9ce8-4eea-9b5a-8b5c46102aca)
![image](https://github.com/user-attachments/assets/5e2d41b5-7a31-4d14-ba3f-4d337c6b9f88)

  - MSE (평균 절대 오차 ) : 34.43mm
  - RMSE ( 평균 제곱근 오차 ): 62.85mm 
  - Rel(상대오차) : 5.19%
  - Delta (> 1.25) : 93.15% => 실제 값의 1.25배 안에서 93프로 정확도를 가지고 있음을 뜻함

- 더 개발할 점
  - RGB만으로도 깊이를 측정할 수 있도록 개발발

# 주요 기능
- 깊이 보정 : DepthAnything V2와 Orbbec Astro + 를 활용하여 Astro + 가 찍지못한 공간을 DepthAnything V2의 MDE를 활용하여 빈 값을 채우고 실측치랑 맞게 보정을 해줌
- 결과물

![image](https://github.com/user-attachments/assets/f11a6b86-833a-4b1a-953f-7dc4253ae173)

- 얼굴 인증 : 안티 스푸핑을 넣어 핸드폰 사진으로 인증할 경우 막도록 하였음
- 2차 비번 : 얼굴 인증이 안되거나 대리운전자 경우를 위해 기능을 추가
- 결과물 :

![image](https://github.com/user-attachments/assets/a88e9bac-43e2-405f-b048-7ea275f27924)

- DMS : 실시간 스트리밍을 통해 졸음 탐지 및 주의 분산을 탐지 함
- 결과물 :

졸음 및 주의 분산 평가 기준 <br/>
![image](https://github.com/user-attachments/assets/70a35ae1-8212-405c-ade6-e16cf45a72e8)

실제 작동 사진
![image](https://github.com/user-attachments/assets/6b63066d-83e7-4991-92c1-e325b537250d)

# 프로젝트 추가로 개발 해야 할 점
- 사이트 초기 진입 시 로딩 속도 개선
- 연구 목적 딥러닝 모델 적용 후 테스트
- 실시간 스트리밍 부분 및 얼굴 등록 부분 개선

# 사이트 전체 이미지
- 메인
![main](https://github.com/user-attachments/assets/3d8dec94-ef2c-46d1-b6aa-caf4e7127a1f)
- 설정 메뉴
![setting-menu](https://github.com/user-attachments/assets/56c89b9b-1fb2-400e-b696-5f6a3fac2aa9)
- 좌석 설정
![seat-set](https://github.com/user-attachments/assets/ea134756-d7d1-41a1-970d-10a0e813122b)
- 프로필 업데이트 / 등록
![profile-update](https://github.com/user-attachments/assets/d9291028-fdaf-4153-82dc-dbaab39a4b26)
- 모니터링 세팅
![monitoring-set](https://github.com/user-attachments/assets/dcbaa9a5-4c72-4254-bd6d-5fabfdc100ca)
- 얼굴 재인증 / 등록
![face-reset](https://github.com/user-attachments/assets/33469add-c25f-427a-b72b-f49f6845cd58)

# 어려웠던 점
- 기존에 Next.js를 연습삼아 사용하였지만 주로 Nest.js나 Express를 활용하여 백 서버를 구현하였지만 이번에 FastAPI를 활용하면서 연결하는데 어려움이 컸습니다.<br/> 특히, 실시간 스트리밍 쪽에서 에러가 많이 나타나 WebSocket을 Next.js : SSR(서버 사이드 렌더링)이 가능한 Node.js의 풀스택 기반 프레임워크로 <b>빠른 로딩과 React의 장점을 그대로 가져가</b> 화면 구현하는데 <br/> 어려움이 없을것 같아 채용하였습니다.
- Milvus : 얼굴 인식을 할 때 기존 RDB에 적용시키면 인증의 어려움과 큰 배열의 값은 RDB와는 적합하지 않다고 생각하여 들어온 벡터 데이터의 <br/> 근사값으로 데이터를 조회하는 기능인 VectorDB중 자체적으로 DBMS시스템을 제공해주는 이유 때문에 채용하였습니다.
- Pytorch : tensorflow 대비 다양한 기능과 연구목적인 모델로 제작 하였기 때문에 pytorch로 구현하였습니다.
- Three.js : 메모리 시트 구현시 실제 차량 과 비슷하게 하기 위해 좌석과 핸들 3D 모델을 불러와서 움직임을 보이도록 하기 위해서 사용하였습니다.

# 시스템 아키텍처
![image](https://github.com/user-attachments/assets/43646a11-43ff-4d9b-a895-ff76f7badff0)

# 딥러닝 모델
![image](https://github.com/user-attachments/assets/6b61ba83-8dd7-4989-a5bf-ff967f527f71)
- U-Net 아키텍처를 활용하여 CBAM(Convolutional Block Attention)으로 제작된 모델
- 특징 : 기존의 ToF나 광구조학 카메라가 찍지 못하는 공간을 MDE(Metric Depth Estimation)의 값으로 대체하고 대체 된 값을 기존 Depth와 비슷하게 하여 저비용 RGB-D카메라로 고비용 급의 정보를 낼 수있음
- 연구 목적으로 실제 개발에는 채용이 안됨
- 학습데이터 : MDE값 (3채널), 신뢰도 값 (1채널)
- 정답 데이터 : 깊이센서 Depth 값

- 결과

![image](https://github.com/user-attachments/assets/f1be940a-9ce8-4eea-9b5a-8b5c46102aca)
![image](https://github.com/user-attachments/assets/5e2d41b5-7a31-4d14-ba3f-4d337c6b9f88)

  - MSE (평균 절대 오차 ) : 34.43mm
  - RMSE ( 평균 제곱근 오차 ): 62.85mm 
  - Rel(상대오차) : 5.19%
  - Delta (> 1.25) : 93.15% => 실제 값의 1.25배 안에서 93프로 정확도를 가지고 있음을 뜻함

- 더 개발할 점
  - RGB만으로도 깊이를 측정할 수 있도록 개발발

# 주요 기능
- 깊이 보정 : DepthAnything V2와 Orbbec Astro + 를 활용하여 Astro + 가 찍지못한 공간을 DepthAnything V2의 MDE를 활용하여 빈 값을 채우고 실측치랑 맞게 보정을 해줌
- 결과물

![image](https://github.com/user-attachments/assets/f11a6b86-833a-4b1a-953f-7dc4253ae173)

- 얼굴 인증 : 안티 스푸핑을 넣어 핸드폰 사진으로 인증할 경우 막도록 하였음
- 2차 비번 : 얼굴 인증이 안되거나 대리운전자 경우를 위해 기능을 추가
- 결과물 :

![image](https://github.com/user-attachments/assets/a88e9bac-43e2-405f-b048-7ea275f27924)

- DMS : 실시간 스트리밍을 통해 졸음 탐지 및 주의 분산을 탐지 함
- 결과물 :

졸음 및 주의 분산 평가 기준 <br/>
![image](https://github.com/user-attachments/assets/70a35ae1-8212-405c-ade6-e16cf45a72e8)

실제 작동 사진
![image](https://github.com/user-attachments/assets/6b63066d-83e7-4991-92c1-e325b537250d)

# 프로젝트 추가로 개발 해야 할 점
- 사이트 초기 진입 시 로딩 속도 개선
- 연구 목적 딥러닝 모델 적용 후 테스트
- 실시간 스트리밍 부분 및 얼굴 등록 부분 개선

# 사이트 전체 이미지
- 메인
![main](https://github.com/user-attachments/assets/3d8dec94-ef2c-46d1-b6aa-caf4e7127a1f)
- 설정 메뉴
![setting-menu](https://github.com/user-attachments/assets/56c89b9b-1fb2-400e-b696-5f6a3fac2aa9)
- 좌석 설정
![seat-set](https://github.com/user-attachments/assets/ea134756-d7d1-41a1-970d-10a0e813122b)
- 프로필 업데이트 / 등록
![profile-update](https://github.com/user-attachments/assets/d9291028-fdaf-4153-82dc-dbaab39a4b26)
- 모니터링 세팅
![monitoring-set](https://github.com/user-attachments/assets/dcbaa9a5-4c72-4254-bd6d-5fabfdc100ca)
- 얼굴 재인증 / 등록
![face-reset](https://github.com/user-attachments/assets/33469add-c25f-427a-b72b-f49f6845cd58)

