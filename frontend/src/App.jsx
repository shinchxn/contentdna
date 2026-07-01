import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Detect from "./pages/Detect";
import Hunt from "./pages/Hunt";
import Monitor from "./pages/Monitor";
import Alerts from "./pages/Alerts";
import Accounts from "./pages/Accounts";

export default function App() {
  return (
    <BrowserRouter>
      <div
        className="min-h-screen text-white"
        style={{ background: "#0F172A", fontFamily: "'Inter', system-ui, sans-serif" }}
      >
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/"        element={<Home />}    />
            <Route path="/upload"  element={<Upload />}  />
            <Route path="/detect"  element={<Detect />}  />
            <Route path="/hunt"    element={<Hunt />}    />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/monitor" element={<Monitor />} />
            <Route path="/alerts"  element={<Alerts />}  />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
