import SideBar from "@/components/SideBar";
import settinglayout from "@/styles/setting_layout.module.css"
import Link from "next/link";
import { getSession } from "../layout";

export default function SettingLayout({ children }: { children: React.ReactNode }) {
  
  const sessionData = getSession();
  
  return (
      <>
        <div className={settinglayout.content}>
        <SideBar data = {sessionData} />
          <div className={settinglayout.container}>
            <Link href={"./"}><div className="return-btn">돌아가기</div></Link>
            {children}
          </div>
        </div>
      </>
    );
  }