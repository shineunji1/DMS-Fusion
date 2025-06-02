import React from 'react'
import indexStyle from "@/styles/index.module.css"

const CarInfo = () => {

    const seasons = () => {
        const month = new Date().getMonth() + 1;

        switch(true) {
            case month >= 3 && month <= 5:
                return "봄";
            case month >= 6 && month <= 8:
                return "여름";
            case month >= 9 && month <= 11:
                return "가을";
            default:
                return "겨울";
        }
    }
  return (
    <div className={indexStyle.carInfoContainer}>
        <div>
            <label className={indexStyle.title}>공기압</label>
            <label>계절 <span>{seasons()}</span></label>
            <div className={indexStyle.pressure}>
                <div>
                    <div>
                        <label>전방</label>
                        <div className={indexStyle.pressureValue}>
                            <span>좌측 : <span className={indexStyle.status}>양호</span></span>
                            <span>우측 : <span className={indexStyle.status}>양호</span></span>
                        </div>
                    </div>
                </div>
                <div>
                    <div>
                        <label>후방</label>
                        <div className={indexStyle.pressureValue}>
                            <span>좌측 : <span className={indexStyle.status}>양호</span></span>
                            <span>우측 : <span className={indexStyle.status}>양호</span></span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div className={indexStyle.fuleInfo}>
            <div className={indexStyle.title}>연료 & 주행거리</div>
            <div className={indexStyle.info}>
                <div className={indexStyle.mileage}>
                    <span className={indexStyle.subtitle}>주행거리 : </span>
                    <span>19250 km</span>
                </div>
                <div className={indexStyle.fule}>
                    <span className={indexStyle.subtitle}>연료량 : </span>
                    <span>450 km</span>
                </div>
            </div>
        </div>
    </div>
  )
}

export default CarInfo