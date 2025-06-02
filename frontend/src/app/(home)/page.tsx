
import Index from "../../components/Index"
import { getSession } from "../layout"

export default async function index(){

  const sessionData = await getSession()
    
  return <Index data = {sessionData}/>
}
