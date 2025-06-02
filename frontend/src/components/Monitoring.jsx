"use client"
import React, { useState } from 'react'
import monitoringStyle from "@/styles/monitoring.module.css"
import { CheckCircle } from '@mui/icons-material'
import AlertSetting from './monitoring/AlertSetting';
import WheelInfo from './monitoring/Wheelnfo';
import VideoBox from './monitoring/VideoBox';

const Monitoring = ({data}) => {
  console.log(data)

  const  [camMove, setCamMove] = useState(false);


  return (
    <div className={monitoringStyle.container}>
        <div className={monitoringStyle.videoContainer}>
          <VideoBox camMove = {camMove} setCamMove = {setCamMove}></VideoBox>
        </div>
        <div className={monitoringStyle.setArea}>
            {
              camMove ? <WheelInfo/> : <AlertSetting></AlertSetting>
            }
        </div>
    </div>
  )
}

export default Monitoring