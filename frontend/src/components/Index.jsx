"use client"

import React, { useCallback, useEffect, useState } from 'react';
import indexStyle from "@/styles/index.module.css";
import Icon from '@mdi/react';
import { mdiSeatbelt, mdiSleep } from '@mdi/js';
import { Settings, Visibility } from '@mui/icons-material';
import Music from "@/components/Music";
import { usePathname, useRouter } from 'next/navigation';
import Script from 'next/script';
import dynamic from 'next/dynamic';
import axios from 'axios';

const Index = ({data}) => {

  const router = useRouter();
  const pathname = usePathname();

  const kakaoKey = '47ffcb893810b21a7c342f3d94acf09c';
  const weatherKey = '92e0ae79f3a498b4bac9addc969c7c8f';

  const [coords, setCoords] = useState({ lat: null, lon: null });
  const [weatherData, setWeatherData] = useState({});
  const [isKakaoLoaded, setIsKakaoLoaded] = useState(false);
  const [isBrowser, setIsBrowser] = useState(false);
  const [host, setHost] = useState(null);
  const [drowness,setDrowsiness] = useState(null);
  const [distraction,setDistraction] = useState(null);
  const [InfoComponent, setInfoComponent] = useState(null);

  useEffect(() => {
    // 컴포넌트를 한 번만 동적으로 로드
    if (!InfoComponent) {
      const loadComponent = async () => {
        const Component = (await import("@/components/Info")).default;
        setInfoComponent(() => Component);
      };
      loadComponent();
    }
  }, [InfoComponent]);


  // 컴포넌트 내부에서
  const setDrowsinessCallback = useCallback((value) => {
    setDrowsiness(value);
  }, []);

  const setDistractionCallback = useCallback((value) => {
    setDistraction(value);
  }, []);

  // First useEffect to set isBrowser
  useEffect(() => {

    const savedLayout = localStorage.getItem('layout_login_page');
    if (savedLayout) {
      const { streamActive, faceDetected } = JSON.parse(savedLayout);
      // 상태 복원
    }

    const needsRefresh = localStorage.getItem('needsRefresh');
    if(needsRefresh === 'true') {
      localStorage.removeItem('needsRefresh');
      router.refresh();
    }
    setIsBrowser(true);
    setHost(window.location.hostname);
  }, []);

  // Get user location only on the client side
  useEffect(() => {
    if (!isBrowser) return;
    
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          console.log(latitude, longitude);
          setCoords({ lat: latitude, lon: longitude });
          console.log("좌표 설정완료")
        },
        (error) => console.error("위치 가져오기 실패:", error),
        { enableHighAccuracy: true }
      );
    } else {
      console.error("Geolocation을 지원하지 않는 브라우저입니다.");
    }
  }, [isBrowser]);


  // 지도 초기화 부분 수정
  useEffect(() => {
    if (!isBrowser || !coords.lat || !coords.lon || !window.kakao?.maps) return;
    
    const container = document.getElementById("map");
    if (!container) return;
    
    try {
      const options = {
        center: new window.kakao.maps.LatLng(coords.lat, coords.lon),
        level: 3,
      };
      new window.kakao.maps.Map(container, options);
    } catch (e) {
      console.error('지도 초기화 실패:', e);
    }
  }, [isBrowser, coords.lat, coords.lon, isKakaoLoaded]);

  useEffect (() => {
    const fetchWeather = async () => {

      if (!coords.lat || !coords.lon) return;

      try {

        console.log("받아온 좌표 : ",coords)

        const res = await axios.get(
          `https://api.openweathermap.org/data/2.5/weather?lat=${coords.lat}&lon=${coords.lon}&appid=${weatherKey}&units=metric&lang=kr`
        );

        const data = res.data;
        if (data) {
          console.log("날씨 데이터:", data);
          setWeatherData(data);
        }
      } catch (error) {
        console.error("날씨 데이터 불러오기 실패!", error);
      }
    };

    fetchWeather();
  },[coords.lat,coords.lon])
  
  const handleKakaoMapLoaded = () => {
    console.log("카카오맵 로드 완료!");
    window.kakao.maps.load(() => {
      setIsKakaoLoaded(true);
    });
  };

  const logout = () => {
    axios.get(`http://${host}:8000/logout`, {
      withCredentials: true
    }).then(res => {
      const data = res.data
      if(!data.authenticated) {
        router.refresh()
      }
    }).catch(err => console.error(err))
  }
  return (
    <div key={pathname}>
      <div className={indexStyle.header}>
        <div className={indexStyle.rightIcons}>
          <div className={indexStyle.status}>
            <Icon path={mdiSleep} />
            <div className={indexStyle.text}>{!drowness ? "오프라인" : drowness}</div>
             <div className={`${indexStyle.statusBall} 
                            ${drowness == "양호" && indexStyle.green} 
                            ${drowness == "주의" && indexStyle.yellow} 
                            ${drowness == "경고" && indexStyle.red}`}>
            </div>
          </div>
          <div className={indexStyle.status}>
            <Visibility />
            <div className={indexStyle.text}>{!distraction ? "오프라인" : distraction}</div>
            <div className={`${indexStyle.statusBall} 
                            ${distraction == "양호" && indexStyle.green} 
                            ${distraction == "주의" && indexStyle.yellow} 
                            ${distraction == "경고" && indexStyle.red}`}>
            </div>
          </div>
        </div>
        <div className={indexStyle.leftIcons}>
          {data.authenticated ? 
            <div className={indexStyle.login} onClick={() => logout()}>로그아웃</div> :
            <div className={indexStyle.login} onClick={() => router.push("/login")}>로그인</div>}
          <div
            className={indexStyle.status}
            onClick={() => {
              if(data.item) {
                router.push("/setting");
              } else {
                alert("로그인을 해주세요!")
              }
            }}
          >
            <Settings />
          </div>
        </div>
      </div>
      <div className={indexStyle.container}>
        {isBrowser && (
          <Script
            strategy="afterInteractive"
            src={`//dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoKey}&autoload=false`}
            onLoad={handleKakaoMapLoaded}
          />
        )}
        <div className={indexStyle.map} id="map"></div>
        <div className={indexStyle.side}>
        {isBrowser && InfoComponent && 
              <InfoComponent
                weatherData={weatherData || {}}
                data={data || {}}
                setDrowsiness={setDrowsiness}
                setDistraction={setDistraction}
                distraction={distraction}
                drowness={drowness}
              />
            }
          <Music />
        </div>
      </div>
    </div>
  );
};

export default Index;