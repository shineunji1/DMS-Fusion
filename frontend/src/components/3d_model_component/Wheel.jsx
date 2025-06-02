"use client";
import { useGLTF } from '@react-three/drei';
// Wheel.jsx
import React, { useEffect } from 'react';

const Wheel = ({seat, position}) => {
    const {scene} = useGLTF("/3d_model/steering_wheel/scene.gltf");

    useEffect(()=> {

        scene.traverse((child) => {
          if(child.isMesh) {
            child.material.map = null;
            child.material.needsUpdate = true;
            child.material.color.set("grey");
            child.material.transparent = true;
            child.material.opacity = seat ==="seat" ? 0.3 : 0.5;
          }
        })
    },[])

    return <primitive object = {scene} scale = {2} position={position}/>
};

export default Wheel;