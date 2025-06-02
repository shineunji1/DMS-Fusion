import SeatSet from "@/components/seat-set/SeatSet";

const url = "http://localhost:8000/seat-set";

interface ApiResponse{
  message:string;
  positions: string[];  // ✅ FastAPI의 응답에 맞게 수정
}

interface IndexProps{
  data: ApiResponse;
}

async function getIndex(): Promise<ApiResponse> {
  const response = await fetch(url, {method: "GET"});
  const json = await response.json();
  return json;
  
}

const page = async() => {
  const userId = 1;
  console.log(userId);

  return (
    <SeatSet userId = {userId}/>
  )
}

export default page