"use client"

import React, { useEffect, useState } from 'react';
import indexStyle from "@/styles/index.module.css";
import { Swiper, SwiperSlide } from 'swiper/react';
import { A11y, Pagination, Scrollbar } from 'swiper/modules';
import "swiper/css";
import Lottie from 'react-lottie-player';
import CarInfo from './CarInfo';
import Seat from './3d_model_component/Seat';
import { Canvas, useThree } from '@react-three/fiber';
import Wheel from './3d_model_component/Wheel';
import axios from 'axios';



// 파일 상단에 추가 (변수 선언)
let websocketInstance = null;
let prevDistraction = null;
let prevDrowsiness = null;

const Info = ({weatherData, data, setDrowsiness, setDistraction, drowness, distraction}) => {

  const [monitoringStatus, setMonitoringStatus] = useState(false);
  const [guest, setguest] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [seatPosArr, setSeatPosArr] = useState([0.2, -1, 0]);
  const [handlePosArr, setHandlePosArr] = useState([0.2, 0.5, -0.5]);
  const [videoSrc, setVideoSrc] = useState(''); // 비디오 소스 상태 추가
  const [videoKey, setVideoKey] = useState(0);



  // ✅ 현재 모니터링 상태 초기화
  useEffect(() => {
    setIsClient(true);
    require("swiper/css/pagination");
    
    // 서버에서 초기 모니터링 상태 가져오기
    fetch("http://localhost:8000/monitoring/status",{
      credentials: "same-origin"
    })
      .then((res) => res.json())
      .then((data) => {
        setMonitoringStatus(data.status);
      })
      .catch((err) => console.error("모니터링 상태 가져오기 실패:", err));

      fetch("http://127.0.0.1:8000/monitoring/drowsiness")
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error("🚨 API 호출 실패:", error));
  },[])


  let animationFile;
  let animationPath;

  useEffect(()=> {
    setIsClient(true);
    require("swiper/css/pagination");
  },[])

  
  // toggleMonitoring 함수를 수정합니다
  const toggleMonitoring = async () => {
    try {
      // 이미 활성화되어 있다면 소켓부터 정리
      if (monitoringStatus && websocketInstance) {
        websocketInstance.close();
        websocketInstance = null;
      }

      const response = await fetch("http://localhost:8000/monitoring/toggle", { 
        method: "GET",
        credentials: "include"
      });
      
      const data = await response.json();
      
      if (data.status === true) {
        setMonitoringStatus(true);
      } else {
        setMonitoringStatus(false);
        setDrowsiness(null);
        setDistraction(null);
        
        // 소켓 연결 확실히 종료
        if (websocketInstance) {
          websocketInstance.close();
          websocketInstance = null;
        }
        
        // 비디오 소스 초기화
        setVideoSrc('');
      }
    } catch (error) {
      console.error("⚠️ 모니터링 토글 요청 실패:", error);
      
      // 오류 발생시에도 소켓 정리
      if (websocketInstance) {
        websocketInstance.close();
        websocketInstance = null;
      }
    }
  };
  // Info.js 파일의 useEffect 수정
  // 3. 기존 useEffect를, 웹소켓 처리와 비디오 스트림 처리를 분리해서 다시 작성
  useEffect(() => {
    if (monitoringStatus) {
      // 비디오 소스 설정 (랜덤값 제거)
      setVideoSrc(`http://localhost:8000/monitoring/video_feed?ts=${Date.now()}`);
      
      // 웹소켓 연결
      const wsUrl = `ws://localhost:8000/monitoring/ws`;
      websocketInstance = new WebSocket(wsUrl);
      
      websocketInstance.onopen = () => {
        console.log('모니터링 웹소켓 연결됨');
        // 초기값은 한 번만 설정
        if (!distraction) setDistraction("양호");
        if (!drowness) setDrowsiness("양호");
      };
      
      websocketInstance.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // 주의 분산 상태 처리 (변경된 경우만)
          if (data.distraction_state && data.distraction_state !== prevDistraction) {
            prevDistraction = data.distraction_state;
            let newStatus;
            
            switch(data.distraction_state) {
              case 'danger': newStatus = '경고'; break;
              case 'warn': newStatus = '주의'; break;
              default: newStatus = '양호';
            }
            
            setDistraction(newStatus);
          }
          
          // 졸음 상태 처리 (변경된 경우만)
          if (data.drowsiness_state && data.drowsiness_state !== prevDrowsiness) {
            prevDrowsiness = data.drowsiness_state;
            let newStatus;
            
            switch(data.drowsiness_state) {
              case 'danger': newStatus = '경고'; break;
              case 'warn': newStatus = '주의'; break;
              default: newStatus = '양호';
            }
            
            setDrowsiness(newStatus);
          }
        } catch (error) {
          console.error('웹소켓 메시지 처리 오류:', error);
        }
      };
    } else {
      // 모니터링 중지 시
      setVideoSrc('');
      
      // 웹소켓 연결 종료
      if (websocketInstance) {
        websocketInstance.close();
        websocketInstance = null;
      }
      
      // 이전 상태 초기화
      prevDistraction = null;
      prevDrowsiness = null;
    }
    
    // 컴포넌트 언마운트 시 정리
    return () => {
      if (websocketInstance) {
        console.log('웹소켓 연결 정리 중...');
        websocketInstance.onclose = null; // onclose 이벤트 제거
        websocketInstance.onerror = null; // onerror 이벤트 제거
        websocketInstance.close();
        websocketInstance = null;
      }
      
      // 상태 변수도 초기화
      prevDistraction = null;
      prevDrowsiness = null;
    };
  }, [monitoringStatus]); // 의존성 배열에는 monitoringStatus만 포함
    
  const CameraController = () => {
      const { camera } = useThree();
    
      useEffect(() => {
        camera.position.set(5, 3, -4); // 🚀 카메라를 강제로 [5, 1, -4]로 설정
        camera.lookAt(0.8, 0, 0); // 📌 원점을 바라보도록 설정
      }, []);
    
      return null;
  };


  if(!isClient) return null;
  

  const weatherIcons = {
    "01d": "sunny.json",
    "01n": "night.json",
    "02d": "partly_cloudy.json",
    "02n": "cloudy(night).json",
    "03d": "cloudy(night).json",
    "03n": "cloudy(night).json",
    "04d": "partly_cloudy.json",
    "04n": "partly_cloudy.json",
    "09d": "partly_shower.json",
    "09n": "partly_shower.json",
    "10d": "rainy(night).json",
    "10n": "rainy(night).json",
    "11d": "thunder.json",
    "11n": "thunder.json",
    "13d": "snow.json",
    "13n": "snow(night).json",
    "50d": "mist.json",
    "50n": "mist.json",
  };

// ✅ 날씨 아이콘에 맞는 배경색 (그라데이션 적용)
const backgroundGradients = {
  "01d": {
    background: "linear-gradient(to bottom, #FFD700, #FF8C00)", // ☀️ 맑음 (골드 → 다크 오렌지)
    textEffect: "0 1px 2px rgba(0,0,0,0.4)", // 밝은 배경에 글자 가독성을 위한 그림자
  },
  "01n": {
    background: "linear-gradient(to bottom, #1A237E, #0D1321)", // 🌙 밤 맑음 (딥 네이비 → 미드나이트)
    textEffect: "0 0 8px rgba(255,255,255,0.4)", // 어두운 배경에 글로우 효과
  },
  "02d": {
    background: "linear-gradient(to bottom, #90CAF9, #5C9CE6)", // 🌤 구름 조금 (밝은 하늘색 → 중간 블루)
    textEffect: "0 1px 1px rgba(0,0,0,0.3)", // 중간 밝기 배경에 약한 그림자
  },
  "02n": {
    background: "linear-gradient(to bottom, #37474F, #263238)", // 🌙 밤 구름 (그레이 블루 → 다크 슬레이트)
    textEffect: "0 0 6px rgba(255,255,255,0.3)", // 어두운 배경에 약한 글로우
  },
  "03d": {
    background: "linear-gradient(to bottom, #BBDEFB, #81D4FA)", // ☁️ 흐림 (라이트 블루 → 스카이 블루)
    textEffect: "0 1px 2px rgba(0,0,0,0.25)", // 밝은 배경에 약한 그림자
  },
  "03n": {
    background: "linear-gradient(to bottom, #455A64, #1C313A)", // 🌙 밤 흐림 (블루 그레이 → 다크 블루)
    textEffect: "0 0 5px rgba(255,255,255,0.25)", // 어두운 배경에 약한 글로우
  },
  "04d": {
    background: "linear-gradient(to bottom, #B0BEC5, #78909C)", // 🌥 구름 많음 (밝은 블루 그레이 → 미디움 그레이)
    textEffect: "0 1px 1px rgba(0,0,0,0.2), 0 0 1px rgba(0,0,0,0.3)", // 중간 톤 배경에 섬세한 그림자
  },
  "04n": {
    background: "linear-gradient(to bottom, #37474F, #102027)", // 🌙 밤 구름 많음 (다크 블루 그레이 → 차콜)
    textEffect: "0 0 6px rgba(255,255,255,0.3)", // 어두운 배경에 글로우
  },
  "09d": {
    background: "linear-gradient(to bottom, #64B5F6, #1E88E5)", // 🌧️ 소나기 (블루 → 로열 블루)
    textEffect: "0 1px 2px rgba(0,0,0,0.3), 0 0 4px rgba(255,255,255,0.2)", // 중간 톤 배경에 복합 효과
  },
  "09n": {
    background: "linear-gradient(to bottom, #0D47A1, #051C33)", // 🌙 밤 소나기 (네이비 → 미드나이트 블루)
    textEffect: "0 0 7px rgba(255,255,255,0.35)", // 어두운 배경에 강한 글로우
  },
  "10d": {
    background: "linear-gradient(to bottom, #42A5F5, #0D47A1)", // 🌦️ 비 (블루 → 딥 블루)
    textEffect: "0 1px 2px rgba(0,0,0,0.3), 0 0 3px rgba(255,255,255,0.2)", // 중간 톤 배경에 복합 효과
  },
  "10n": {
    background: "linear-gradient(to bottom, #1A237E, #071330)", // 🌙 밤 비 (인디고 → 딥 네이비)
    textEffect: "0 0 8px rgba(255,255,255,0.4)", // 어두운 배경에 강한 글로우
  },
  "11d": {
    background: "linear-gradient(to bottom, #5E35B1, #311B92)", // ⛈️ 천둥 번개 (바이올렛 → 딥 퍼플)
    textEffect: "0 0 10px rgba(255,255,255,0.45), 0 0 5px rgba(255,255,255,0.3)", // 번개 효과를 위한 강한 글로우
  },
  "11n": {
    background: "linear-gradient(to bottom, #4A148C, #12005E)", // 🌙 밤 천둥 번개 (퍼플 → 다크 퍼플)
    textEffect: "0 0 12px rgba(255,255,255,0.5), 0 0 6px rgba(255,255,255,0.35)", // 밤 번개 효과를 위한 더 강한 글로우
  },
  "13d": {
    background: "linear-gradient(to bottom, #E3F2FD, #BBDEFB)", // ❄️ 눈 (아주 밝은 블루 → 라이트 블루)
    textEffect: "0 1px 3px rgba(0,0,0,0.2), 0 0 2px rgba(0,0,0,0.1)", // 밝은 배경에 섬세한 그림자
  },
  "13n": {
    background: "linear-gradient(to bottom, #CFD8DC, #90A4AE)", // 🌙 밤 눈 (라이트 그레이 → 그레이 블루)
    textEffect: "0 1px 2px rgba(0,0,0,0.25), 0 0 3px rgba(255,255,255,0.2)", // 중간 밝기 배경에 복합 효과
  },
  "50d": {
    background: "linear-gradient(to bottom, #ECEFF1, #CFD8DC)", // 🌫 안개 (오프 화이트 → 라이트 그레이)
    textEffect: "0 0 5px rgba(255,255,255,0.5), 0 1px 3px rgba(0,0,0,0.2)", // 안개 효과를 위한 흐릿한 글로우와 그림자
  },
  "50n": {
    background: "linear-gradient(to bottom, #90A4AE, #546E7A)", // 🌙 밤 안개 (그레이 블루 → 블루 그레이)
    textEffect: "0 0 8px rgba(255,255,255,0.4), 0 1px 2px rgba(0,0,0,0.3)", // 밤 안개 효과를 위한 강한 글로우와 그림자
  }
  };

  

  // ✅ public 폴더 내 JSON 파일 경로 설정
  if(weatherData) {
    animationFile = weatherIcons[weatherData?.weather?.[0]?.icon] || "sunny.json";
    animationPath = `/weather_animation/${animationFile}`; // public 폴더 기준 URL 접근  
  }


  return (
    <div className={indexStyle.infoContainer}>
      <div className={indexStyle.btnArea}>
          <button onClick={() => {
            if(data.authenticated) {
              toggleMonitoring()
            } else {
              alert("로그인을 해주세요!")
            }
          }}>
            모니터링 : {data.authenticated ? 
            <span style={{ 
              color: monitoringStatus ? "green" : "red",
              fontWeight: 'bold'
            }}>
            {monitoringStatus ? "🟢 활성화됨" : "🔴 비활성화됨"}
            </span> :
            <span>사용자 인증 필요</span>
          }
          </button>
          <button onClick={()=> setguest(!guest)}>게스트 모드 : <span>{guest ? "켜짐" : "꺼짐"}</span></button>
      </div>

      {/* 모니터링 비디오 피드 추가 */}
      <div className={indexStyle.monitoringBox} style={{ display: monitoringStatus ? 'block' : 'none' }}>
        {videoSrc && (
          <img 
            src={videoSrc} 
            alt="Monitoring Stream" 
            style={{ opacity: monitoringStatus ? 1 : 0, transition: 'opacity 0.3s ease' }}
          />
        )}
      </div>

      <div className={indexStyle.contentArea}>
        <Swiper
          spaceBetween={20}
          slidesPerView={1}
          pagination={{clickable: true}}
          scrollbar={{ draggable: true }}
          loop={true}
          modules={[Pagination, Scrollbar, A11y]}
          className={indexStyle.slideContainer}
        >
          <SwiperSlide 
            className={indexStyle.slide1}
            style={{
                "--bg-color": backgroundGradients[weatherData?.weather?.[0]?.icon]?.background || "#ffffff",
                "--bg-textShadow": backgroundGradients[weatherData?.weather?.[0]?.icon]?.textEffect
            }}>
            <div>
              <div className={indexStyle.weatherName}>{weatherData?.weather?.[0]?.description}</div>
              <div className={indexStyle.weatherContainer}>
                <Lottie
                  loop
                  path={animationPath} // ✅ URL 방식으로 JSON 파일 로드
                  play
                  style={{ width: "50%", height: "50%" }}
                />
                <div className={indexStyle.temp}>{Math.floor(weatherData?.main?.temp)} °C</div>
              </div>
              <div className={indexStyle.cityName}>
                {weatherData?.name}
              </div>
              <div className={indexStyle.weatherInfo}>
                <div className={indexStyle.wind}>
                  <div>바람</div> <div>{weatherData?.wind?.speed} m/s</div>
                </div>
                <div className={indexStyle.humidity}>
                  <div>습도</div><div>{weatherData?.main?.humidity} %</div>
                </div>
                <div>
                  <div>일출</div>
                  <div>
                    {weatherData?.sys?.sunrise ? new Date(weatherData.sys.sunrise * 1000).toLocaleTimeString("ko-KR", {
                      hour: "2-digit",
                      hour12: true
                    }) : ''}
                  </div>
                </div>
                <div>
                  <div>일몰</div>
                  <div>
                    {weatherData?.sys?.sunset ? new Date(weatherData.sys.sunset * 1000).toLocaleTimeString("ko-KR", {
                      hour: "2-digit",
                      hour12: true
                    }) : ''}
                  </div>
                </div>
              </div>
            </div>
          </SwiperSlide>
          <SwiperSlide className={`${indexStyle.slide2}`}>
            <CarInfo></CarInfo>
          </SwiperSlide>
          <SwiperSlide className={`${indexStyle.slide3}`}>
            <div className={indexStyle.title}>시트 위치 상태</div>
            <div>
              <Canvas style={{ width: "100%", height: "475px" }} camera={{
                fov:45
              }}>
                <CameraController/>
                <ambientLight intensity={10} />
                <pointLight position={[10, 10, 5]} />
                <Seat position={seatPosArr} />
                <Wheel seat={"seat"} position={handlePosArr} />
              </Canvas>
            </div>
          </SwiperSlide>
        </Swiper>
      </div>
    </div>
  )
}

export default React.memo(Info)