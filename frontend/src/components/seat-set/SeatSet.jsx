"use client"
import { Canvas, useThree } from '@react-three/fiber';
import React, { useEffect, useState } from 'react';
import * as THREE from 'three';
import seatSetStyle from "@/styles/seatSet.module.css";
import axios from "axios";

// 3D Model
import Seat from "@/components/3d_model_component/Seat";
import Wheel from '../3d_model_component/Wheel';
import { OrbitControls } from '@react-three/drei';

const SeatSet = ({ userId }) => {
  console.log("🟢 현재 로그인된 userId:", userId);
  const [seatPosArr, setSeatPosArr] = useState([0.2, -1, 0]);
  const [handlePosArr, setHandlePosArr] = useState([0.2, 0.5, -0.5])
  const [btnValue, setBtnValue] = useState("");
  const [headVal, setHeadVal] = useState(0);
  const [backVal, setBackVal] = useState(0);
  const [changeVal, setChangeVal] = useState("head");


  // ✅ FastAPI에서 데이터 가져오기
  useEffect(() => {
    async function fetchSeatSettings() {
      try {
        const response = await axios.get(`http://127.0.0.1:8000/seat-set/${userId}`);
        const seatData = response.data;
        console.log("✅ FastAPI에서 받은 좌석 데이터:", seatData);
        if (seatData) {
          setSeatPosArr([
            seatData["좌석"]?.["좌우"] ?? 0.2,
            seatData["좌석"]?.["상하"] ?? -1,
            seatData["좌석"]?.["전후"] ?? 0.0
          ]);
          setHandlePosArr([
            seatData["핸들"]?.["좌우"] ?? 0.2,
            seatData["핸들"]?.["상하"] ?? 0.5,
            seatData["핸들"]?.["전후"] ?? -0.5
          ]);
          setHeadVal(seatData["머리"]?.["각도"] ?? 0);
          setBackVal(seatData["등받이"]?.["각도"] ?? 0);
        }
      } catch (error) {
        console.error("🚨 좌석 설정을 불러오지 못했습니다:", error);
      }
    }
    fetchSeatSettings(); // ✅ 컴포넌트 마운트 시 FastAPI 호출
  }, [userId]); // ✅ userId가 바뀔 때마다 호출



  const CameraController = () => {
    const { camera } = useThree();
  
    useEffect(() => {
      camera.position.set(5, 3, -4); // 🚀 카메라를 강제로 [5, 1, -4]로 설정
      camera.lookAt(0, 0, 0); // 📌 원점을 바라보도록 설정
      camera.fov = Math.PI/6;
    }, []);
  
    return null;
  };

  const handleBtn = (value) => {
    let adjustment = {};  // FastAPI에 전달할 값
    let position = changeVal; // 선택된 변경 위치 (head, back, seat, handle)
       
    if(changeVal == "head") {
      if(value == "plus") {
        setHeadVal((prev) => Math.min(prev + 1, 6));
        setBtnValue(value);
        adjustment = { "각도": 1 };
      } else if (value == "minus") {
        setHeadVal((prev) => Math.max(prev - 1, 0));
        setBtnValue(value);
        adjustment = { "각도": -1 };
      } 
  } else if (changeVal == "back") {
    if(value == "plus") {
      setBackVal((prev) => Math.min(prev + 1, 6));
      setBtnValue(value);
      adjustment = { "각도": 1 };
    } else if (value == "minus") {
      setBackVal((prev) => Math.max(prev - 1, 0));
      setBtnValue(value);
      adjustment = { "각도": -1 };
    } 
  } else if (changeVal == "seat") {
    if(value == "plus") {
      setSeatPosArr(prev => prev.map((value, index) => index === 2 ? value - 0.02 : value))
      adjustment = { "전후": 0.02 };
    }
    else if(value == "minus") {
      setSeatPosArr(prev => prev.map((value, index) => index === 2 ? value + 0.02 : value))
      adjustment = { "전후": -0.02 };
    }
    else if(value == "up") {
      setSeatPosArr(prev => prev.map((value, index) => index === 1 ? value + 0.02 : value))
      adjustment = { "상하": 0.02 };
    }
    else if(value == "down") {
      setSeatPosArr(prev => prev.map((value, index) => index === 1 ? value - 0.02 : value))
      adjustment = { "상하": -0.02 };
    }
  } else if (changeVal == "handle") {
    if(value == "plus") {
      setHandlePosArr(prev => prev.map((value, index) => index === 2 ? value - 0.02 : value))
      adjustment = { "전후": 0.02 };
    }
    else if(value == "minus") {
      setHandlePosArr(prev => prev.map((value, index) => index === 2 ? value + 0.02 : value))
      adjustment = { "전후": -0.02 };
    }
    else if(value == "up") {
      setHandlePosArr(prev => prev.map((value, index) => index === 1 ? value + 0.02 : value))
      adjustment = { "상하": 0.02 };
    }
    else if(value == "down") {
      setHandlePosArr(prev => prev.map((value, index) => index === 1 ? value - 0.02 : value))
      adjustment = { "상하": -0.02 };
    }
  }

  }

  const reset = () => {
    setHeadVal(0);
    setBackVal(0);
    setSeatPosArr([0.2, -1, 0]);
    setHandlePosArr([0.2, 0.5, -0.5]);
  }

    // 좌석 설정 업데이트 함수
    const updateSeat = async () => {
      try {
        const seatData = {
          "좌석": {
            "좌우": seatPosArr[0],
            "상하": seatPosArr[1],
            "전후": seatPosArr[2]
          },
          "핸들": {
            "좌우": handlePosArr[0],
            "상하": handlePosArr[1],
            "전후": handlePosArr[2]
          },
          "머리": {
            "각도": headVal
          },
          "등받이": {
            "각도": backVal
          }
        };
              
      console.log("📤 업데이트할 데이터:", seatData);
      const response = await axios.post(`/api/seat-set`, seatData);
      console.log("✅ 좌석 설정 업데이트 성공:", response.data);
      alert("좌석 설정이 저장되었습니다!");
    } catch (error) {
      console.error("🚨 좌석 설정 업데이트 실패:", error);
      alert("좌석 설정 저장에 실패했습니다.");
    }

        // 함수 끝에서 서버에 업데이트 요청 보내기
        if(Object.keys(adjustment).length > 0) {
          updateSeatSetting(userId, position, adjustment)
            .catch(error => console.error("업데이트 실패:", error));
        }
    
  };

  return (
    <div className={seatSetStyle.container}>
      <Canvas style={{ width: "50%", height: "100%" }}>
        <CameraController/>
        <ambientLight intensity={10} />
        <pointLight position={[10, 10, 5]} />
        <Seat position={seatPosArr} 
          value={btnValue} 
          changeVal = {changeVal}
          headVal = {headVal}
          backVal = {backVal}
        />
        <Wheel seat={"seat"} position={handlePosArr} />
      </Canvas>
     <div className={seatSetStyle.controllBox}>
     <div>  
            <div className={seatSetStyle.subtitle}>변경 위치</div>
            <select defaultValue={changeVal} onChange={e => {
              setChangeVal(e.target.value);
            }} >
              <option value="head">머리</option>
              <option value="back">등받이</option>
              <option value="seat">좌석</option>
              <option value="handle">핸들</option>
            </select>
        </div>
      <div>
          <div className={seatSetStyle.subtitle}>조정 버튼</div>
          <div className={seatSetStyle.btnContainer}>
            <button onClick={()=> handleBtn("plus")}>
              앞
            </button>
            <button onClick={() => handleBtn("minus")}>
              뒤
            </button>
            {
              changeVal === "seat"  && <>
                <button onClick={() => handleBtn("up")}>위</button>
                <button onClick={() => handleBtn("down")}>아래</button>
              </>
            }
            {
              changeVal === "handle"  && <>
                <button onClick={() => handleBtn("up")}>위</button>
                <button onClick={() => handleBtn("down")}>아래</button>
              </>
            }
          </div>
        </div>
        <div>
          <div className={seatSetStyle.subtitle}>설정 값</div>
          <div className={seatSetStyle.tableBox}>
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>머리</th>
                  <th>등받이</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>각도</td>
                  <td>{headVal}</td>
                  <td>{backVal}</td>
                </tr>
              </tbody>
            </table>
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>좌우</th>
                  <th>상하</th>
                  <th>전후</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>좌석</td>
                  {seatPosArr.map((item,index) => <td key={index}>{item.toFixed(2)}</td>)}
                </tr>
                <tr>
                  <td>핸들</td>
                  {handlePosArr.map((item,index) => <td key={index}>{item.toFixed(2)}</td>)}
                </tr>
              </tbody>
            </table>
          </div>
          <div className={seatSetStyle.resetBtn} onClick={()=> reset()}>초기화</div>
          </div>
          <div className={seatSetStyle.update} onClick={()=> updateSeat()}>수정완료</div>
     </div>
    </div>
  );
};


export default SeatSet;
