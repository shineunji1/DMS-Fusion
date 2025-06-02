"use client"

import React, { useEffect, useRef, useState } from 'react'
import SetColor from "./components/SetColor"
import profileStyle from "@/styles/profile.module.css"
import axios from 'axios'
import { useRouter } from 'next/navigation'


const Profile = ({data}) => {

  const router = useRouter();

  const userNameRef = useRef("");
  const profileNameRef = useRef("");
  const pwdRef = useRef("");

  const [userId, setUserId] = useState(null);
  const [color, setColor] = useState('rgba(255,255,255,1)');

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }
  
  function deleteCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
  }
  
  useEffect(() => {
    const id = getCookie('userId');

    console.log(id)

    if (id) {
      setUserId(id);
      deleteCookie('userId');
    }
  }, []);

  // 비밀번호 유효성 검사 함수
  const isValidPassword = (pwd) => {
    // 기본 검사: 6자리 이상의 숫자
    if (!/^\d{6,}$/.test(pwd)) {
      return false;
    }
    
    // 연속된 숫자 패턴 검사 (오름차순)
    for (let i = 0; i < pwd.length - 2; i++) {
      const d1 = parseInt(pwd[i]);
      const d2 = parseInt(pwd[i+1]);
      const d3 = parseInt(pwd[i+2]);
      
      // 3자리 연속된 숫자 검사 (예: 123, 456, 789)
      if (d1 + 1 === d2 && d2 + 1 === d3) {
        return false;
      }
      
      // 3자리 역순 연속된 숫자 검사 (예: 321, 654, 987)
      if (d1 - 1 === d2 && d2 - 1 === d3) {
        return false;
      }
    }
    
    return true;
  };


  const addUser = () => {
    const userName = userNameRef.current.value;
    const profileName = profileNameRef.current.value;
    const pwd = pwdRef.current.value;

    if(isValidPassword(pwd) && userName && profileName) {
      axios.post("http://localhost:8000/login/add-profile", {
        user_id: userId,
        user_name : userName,
        profile_name: profileName,
        user_pwd: pwd,
        profile_color: color
      }, {
        withCredentials: true,
        headers: {
          "Content-Type" : "application/json"
        }
      }).then(res => {
        if(res.data.success) {
          router.replace("/login")
        }
      }).catch(err => console.error(err))
    } 
    if (isValidPassword(pwd) === false) {
      alert("비밀번호 조건이 맞지 않습니다!");
      pwdRef.current.focus();
    } 
    else if (!userName) {
      alert("이름을 입력해주세요")
      userNameRef.current.focus();
    } 
    if (!profileName) {
      alert("프로필 이름을 입력해주세요")
      profileNameRef.current.focus();
    }
    if (!pwd) {
      alert("비밀번호를 입력해주세요!")
      pwdRef.current.focus()
    }
  }

  console.log(userId)

  return (
    <div className={profileStyle.container}>
        <SetColor color={color} setColor={setColor}/>
        <div className={profileStyle.inputBox}>
          <div>
            <label>사용자 이름</label>
            <input type='text' ref={userNameRef}/>
          </div>
          <div>
            <label>프로필 이름</label>
            <input type='text' ref={profileNameRef}/>
          </div>
          <div>
            <label className={profileStyle.subtitle}>비밀번호</label>
            <input type='password' ref={pwdRef}/>
            <div className={profileStyle.pwdInfo}>비밀번호는 6자리 이상으로 입력하며 연속된 숫자는 안됩니다</div>
          </div>
        </div>

        <div className={profileStyle.add} onClick={() => addUser()}>등록하기</div>
    </div>
  )
}

export default Profile