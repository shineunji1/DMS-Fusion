import Image from 'next/image'
import React from 'react'
import char404 from '../../public/pngs/404char.png'
import notFoundStyle from '@/styles/not-found.module.css'


const Error404 = () => {
  return (
    <div className={notFoundStyle.container}>
        <Image src={char404} alt='404 Character'/>
        <div className={notFoundStyle.chat}>404...</div>
        <div>
            <div className={notFoundStyle.title}>404 Not Found!</div>
            <div className={notFoundStyle.subtitle}>페이지가 <br/> 존재하지 않습니다!</div>
        </div>
    </div>
  )
}

export default Error404