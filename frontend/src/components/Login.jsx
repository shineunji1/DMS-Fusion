"use client"

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import loginStyle from "@/styles/login.module.css" 
import BannerSVG from "../../public/MOCA.svg"
import SideBar from './SideBar'
import ManualVerify from "@/components/Modal/ManualVerify"
import axios from "axios";
import { resolve } from "path";

const Login = () => { 
  const router = useRouter();
  const [loading, setLoading] = useState(false); 
  const [checking, setChecking] = useState(false); 
  const [foundUser, setFoundUser] = useState(false);
  const [pwdInput, setPwdInput] = useState(false);
  const [host, setHost] = useState(null);
  const [modal, setModal] = useState(false);

  // 페이지 로드 시 웹캠 스트리밍 실행
  useEffect(()=>{
    const savedLayout = localStorage.getItem('layout_login_page');
    if (savedLayout) {
      const { streamActive, faceDetected } = JSON.parse(savedLayout);
      // 상태 복원
    }
    setHost(window.location.hostname);
  }, []);

   // 얼굴 인증 버튼 클릭 시 Face ID 요청
   const handleFaceIDLogin = async () => {
    console.log("얼굴인증 중😊")
    setLoading(true);
    setChecking(true);

    try {
      // 얼굴 벡터값 받아오기
          const captureResponse = await fetch(`http://${host}:8000/login/capture-face`);
          const captureResult = await captureResponse.json();
    
          if(!captureResponse.ok || !captureResult.embedding){
            alert("얼굴 인증 실패!")
            throw new Error("얼굴 캡쳐 실패");
          }
    
          const startTime = Date.now();
          
          if (captureResult.embedding) {
            axios.post("http://localhost:8000/login/face-id",{
              embedding: captureResult.embedding
            },{
              withCredentials:true,
              headers:{
                "Content-Type":"application/json"
              }
            }).then(res => {
                const data = res.data
                if(data.success) {
                  setFoundUser(true);
                } else {
                  alert("얼굴 인증 실패!")
                }
            }).catch(error => {
              console.error(error)
            })
          }
        setChecking(false);
        setLoading(false);
    

  }catch(err){
    console.error(err);
  }finally{
    setChecking(false);
    setLoading(false);
  }
};

useEffect(()=> {
  if(foundUser) {
    console.log("유저 일치")
    setTimeout(() => {
      localStorage.setItem('needsRefresh', 'true');
      router.replace("/")
    }, 200);
  }
},[foundUser])

const handleRegister = async () => {
  router.replace("/signup/face-set")
};


const manualVerify = () => {
  console.log("모달 on")
  setModal(!modal);
}

  return (
    <div className={loginStyle.content}>
      <SideBar></SideBar>
      <div className={loginStyle.contentBox}>
        <div className={loginStyle.container}>
          <div className={loginStyle.banner}><BannerSVG></BannerSVG></div>
          <h2>얼굴인증을 해주세요</h2>

          {/* 얼굴 인증 버튼 */}
          <div className={loginStyle.btnBox}>
            <div className={loginStyle.btn} onClick={handleFaceIDLogin}>
            {loading
              ? checking
                ? <div>얼굴 확인 중</div>
                : <div>인증 중...</div>
              : <div>얼굴 인증</div>}
          </div>

            <div className={loginStyle.btn} onClick={handleRegister}>
              <div>사용자 등록</div>
            </div>
          </div>
          <div className={loginStyle.btnBox}>
            <div className={loginStyle.btn} onClick={manualVerify}>
              <div>수동 인증</div>
            </div>
          </div>
        </div>
      </div>

      {modal && <ManualVerify setModal = {setModal}/>}
    </div>
  )
}

export default Login