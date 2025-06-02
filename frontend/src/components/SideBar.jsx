"use client"
import React, { useEffect, useState } from 'react'
import sideBarStyle from "@/styles/side.module.css"
import { AutoGraph, CheckCircle, Map, Settings } from '@mui/icons-material';
import BannerSVG from "../../public/MOCA.svg"
import { usePathname, useRouter } from 'next/navigation';

const SideBar = ({data}) => {

  const router = useRouter();
  const pathname  = usePathname();
  const [select,setSelect] = useState("");

  useEffect(()=> {
    setSelect(pathname);
  },[pathname])

  const movePage = (pageName) => {
    if(data) {
      router.push(`./setting/${pageName}`);
    } else {
      alert("로그인을 해주세요!")
    }
  }


  return (
    <div className={sideBarStyle.container}>
        <div className={sideBarStyle.banner}>
          <BannerSVG  
            viewBox="0 0 300 70" 
            preserveAspectRatio="xMidYMid meet"
            onClick = {() => {
              router.push("/");
              router.refresh();
            }}>
          </BannerSVG>
        </div>
        <div className={sideBarStyle.navContainer}>
          <ul>
            <li onClick={() => movePage("monitoring")} className={`${select == "/setting/monitoring" ? sideBarStyle.select : null}`}><AutoGraph/><span>모니터링 설정</span></li>
            <li onClick={() => movePage("face-reset")} className={`${select == "/setting/face-reset" ? sideBarStyle.select : null}`}><CheckCircle/>얼굴 초기화</li>
            <li onClick={() => movePage("seat-set")} className={`${select == "/setting/seat-set" ? sideBarStyle.select : null}`}><Map/>의자 설정</li>
            <li onClick={() => movePage("profile")} className={`${select == "/setting/profile" ? sideBarStyle.select : null}`}><Settings/>프로필 설정</li>
          </ul>
        </div>
    </div>
  )
}

export default SideBar