import React, { useState } from 'react'
import monitoringStyle from "@/styles/monitoring.module.css"

const VideoBox = ({camMove, setCamMove}) => {
    const [select,setSelect] = useState(0);
    const btnArr = ["일반" , "깊이"]
  return (
    <>
        <div className={monitoringStyle.videoBtns}>
            {btnArr.map((item,index) => (<div key={index}
                onClick={() => setSelect(index)}
            >{item}</div>))}
            <div className={monitoringStyle.selectedVideo}
                style={{transform:`translateX(calc(${select} * 100%))`}}
            ></div>
        </div>
        <div className={monitoringStyle.videoArea}>
            No Signal
        </div>
        <div 
            className={monitoringStyle.camMoveBtn}
            onClick={() => setCamMove(!camMove)}
            >
            {camMove ? "카메라 위치 수정 중" : "카메라 위치 변경" }
        </div>
    </>
  )
}

export default VideoBox