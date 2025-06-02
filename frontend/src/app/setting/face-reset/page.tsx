import FaceReset from './../../../components/face_reset/FaceReset';

const url = "http://localhost:8000/face-reset/";  
interface ApiResponse {
  message: string;
  id: number;
}

interface IndexProps {
  data: ApiResponse;
}

async function getIndex(): Promise<ApiResponse> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type" : "application/json",
    },
    body: JSON.stringify({
      user_id : 1,
    }),
  });
  
  const json = await response.json();
  return json;
}


const page = async () => {
  const data = await getIndex();
  console.log(data);

  return (
    <FaceReset data = {data}></FaceReset>
  )
}

export default page