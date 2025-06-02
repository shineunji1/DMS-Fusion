import React from 'react'
import faceRecogStyle from "@/styles/faceRecog.module.css"

const Progress = () => {
  return (
    <>
        <div className={faceRecogStyle.progressBox}>
            <div className={faceRecogStyle.progressBar}>
            </div>
            <div className={faceRecogStyle.progressStatus}>
                <div>
                    <span>정면</span>
                    <div className={faceRecogStyle.progressEclipse}></div>
                </div>
                <div>
                    <span>좌측</span>
                    <div className={faceRecogStyle.progressEclipse}></div>
                </div>
                <div>
                    <span>우측</span>
                    <div className={faceRecogStyle.progressEclipse}></div>
                </div>
            </div>
        </div>
    </>
  )
}

export default Progress