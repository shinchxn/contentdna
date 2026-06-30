import { useState } from "react";
import DragDropZone from "../components/DragDropZone";
import api from "../lib/api";
import { CheckCircle, Loader2, Lock, Copy, Check } from "lucide-react";

const OWNER_ID = "1c13b877-829b-4f5b-9b0f-058b24dc5c4d";

function CopyableField({ label, value }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="space-y-1">
      <p className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>{label}</p>
      <div
        className="flex items-center gap-2 rounded-lg px-3 py-2"
        style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}
      >
        <code
          className="flex-1 text-xs font-mono truncate"
          style={{ color: "rgba(255,255,255,0.85)" }}
        >
          {value}
        </code>
        <button
          onClick={copy}
          className="flex-shrink-0 p-1 rounded"
          style={{ color: copied ? "#10B981" : "rgba(255,255,255,0.35)" }}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
        </button>
      </div>
    </div>
  );
}

export default function Upload() {
  const [file, setFile]       = useState(null);
  const [title, setTitle]     = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState(null);
  const [error, setError]     = useState(null);

  const handleUpload = async () => {
    if (!file || !title.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("owner_id", OWNER_ID);
      form.append("title", title.trim());
      const res = await api.post("/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60000,
      });
      setResult(res.data);
    } catch (e) {
      setError(
        e.response?.data?.detail ||
        e.response?.data?.message ||
        "Upload failed — check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const ready = file && title.trim() && !loading;

  return (
    <div className="max-w-2xl mx-auto space-y-6 fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white" style={{ letterSpacing: "-0.5px" }}>
          Register Content
        </h1>
        <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.45)" }}>
          Upload your original media to generate a ContentDNA fingerprint and embed an invisible watermark.
        </p>
      </div>

      {/* Drop zone */}
      <DragDropZone onFile={setFile} />

      {/* Title input */}
      <div className="space-y-2">
        <label className="text-sm font-medium" style={{ color: "rgba(255,255,255,0.6)" }}>
          Asset Title
        </label>
        <input
          type="text"
          placeholder="e.g. Champions League Final Highlight — June 2025"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ready && handleUpload()}
          className="w-full rounded-xl px-4 py-3 text-sm"
          style={{
            background: "rgba(30,41,59,0.8)",
            border: `1px solid ${title ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.12)"}`,
            color: "white",
            outline: "none",
            transition: "border-color 0.2s",
          }}
          onFocus={(e) => { e.target.style.borderColor = "rgba(59,130,246,0.6)"; }}
          onBlur={(e) => { e.target.style.borderColor = title ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.12)"; }}
        />
      </div>

      {/* Submit button */}
      <button
        id="upload-submit"
        onClick={handleUpload}
        disabled={!ready}
        className="w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2"
        style={{
          background: ready
            ? "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)"
            : "rgba(59,130,246,0.2)",
          color: ready ? "white" : "rgba(255,255,255,0.3)",
          border: "none",
          cursor: ready ? "pointer" : "not-allowed",
          boxShadow: ready ? "0 4px 16px rgba(59,130,246,0.3)" : "none",
          transition: "all 0.2s ease",
        }}
      >
        {loading ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            Generating DNA fingerprint…
          </>
        ) : (
          <>
            <Lock size={18} />
            Lock Content DNA
          </>
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

      {/* Success card */}
      {result && (
        <div
          className="rounded-2xl p-6 space-y-4 fade-in"
          style={{
            background: "rgba(16,185,129,0.07)",
            border: "1px solid rgba(16,185,129,0.3)",
            boxShadow: "0 0 32px rgba(16,185,129,0.08)",
          }}
        >
          <div className="flex items-center gap-2">
            <CheckCircle size={20} color="#10B981" />
            <span className="font-bold text-base" style={{ color: "#10B981" }}>
              DNA Fingerprint Locked ✓
            </span>
          </div>

          <div className="space-y-3">
            <CopyableField label="Asset ID" value={result.asset_id || "—"} />
            <CopyableField label="Perceptual Hash (pHash)" value={result.phash || "—"} />
            {result.faiss_id !== undefined && (
              <CopyableField label="FAISS Vector ID" value={String(result.faiss_id)} />
            )}
          </div>

          <div
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium"
            style={{
              background: "rgba(16,185,129,0.1)",
              color: "#10B981",
            }}
          >
            🛡 Invisible watermark embedded · Protection active immediately
          </div>
        </div>
      )}
    </div>
  );
}
