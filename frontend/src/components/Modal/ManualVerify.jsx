import React, { useRef } from 'react'
import modalStyle from "@/styles/modal.module.css"
import axios from 'axios'
import { useRouter } from 'next/navigation'

const ManualVerify = ({setModal}) => {

  const router = useRouter();

  const pwdRef = useRef();

  const manualLogin = () => {
    const pwd = pwdRef.current.value
    axios.post("http://localhost:8000/login/manual", {
      "user_pwd" : pwd
    }, {
      withCredentials: true,
      headers: {
        "Content-Type" : "application/json"
      }
    }).then(res => {
       const data = res.data
       console.log(data)
        if(data.success) {
          localStorage.setItem('needsRefresh', 'true');
          router.replace("/");
          pwdRef.current.value = '';
        } else {
          alert("얼굴 인증 실패!")
          pwdRef.current.value = '';
        }
    }).catch(err => {
      alert("로그인 실패!")
      console.error("로그인 실패:", err)
    })
  }

  return (
    <div className={modalStyle.container}>
        <div className={modalStyle.manualVerify}>
            <span className={modalStyle.closeBtn} onClick={() => setModal(false)}>X</span>
            <div className={modalStyle.title}>비밀번호를 입력해주세요</div>
            <div className={modalStyle.inputBox}>
                <input type='password' placeholder='설정했던 6자리를 입력하세요' ref={pwdRef}></input>
            </div>
            <div className={modalStyle.btnBox}>
              <div className={modalStyle.manualLoginBtn} onClick={() => manualLogin()}>로그인</div>
            </div>
        </div>
    </div>
  )
}

export default ManualVerify