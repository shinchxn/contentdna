import { useState } from "react";
import DragDropZone from "../components/DragDropZone";
import ScoreGauge from "../components/ScoreGauge";
import SeverityBadge from "../components/SeverityBadge";
import PlatformBadge from "../components/PlatformBadge";
import api from "../lib/api";
import { Loader2, Search, ShieldCheck, CheckCircle } from "lucide-react";

const PLATFORMS = ["web", "instagram", "youtube", "tiktok", "reddit", "live"];

export default function Detect() {
  const [tab, setTab]           = useState("file");
  const [file, setFile]         = useState(null);
  const [url, setUrl]           = useState("");
  const [platform, setPlatform] = useState("web");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);

  const canRun = (tab === "file" && file) || (tab === "url" && url.trim());

  const runDetect = async () => {
    if (!canRun) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      let res;
      if (tab === "file") {
        const form = new FormData();
        form.append("file", file);
        res = await api.post("/detect", form, {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 60000,
        });
      } else {
        res = await api.post("/check-url", {
          url: url.trim(),
          platform,
        });
      }
      setResult(res.data);
    } catch (e) {
      setError(
        e.response?.data?.detail ||
        e.response?.data?.message ||
        "Detection failed — check that the backend is running."
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
          Detect Violations
        </h1>
        <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.45)" }}>
          Upload a file or paste a URL to run AI-powered fingerprint matching against your protected assets.
        </p>
      </div>

      {/* Tab switcher */}
      <div
        className="flex gap-1 p-1 rounded-xl"
        style={{ background: "rgba(30,41,59,0.8)", border: "1px solid rgba(255,255,255,0.08)" }}
      >
        {[
          { key: "file", label: "📂 Upload File" },
          { key: "url",  label: "🔗 Paste URL" },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => { setTab(key); setResult(null); setError(null); }}
            className="flex-1 py-2 rounded-lg text-sm font-medium transition-all"
            style={{
              background: tab === key ? "rgba(59,130,246,0.2)" : "transparent",
              color:      tab === key ? "#60A5FA" : "rgba(255,255,255,0.45)",
              border:     tab === key ? "1px solid rgba(59,130,246,0.35)" : "1px solid transparent",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Input area */}
      {tab === "file" ? (
        <DragDropZone onFile={setFile} />
      ) : (
        <div className="space-y-3">
          <input
            type="url"
            id="detect-url-input"
            placeholder="https://example.com/suspected-video.mp4"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && canRun && runDetect()}
            className="w-full rounded-xl px-4 py-3 text-sm"
            style={{
              background: "rgba(30,41,59,0.8)",
              border: `1px solid ${url ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.12)"}`,
              color: "white",
              outline: "none",
            }}
            onFocus={(e) => { e.target.style.borderColor = "rgba(59,130,246,0.6)"; }}
            onBlur={(e)  => { e.target.style.borderColor = url ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.12)"; }}
          />
          <div className="flex items-center gap-3">
            <label className="text-xs font-medium" style={{ color: "rgba(255,255,255,0.5)" }}>
              Platform:
            </label>
            <div className="flex gap-1 flex-wrap">
              {PLATFORMS.map((p) => (
                <button
                  key={p}
                  onClick={() => setPlatform(p)}
                  className="px-3 py-1 rounded-lg text-xs font-medium capitalize transition-all"
                  style={{
                    background: platform === p ? "rgba(59,130,246,0.2)" : "rgba(255,255,255,0.05)",
                    border:     platform === p ? "1px solid rgba(59,130,246,0.4)" : "1px solid rgba(255,255,255,0.1)",
                    color:      platform === p ? "#60A5FA" : "rgba(255,255,255,0.5)",
                  }}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Run button */}
      <button
        id="detect-run"
        onClick={runDetect}
        disabled={!canRun || loading}
        className="w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2"
        style={{
          background: canRun && !loading
            ? "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)"
            : "rgba(59,130,246,0.15)",
          color: canRun && !loading ? "white" : "rgba(255,255,255,0.3)",
          border: "none",
          cursor: canRun && !loading ? "pointer" : "not-allowed",
          boxShadow: canRun && !loading ? "0 4px 16px rgba(59,130,246,0.3)" : "none",
        }}
      >
        {loading ? (
          <><Loader2 size={18} className="animate-spin" /> Scanning…</>
        ) : (
          <><Search size={18} /> Run Detection</>
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

      {/* Results */}
      {result && (
        <div
          className="rounded-2xl p-6 space-y-5 fade-in"
          style={{
            background: "rgba(30,41,59,0.8)",
            border: result.matched
              ? "1px solid rgba(239,68,68,0.3)"
              : "1px solid rgba(16,185,129,0.3)",
          }}
        >
          {result.matched ? (
            <>
              {/* Violation header */}
              <div className="flex items-center justify-between">
                <p className="font-bold text-base flex items-center gap-2" style={{ color: "#EF4444" }}>
                  ⚠️ {result.matches?.length ?? 1} Violation{(result.matches?.length ?? 1) !== 1 ? "s" : ""} Found
                </p>
                {result.processing_time_ms && (
                  <span className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
                    {result.processing_time_ms}ms
                  </span>
                )}
              </div>

              {/* Match cards */}
              {(result.matches || []).map((m, i) => (
                <div
                  key={i}
                  className="flex items-center gap-5 pt-4"
                  style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}
                >
                  <ScoreGauge score={m.score ?? m.similarity ?? 0} size={80} />
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <SeverityBadge severity={m.severity} />
                      {m.platform && <PlatformBadge platform={m.platform} />}
                    </div>
                    {m.filename && (
                      <p className="text-sm" style={{ color: "rgba(255,255,255,0.65)" }}>
                        Asset: <span className="font-medium text-white">{m.filename}</span>
                      </p>
                    )}
                    {m.asset_title && (
                      <p className="text-sm" style={{ color: "rgba(255,255,255,0.65)" }}>
                        Title: <span className="font-medium text-white">{m.asset_title}</span>
                      </p>
                    )}
                    {m.watermark_confirmed && (
                      <p
                        className="text-xs flex items-center gap-1 font-semibold"
                        style={{ color: "#10B981" }}
                      >
                        <ShieldCheck size={12} /> Watermark confirmed
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="flex items-center gap-3">
              <CheckCircle size={24} color="#10B981" />
              <div>
                <p className="font-semibold" style={{ color: "#10B981" }}>
                  No violations found
                </p>
                <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>
                  This content does not match any registered assets.
                  {result.processing_time_ms && ` (${result.processing_time_ms}ms)`}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
