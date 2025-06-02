"use client"

import React from 'react'
import settingStyle from "@/styles/setting.module.css"
import { Swiper, SwiperSlide } from 'swiper/react'
import "swiper/css"
import { EffectCoverflow, Pagination } from 'swiper/modules'
import Image from 'next/image'

// menu icon path
import MonitoringIcon from "../../public/menu_icon/main/monitoring.png"
import FaceIcon from "../../public/menu_icon/main/face_rest.png"
import SeatIcon from "../../public/menu_icon/main/sheet_set.png"
import SettingIcon from "../../public/menu_icon/main/profile_update.png"
import { useRouter } from 'next/navigation'

const Setting = () => {

  const router = useRouter();

  const movePage = (pageName) => {
    router.push(`/setting/${pageName}`);
  }

  return (
        <div className={settingStyle.container}>
        <Swiper
        loop={false}
        spaceBetween = {20} 
        slidesPerView="auto"
        pagination = {{clickable:true}} 
        navigation = {true}
        effect='coverflow'
        grabCursor={true}
        centeredSlides={false}
        coverflowEffect={{
          rotate: 0,
          stretch: 50,
          depth: 100,
          modifier: 1,
          slideShadows:true,
        }}
        modules={[EffectCoverflow]}
        className={settingStyle.swiperContainer}
        >
          
          <SwiperSlide 
            className={settingStyle.slide1}
            onClick={() => movePage("monitoring")}
          >
            <div className={settingStyle.menuTitle}>
              모니터링 설정
              </div>
            <Image src={MonitoringIcon}  alt='Monitoring Icon'/>
          </SwiperSlide>
          <SwiperSlide className={settingStyle.slide2} 
                        onClick={() => movePage("face-reset")}>
            <div className={settingStyle.menuTitle}>얼굴 초기화</div>
            <Image src={FaceIcon}  alt='Face Icon'/>
          </SwiperSlide>
          <SwiperSlide className={settingStyle.slide3}
                        onClick={() => movePage("seat-set")}>
            <div className={settingStyle.menuTitle}>의자 설정</div>
            <Image src={SeatIcon}  alt='Seat Icon'/>
          </SwiperSlide>
          <SwiperSlide className={settingStyle.slide4}
                        onClick={() => movePage("profile")}>
            <div className={settingStyle.menuTitle}>프로필설정</div>
            <Image src={SettingIcon}  alt='Setting Icon'/>
          </SwiperSlide>
      </Swiper>
      </div>
  )
}

export default Setting