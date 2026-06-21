import { Outlet, useLocation } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { AppTopbar } from "./AppTopbar";
import { DemoModeBanner } from "@/components/DemoModeBanner";

export function AppLayout() {
  const location = useLocation();
  const hideDemoBanner = location.pathname.startsWith("/app/review");

  return (
    <div className="app-shell min-h-screen flex w-full">
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopbar />
        {!hideDemoBanner && <DemoModeBanner />}
        <main className="app-grid-bg relative flex-1 overflow-y-auto">
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
