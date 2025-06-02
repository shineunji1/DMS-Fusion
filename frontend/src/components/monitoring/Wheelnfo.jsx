"use client"

import React, { useEffect, useState } from 'react'
import Wheel from "@/components/3d_model_component/Wheel"
import monitoringStyle from "@/styles/monitoring.module.css"
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import gsap from 'gsap'

const Wheelnfo = () => {
  const [moveEnd, setMoveEnd] = useState(false);

  const WheelZoom = () => {
    const {camera, scene} = useThree();

    useEffect(() => {
      const target = scene.children[0]; 

      // 카메라 줌인 애니메이션
      gsap.to(camera.position, {
        x:-1, y:2, z:2,
        duration:2,
        ease: "power2.inOut",
        onUpdate: () => {
          camera.lookAt(target.position);
        },
        onComplete: () => {
          setMoveEnd(true);
        }
     })
    },[])
    return null;
  }
  return (
    <div className={monitoringStyle.threeContainer}>
      <Canvas
              camera={{ position: [0, 2, 5], fov: 20 }}
              style={{ width: "100%", height: "100%" }}
          >   
              <ambientLight intensity={50}/>
              <pointLight position={[10, 10, 5]}/>
              <Wheel position={[0, 0, 0]}/>
              <WheelZoom/>
      </Canvas>
      <div className={monitoringStyle.info} 
           style={{display: `${moveEnd ? "block" : "none"}`}}
      >
        해당 버튼을 통해 조작해 주세요
      </div>
    </div>
  )
}

export default Wheelnfo