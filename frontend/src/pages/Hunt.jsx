import { useState, useEffect } from "react";
import HuntProgress from "../components/HuntProgress";
import AlertCard from "../components/AlertCard";
import api from "../lib/api";
import { supabase } from "../lib/supabase";
import { Globe, Loader2, Sliders } from "lucide-react";

const OWNER_ID = "d3b07384-d113-4ec5-a55d-229202020202";

export default function Hunt() {
  const [url, setUrl]           = useState("");
  const [depth, setDepth]       = useState(3);
  const [pages, setPages]       = useState(100);
  const [jobId, setJobId]       = useState(null);
  const [loading, setLoading]   = useState(false);
  const [liveAlerts, setLiveAlerts] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError]       = useState(null);

  // Supabase Realtime — receive new alerts as hunt finds them
  useEffect(() => {
    const channel = supabase
      .channel("hunt-alerts")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "alerts" },
        (payload) => {
          setLiveAlerts((prev) => [payload.new, ...prev]);
        }
      )
      .subscribe();
    return () => supabase.removeChannel(channel);
  }, []);

  const startHunt = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setLiveAlerts([]);
    setJobId(null);
    try {
      const res = await api.post("/hunt", {
        url: url.trim(),
        owner_id: OWNER_ID,
        max_depth: depth,
        max_pages: pages,
      });
      setJobId(res.data.job_id);
    } catch (e) {
      setError(
        e.response?.data?.detail ||
        "Failed to start hunt — check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white" style={{ letterSpacing: "-0.5px" }}>
          Universal Web Hunter
        </h1>
        <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.45)" }}>
          Enter any URL or domain. ContentDNA will crawl every page, extract all media,
          and surface violations in real time.
        </p>
      </div>

      {/* URL input */}
      <div className="space-y-2">
        <label className="text-sm font-medium" style={{ color: "rgba(255,255,255,0.6)" }}>
          Target URL or Domain
        </label>
        <div className="relative">
          <Globe
            size={16}
            className="absolute left-4 top-1/2 -translate-y-1/2"
            style={{ color: "rgba(255,255,255,0.3)" }}
          />
          <input
            id="hunt-url-input"
            type="url"
            placeholder="https://anysportssite.com or https://reddit.com/r/soccer"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && url.trim() && !loading && startHunt()}
            className="w-full rounded-xl pl-10 pr-4 py-3 text-sm"
            style={{
              background: "rgba(30,41,59,0.8)",
              border: `1px solid ${url ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.12)"}`,
              color: "white",
              outline: "none",
            }}
            onFocus={(e) => { e.target.style.borderColor = "rgba(59,130,246,0.6)"; }}
            onBlur={(e)  => { e.target.style.borderColor = url ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.12)"; }}
          />
        </div>
      </div>

      {/* Advanced options toggle */}
      <button
        onClick={() => setShowAdvanced((v) => !v)}
        className="flex items-center gap-2 text-sm"
        style={{ color: "rgba(255,255,255,0.45)", background: "none", border: "none", cursor: "pointer" }}
      >
        <Sliders size={13} />
        {showAdvanced ? "Hide" : "Show"} advanced options
      </button>

      {showAdvanced && (
        <div
          className="rounded-xl p-4 space-y-4 fade-in"
          style={{ background: "rgba(30,41,59,0.5)", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-medium" style={{ color: "rgba(255,255,255,0.5)" }}>
                Crawl Depth (1–5)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={1} max={5}
                  value={depth}
                  onChange={(e) => setDepth(Number(e.target.value))}
                  className="flex-1"
                  style={{ accentColor: "#3B82F6" }}
                />
                <span
                  className="w-8 text-center text-sm font-bold"
                  style={{ color: "#60A5FA" }}
                >
                  {depth}
                </span>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium" style={{ color: "rgba(255,255,255,0.5)" }}>
                Max Pages (10–500)
              </label>
              <input
                type="number"
                min={10} max={500}
                value={pages}
                onChange={(e) => setPages(Number(e.target.value))}
                className="w-full rounded-lg px-3 py-2 text-sm"
                style={{
                  background: "rgba(15,23,42,0.5)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "white",
                  outline: "none",
                }}
              />
            </div>
          </div>

          {/* Settings summary */}
          <p className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
            Will crawl up to <strong style={{ color: "rgba(255,255,255,0.6)" }}>{pages}</strong> pages,{" "}
            <strong style={{ color: "rgba(255,255,255,0.6)" }}>{depth}</strong> link{depth !== 1 ? "s" : ""} deep from the seed URL.
          </p>
        </div>
      )}

      {/* Start button */}
      <button
        id="hunt-start"
        onClick={startHunt}
        disabled={!url.trim() || loading}
        className="w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2"
        style={{
          background: url.trim() && !loading
            ? "linear-gradient(135deg, #10B981 0%, #059669 100%)"
            : "rgba(16,185,129,0.15)",
          color: url.trim() && !loading ? "white" : "rgba(255,255,255,0.3)",
          border: "none",
          cursor: url.trim() && !loading ? "pointer" : "not-allowed",
          boxShadow: url.trim() && !loading ? "0 4px 16px rgba(16,185,129,0.3)" : "none",
        }}
      >
        {loading ? (
          <><Loader2 size={18} className="animate-spin" /> Starting hunt…</>
        ) : (
          <><Globe size={18} /> Start Hunt</>
        )}
      </button>

      {/* Error */}
      {error && (
        <div
          className="rounded-xl p-4 text-sm"
          style={{
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.25)",
            color: "#EF4444",
          }}
        >
          ⚠️ {error}
        </div>
      )}

      {/* Live progress */}
      {jobId && (
        <HuntProgress
          jobId={jobId}
          onComplete={(job) => {
            console.log("[ContentDNA] Hunt complete:", job);
          }}
        />
      )}

      {/* Live violations feed */}
      {liveAlerts.length > 0 && (
        <div className="space-y-3 fade-in">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-sm text-white">Live Matches</h2>
            <span
              className="px-2 py-0.5 rounded-full text-xs font-bold"
              style={{
                background: "rgba(239,68,68,0.15)",
                color: "#EF4444",
                animation: "pulse 2s cubic-bezier(0.4,0,0.6,1) infinite",
              }}
            >
              {liveAlerts.length}
            </span>
          </div>
          {liveAlerts.map((a) => (
            <AlertCard key={a.id} alert={a} />
          ))}
        </div>
      )}
    </div>
  );
}
