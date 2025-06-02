import Profile from "@/components/profile/Profile"
import axios from "axios";

const url = "http://localhost:8000/profile/1";

interface ApiResponse{
  message : string;
  id: number;
}


async function getProfile(): Promise<ApiResponse> {
  const response = await axios.get(url, {method: "GET"});
  const json = response.data;
  return json;
}

const page = async() => {
  const data = await getProfile();
  console.log(data);

  return (
    <Profile data = {data}></Profile>
  )
}

export default page