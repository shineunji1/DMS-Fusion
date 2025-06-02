import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { useGLTF } from '@react-three/drei';

const Seat = ({ position, value, changeVal, headVal, backVal, seatVal, handleVal }) => {
  const { scene } = useGLTF('/3d_model/seat/seat.gltf');
  const backGroup = useRef(new THREE.Group());
  const headPivot = useRef(new THREE.Group());

  const [head, setHead] = useState(null);
  const [shoulder, setShoulder] = useState(null);
  const [back, setBack] = useState(null);
  const [backFrame, setBackFrame] = useState(null);

  useEffect(() => {
    scene.traverse((child) => {
      if (child.isMesh) {
        child.material.map = null;
        child.material.needsUpdate = true;
        child.material.color.set('gray');
        child.material.transparent = true;
        child.material.opacity = 0.2;

        // 부품 설정
        if (child.name.includes('Node3')) {
          setHead(child);
        }
        if (child.name.includes('Node5')) {
          setShoulder(child);
        }
        if (child.name.includes('Node6')) {
          setBackFrame(child);
        }
        if (child.name.includes('Node7')) {
          setBack(child);
        }
      }
    });

    // ✅ 등받이 그룹 추가
    if (shoulder && backFrame && back) {
      backGroup.current.add(shoulder, backFrame, back);
      scene.add(backGroup.current);
      console.log(backGroup.current.position.y);
    }

    // ✅ 헤드레스트가 존재하면 피벗에 추가 (좌석과 함께 움직이도록 등받이 그룹에 추가)
    if (head) {
      headPivot.current.position.set(0, 0.55, 0); // 🚀 헤드레스트가 좌석과 붙도록 위치 조정
      head.position.set(0, -0.55, 0); // 🚀 피벗보다 살짝 아래로 배치하여 연결된 느낌 유지

      headPivot.current.add(head);
      backGroup.current.add(headPivot.current); // ✅ 등받이 그룹에 headPivot 추가
      console.log(headPivot.current.position.y);
    }

  }, [scene, head, shoulder, backFrame, back]);

  useEffect(() => {
    changePos(changeVal);
  }, [headVal,backVal]);


  const changePos = (changeValue) => {


    if(headVal == 0) {
      headPivot.current.rotation.x = THREE.MathUtils.degToRad(-headVal % 360) * 1.8;
      headPivot.current.position.y = 0.55
      headPivot.current.position.z = 0
    }

    if(backVal == 0) {
      backGroup.current.rotation.x = THREE.MathUtils.degToRad(-backVal % 360) * 1.8; 
      backGroup.current.position.y = 0
      backGroup.current.position.z = 0
    }

   if(changeValue == "head") {
      console.log(value)
        if(value == "plus") {
            if (headPivot.current) {
                headPivot.current.rotation.x = THREE.MathUtils.degToRad(-headVal % 360) * 1.8;
                headPivot.current.position.y -= Math.sin(THREE.MathUtils.degToRad(headVal)) * 0.75;
                headPivot.current.position.z += Math.cos(THREE.MathUtils.degToRad(headVal)) * 0.05;
            }
        } else {
            if (headPivot.current) {
                headPivot.current.rotation.x = THREE.MathUtils.degToRad(-headVal % 360) * 1.8; 
                headPivot.current.position.y += Math.sin(THREE.MathUtils.degToRad(headVal)) * 0.75;
                headPivot.current.position.z -= Math.cos(THREE.MathUtils.degToRad(headVal)) * 0.05;
            }
        }
    } else if (changeValue == "back") {
        if(value == "plus") {
            if (backGroup.current) {

                backGroup.current.rotation.x = THREE.MathUtils.degToRad(-backVal % 360) * 1.8;
                backGroup.current.position.y -= Math.sin(THREE.MathUtils.degToRad(backVal)) * 0.55;
                backGroup.current.position.z -= Math.cos(THREE.MathUtils.degToRad(backVal)) * 0.005;
            }
        } else {
            if (backGroup.current) {
                
                backGroup.current.rotation.x = THREE.MathUtils.degToRad(-backVal % 360) * 1.8; 
                backGroup.current.position.y += Math.sin(THREE.MathUtils.degToRad(backVal)) * 0.55;
                backGroup.current.position.z += Math.cos(THREE.MathUtils.degToRad(backVal)) * 0.005;
            }
        }
    }
  }

  return <primitive object={scene} position={position} />;
};

export default Seat;
