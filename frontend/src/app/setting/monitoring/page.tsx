import Monitoring from '@/components/Monitoring';

const url = "http://localhost:8000";

interface ApiResponse{
  message:string;
  id:number;
}

interface IndexProps {
  data: ApiResponse;
}

async function getIndex(): Promise<ApiResponse> {
  const response = await fetch(url);
  const json = await response.json();
  return json;
}

export const metadata = {
    title:"Monitoring"
}

const page = async() => {

  const data = await getIndex();
  console.log(data);

  return (
    <Monitoring data = {data}></Monitoring>
  )
}

export default page