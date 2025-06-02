import React, { useEffect, useRef, useState } from 'react'
import profileStyle from "@/styles/profile.module.css"
import ColorPicker from 'react-best-gradient-color-picker';

const SetColor = ({color,setColor}) => {
    const [showPicker, setShowPicker] = useState(false);
    

    const pickerRef = useRef(null); // ColorPicker 감지

    useEffect(() => {
        function handleClickOutside(event) {
          if (pickerRef.current && !pickerRef.current.contains(event.target)) {
            setShowPicker(false); // 바깥 클릭하면 닫기
          }
        }
    
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
          document.removeEventListener("mousedown", handleClickOutside);
        };
      }, []);

 return (
    <div className={profileStyle.setColorContainer}>
        <div className={profileStyle.colorBox}
        style={{backgroundColor: color}}
        onClick={() => setShowPicker(true)}>
        </div>
        <div className={profileStyle.colorAlert}>클릭하여 색상을 선택해주세요</div>

        {showPicker && (
            <div className={profileStyle.setColor} ref={pickerRef}>
                <ColorPicker 
                    value={color} 
                    onChange={(e) => setColor(e)}
                    width={294}
                    height={200}
                    hideGradientControls={true}
                />
            </div>
        )}
    </div>
  )
}

export default SetColor