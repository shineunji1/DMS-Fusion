"use client"

import React, { useEffect, useState, useRef } from 'react'
import faceRecogStyle from "@/styles/faceRecog.module.css"
import Progress from "./components/Progress";
import CameraArea from "./components/CameraArea";
import { useRouter, usePathname } from "next/navigation";
import axios from 'axios';

const FaceReset = ({data}) => {
  const [step, setStep] = useState("front"); // 현재 등록 단계 (front, left, right)
  const [countdown, setCountdown] = useState(5); // 카운트다운
  const [userId, setUserId] = useState(data?.userId || "1"); // 사용자 ID 상태
  const [registrationStatus, setRegistrationStatus] = useState({
    front: false,
    left: false,
    right: false
  }); // 각 단계별 등록 상태
  const [loading, setLoading] = useState(false); // 로딩 상태
  const [message, setMessage] = useState("카메라 앞에서 정면을 바라봐주세요."); // 사용자 안내 메시지
  const [success, setSuccess] = useState(false); // 전체 등록 성공 여부
  const [key, setKey] = useState(Date.now());
  const [faceDetected, setFaceDetected] = useState(false); // 얼굴 감지 상태
  const router = useRouter();
  const pathname = usePathname(); // 현재 경로 추적
  const navigationPendingRef = useRef(false);

  // 앱 라우터에서는 events 대신 수동으로 카메라 초기화를 관리합니다
  const resetCamera = () => {
    console.log("카메라 컴포넌트 리셋");
    setKey(Date.now());
  };

  // 얼굴이 감지되면 현재 단계를 처리하는 useEffect
  useEffect(() => {
    if (faceDetected && !loading && !success) {
      startCountdown();
      router.refresh();
    }
  }, [faceDetected, step]);

  // 카운트다운 처리
  const startCountdown = () => {
    // 이미 완료된 단계면 무시
    if (registrationStatus[step]) {
      return;
    }

    setLoading(true);
    setCountdown(3); // 3초 카운트다운으로 설정

    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          processRegistration();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  };

  // 현재 단계에 대한 얼굴 등록 처리
  const processRegistration = async () => {
    try {
      setMessage(`${getStepName(step)} 촬영 중... 움직이지 마세요.`);

      // API 요청
      const response = await axios.post('http://localhost:8000/login/signup', {
        direction: step,
        user_id: userId
      }, {
        withCredentials: true,
        headers: {
          "Content-Type": "application/json"
        }
      });

      console.log(`${step} 등록 응답:`, response.data);

      // 성공적으로 등록됨
      setRegistrationStatus(prev => ({
        ...prev,
        [step]: true
      }));

      // 다음 단계로 진행
      if (step === 'front') {
        setStep('left');
        setMessage('이제 왼쪽을 바라봐주세요.');
        resetCamera(); // 단계 변경 시 카메라 리셋
      } else if (step === 'left') {
        setStep('right');
        setMessage('이제 오른쪽을 바라봐주세요.');
        resetCamera(); // 단계 변경 시 카메라 리셋
      } else if (step === 'right') {
        // 모든 단계 완료
        setMessage('얼굴 등록이 완료되었습니다!');
        console.log(response.data);
        setUserId(response.data.userId);
        setSuccess(response.data.success);
      }
    } catch (error) {
      console.error(`${step} 등록 오류:`, error);
      setMessage(`${getStepName(step)} 촬영 중 오류가 발생했습니다. 다시 시도해주세요.`);
    } finally {
      setLoading(false);
      setCountdown(0);
    }
  };

  // 단계 이름 한글화
  const getStepName = (step) => {
    switch(step) {
      case 'front': return '정면';
      case 'left': return '좌측';
      case 'right': return '우측';
      default: return step;
    }
  };

  // 등록 완료 후 다음 페이지로 이동
  const handleRegistrationComplete = () => {
    document.cookie = `userId=${userId}; path=/signup`;
    
    // 카메라 정리 후 네비게이션 표시
    navigationPendingRef.current = true;
    
    // 네비게이션 전에 잠시 지연시켜 리소스 정리 시간 확보
    setTimeout(() => {
      router.push(`/signup/set-profile`);
    }, 100);
  };

  return (
    <div className={faceRecogStyle.container}>
      <Progress/>
      <CameraArea 
        key={key} 
        faceDetected={faceDetected} 
        setFaceDetected={setFaceDetected}
        navigationPending={navigationPendingRef.current}
      />
      {
        success ? 
        <div><button onClick={handleRegistrationComplete} className={faceRecogStyle.add}>등록하기</button></div> : 
        <div className={faceRecogStyle.alertMsg}>{
          faceDetected ? message : "얼굴을 화면에 맞춰주세요"
        }</div>
      }
    </div>
  );
};

export default FaceReset;