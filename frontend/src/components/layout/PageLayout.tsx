import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";

export default function PageLayout() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <main className="pt-16">
        <Outlet />
      </main>
    </div>
  );
}
