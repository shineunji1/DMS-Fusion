"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import faceRecogStyle from "@/styles/faceRecog.module.css";

const CameraArea = ({ faceDetected, setFaceDetected, navigationPending = false }) => {
  const imageRef = useRef(null);
  const wsRef = useRef(null);
  const isMountedRef = useRef(true);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const [streamActive, setStreamActive] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [streamUrl, setStreamUrl] = useState("");
  const [wsConnected, setWsConnected] = useState(false);
  const lastFaceDetectedRef = useRef(faceDetected); // 마지막 상태를 ref로 저장

  // 리소스 정리 함수
  const cleanupResources = useCallback(() => {
    // WebSocket 연결 닫기
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
      wsRef.current = null;
      setWsConnected(false);
    }
    
    // 재연결 시도 카운터 초기화
    reconnectAttemptsRef.current = 0;
    
    // 타임아웃 정리
    if (window.reconnectTimeout) {
      clearTimeout(window.reconnectTimeout);
      window.reconnectTimeout = null;
    }
    
    if (window.pollingInterval) {
      clearTimeout(window.pollingInterval);
      window.pollingInterval = null;
    }
  }, []);

  // 카메라 스트림 초기화 - 불필요한 재초기화 방지
  const initializeCamera = useCallback(() => {
    if (!isMountedRef.current || (streamActive && !loadError)) return;

    console.log("카메라 스트림 초기화");
    setLoadError(false);
    
    // 캐시 방지용 타임스탬프 추가
    const timestamp = Date.now();
    setStreamUrl(`http://localhost:8000/login/stream?t=${timestamp}`);
    setStreamActive(true);
  }, [streamActive, loadError]);

  // WebSocket 연결
  const connectWebSocket = useCallback(() => {
    // 이미 연결된 경우 새 연결 시도 방지
    if (!isMountedRef.current || wsRef.current?.readyState === WebSocket.OPEN) return;

    // 기존 연결 정리
    cleanupResources();

    console.log("WebSocket 연결 시도");
    const wsUrl = "ws://localhost:8000/login/ws/face-status";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket 연결 성공");
      if (isMountedRef.current) {
        setWsConnected(true);
        reconnectAttemptsRef.current = 0;
      }
    };

    ws.onmessage = (event) => {
      if (!isMountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        console.log("받은 WebSocket 데이터:", data); // 디버깅용 로그 추가
        
        // face_detected 값이 있는지 확인하고 boolean으로 변환
        if (data && 'face_detected' in data) {
          const isDetected = Boolean(data.face_detected);
          setFaceDetected(isDetected);
        } else {
        }
      } catch (error) {
        console.error("WebSocket 메시지 파싱 오류:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket 오류:", error);
      if (isMountedRef.current) {
        setWsConnected(false);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket 연결 종료");
      if (isMountedRef.current) {
        setWsConnected(false);
      }

      // 재연결 로직 - 컴포넌트가 마운트되어 있고 페이지가 보일 때만 시도
      if (isMountedRef.current && 
          document.visibilityState === "visible" && 
          reconnectAttemptsRef.current < maxReconnectAttempts) {
        
        // 지수 백오프 적용 (1초, 2초, 4초, 8초...)
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 15000);
        reconnectAttemptsRef.current += 1;
        
        console.log(`WebSocket 재연결 대기 중... (${delay}ms)`);
        window.reconnectTimeout = setTimeout(() => {
          console.log(`WebSocket 재연결 시도 (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          connectWebSocket();
        }, delay);
      }
    };
  }, [cleanupResources, setFaceDetected]);

  // 컴포넌트 마운트/언마운트 관리
  useEffect(() => {
    console.log("카메라 컴포넌트 마운트");
    isMountedRef.current = true;
    lastFaceDetectedRef.current = faceDetected; // 초기값 설정
    
    // 초기 연결
    initializeCamera();
    connectWebSocket();

    return () => {
      console.log("카메라 컴포넌트 언마운트");
      isMountedRef.current = false;
      cleanupResources();
    };
  }, [initializeCamera, connectWebSocket, cleanupResources, faceDetected]);

  // 페이지 가시성 변화 감지 및 처리
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible" && isMountedRef.current) {
        console.log("페이지 활성화 감지");
        
        // 에러가 있거나 스트림이 비활성화된 경우에만 재초기화
        if (loadError || !streamActive) {
          console.log("카메라 스트림 재연결");
          initializeCamera();
        }
        
        // WebSocket이 연결되지 않은 경우에만 재연결
        if (!wsConnected && !wsRef.current) {
          console.log("WebSocket 재연결");
          connectWebSocket();
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [loadError, streamActive, wsConnected, initializeCamera, connectWebSocket]);

  // 네비게이션 발생 시 정리
  useEffect(() => {
    if (navigationPending) {
      console.log("네비게이션 감지 - 리소스 정리");
      cleanupResources();
    }
  }, [navigationPending, cleanupResources]);

  // 얼굴 감지 관련 로직 추가 (useEffect 부분에 넣어주세요)
  useEffect(() => {
    // 얼굴이 5초 이상 감지되지 않으면 카메라 재시도
    let faceDetectionTimer;
    
    if (!faceDetected && streamActive && !loadError) {
      faceDetectionTimer = setTimeout(() => {
        if (isMountedRef.current) {
          console.log("얼굴 미감지 지속 - 카메라 재연결");
          // 새 타임스탬프로 URL 갱신
          const timestamp = Date.now();
          setStreamUrl(`http://localhost:8000/login/stream?t=${timestamp}`);
        }
      }, 5000);
    }

    return () => {
      if (faceDetectionTimer) clearTimeout(faceDetectionTimer);
    };
  }, [faceDetected, streamActive, loadError]);

  // 이미지 로드 성공 핸들러
  const handleImageLoad = () => {
    if (!isMountedRef.current) return;
    console.log("MJPEG 스트림 로드 성공");
    setStreamActive(true);
    setLoadError(false);
    reconnectAttemptsRef.current = 0; // 성공하면 재연결 시도 카운터 초기화
  };

  // 이미지 로드 실패 핸들러
  const handleImageError = () => {
    if (!isMountedRef.current) return;
    console.error("MJPEG 스트림 로드 실패");
    setStreamActive(false);
    setLoadError(true);

    // 최대 재시도 횟수 이내인 경우만 재연결 시도
    if (reconnectAttemptsRef.current < maxReconnectAttempts) {
      // 지수 백오프로 재시도 간격 증가 (기본 3초, 최대 20초)
      const delay = Math.min(3000 * Math.pow(1.5, reconnectAttemptsRef.current), 20000);
      reconnectAttemptsRef.current += 1;
      
      console.log(`스트림 재연결 대기 중... (${delay}ms)`);
      window.reconnectTimeout = setTimeout(() => {
        if (isMountedRef.current) {
          console.log(`스트림 재연결 시도 (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          // 새 타임스탬프로 URL 생성하여 캐시 문제 방지
          const timestamp = Date.now();
          setStreamUrl(`http://localhost:8000/login/stream?t=${timestamp}`);
        }
      }, delay);
    } else {
      console.log("최대 재연결 시도 횟수 초과");
    }
  };

  return (
    <div className={faceRecogStyle.cameraBox}>
      <div
        className={faceRecogStyle.faceStatus}
        style={{
          background: faceDetected ? "green" : "red",
          opacity: streamActive ? 1 : 0.6,
        }}
      >
        <div className={faceRecogStyle.camera}>
          {streamUrl && (
            <img
              ref={imageRef}
              src={streamUrl}
              alt="카메라 스트림"
              className={`${faceRecogStyle.cameraStream} ${loadError ? faceRecogStyle.hidden : ""}`}
              onLoad={handleImageLoad}
              onError={handleImageError}
            />
          )}
          {(!streamActive || loadError) && (
            <div className={faceRecogStyle.reconnecting}>
              {loadError ? "카메라 연결 실패, 재연결 중..." : "카메라 연결 중..."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CameraArea;