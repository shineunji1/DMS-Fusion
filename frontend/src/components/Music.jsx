import React from 'react'
import indexStyle from "@/styles/index.module.css"
import { PlayCircle, SkipNext, SkipPrevious } from '@mui/icons-material'

const Music = () => {
  return (
   <div className={indexStyle.musicStation}>
      <div className={indexStyle.tumbBox}>No Sings</div>
      <div className={indexStyle.songInfo}>
        <div className={indexStyle.playtitle}>playlist name</div>
        <div className={indexStyle.songtitle}>Song Name</div>
        <div className={indexStyle.playBtn}>
          <SkipPrevious></SkipPrevious>
          <PlayCircle></PlayCircle>
          <SkipNext></SkipNext>
        </div>
      </div>
   </div>
  )
}

export default Music