import axios from "axios";
import { getSession } from "../../layout"
import { NextResponse } from "next/server";


/**
 * FastAPI로 좌석 설정 업데이트 요청하는 함수
 * @param {string} position - 변경할 좌석 위치 ("head", "back", "seat", "handle")
 * @param {object} adjustment - 변경할 값 (예: { "각도": 1 } 또는 { "전후": -0.02 })
 */
// export const updateSeatSetting = async (position, adjustment) => {
//     try {
//         const response = await axios.put(`http://127.0.0.1:8000/seat-set/1/${position}`, adjustment);
//         console.log(`✅ FastAPI 업데이트 완료:`, response.data);
//         return response.data;
//     } catch (error) {
//         console.error("🚨 FastAPI 업데이트 실패:", error);
//         return { error: "업데이트 실패 " };
//     }
// };

export async function POST(req) {
    const data = await req.json();
    const sessionData = await getSession();
    console.log(sessionData.item);
    const userId = sessionData.item.user_id;
    const fastapiUrl = `http://localhost:8000/seat-set/${userId}`

    const response = await axios.put(fastapiUrl,{
        position:data
    }, {
        withCredentials: true,
        headers:{
            "Content-Type" : "application/json"
        }
    } )

    return NextResponse.json(
        {message : "데이터 받기 성공"}
    );
}