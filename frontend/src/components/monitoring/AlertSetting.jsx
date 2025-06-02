import React, { useState } from 'react'
import monitoringStyle from "@/styles/monitoring.module.css"
import AlertBox from './AlertBox';
import { useRouter } from 'next/navigation';

const AlertSetting = () => {
    const router = useRouter();
    const [select,setSelect] = useState(0);
    const tabs = ['노래','목소리','경고음'];
    const [slideArr,setSlideArr] = useState(
      [
        {name:"졸음상태",status:false},
        {name:"주의분산",status:false},
        {name:"좌석벨트",status:false}
      ]
    ) 


    const changeStatus = (index) => {
      setSlideArr(prev => prev.map((item, i) =>
        i === index ? {...item,status: !item.status} : item) 
      )
    }

  return (
    <div className={monitoringStyle.alertContainer}>
        <div className={monitoringStyle.title}>알람음 선택</div>
        <div className={monitoringStyle.btnBox}>
           {tabs.map((label,index) => (
             <span key={index} onClick={() => setSelect(index)}>{label}</span>
           ))}
            <div 
                className={monitoringStyle.selectedAlert}
                style={{transform: 
                    `translateX(calc(${select} * 100%))`
                }}
            >
            </div>
        </div>
       
        <AlertBox select={select}></AlertBox>
        <div className={monitoringStyle.detectSetBtns}>
          {slideArr.map((item, index) => (
              <div key={index}>
                <span>{item.name}</span>
                <div className={`${monitoringStyle.slideBtn} ${item.status ? monitoringStyle.slideOn : ""}`} onClick={()=>changeStatus(index)}>
                  <div className={`${monitoringStyle.slideCircle}`}
                    style={{transform:`translateX(${item.status ? 120 : 0}%`}}
                  ></div>
                </div>
              </div>
          ))}
        </div>
    </div>
  )
}

export default AlertSetting