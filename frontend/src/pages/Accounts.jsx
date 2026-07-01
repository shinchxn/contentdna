import { useState, useEffect } from "react";
import api from "../lib/api";
import { Search, Loader2, Plus, Trash2, Clock, CheckCircle } from "lucide-react";
import PlatformBadge from "../components/PlatformBadge";
import { Link } from "react-router-dom";

const OWNER_ID = "d3b07384-d113-4ec5-a55d-229202020202";
const PLATFORMS = ["instagram", "youtube", "tiktok", "reddit"];

export default function Accounts() {
  const [handle, setHandle] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  
  const [watchlist, setWatchlist] = useState([]);
  const [loadingList, setLoadingList] = useState(true);

  const fetchWatchlist = async () => {
    setLoadingList(true);
    try {
      const res = await api.get(`/accounts?owner_id=${OWNER_ID}`);
      setWatchlist(res.data.accounts || []);
    } catch (e) {
      console.error("Failed to fetch watchlist", e);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const canRun = handle.trim().length > 0;

  const runCheck = async (e) => {
    if (e) e.preventDefault();
    if (!canRun || loading) return;
    
    // Clean handle (remove leading @ or url prefixes if pasted)
    let cleanHandle = handle.trim();
    if (cleanHandle.startsWith("@")) {
      cleanHandle = cleanHandle.substring(1);
    }
    // simple URL stripping fallback
    if (cleanHandle.includes("/")) {
      const parts = cleanHandle.split("/");
      cleanHandle = parts[parts.length - 1] || parts[parts.length - 2]; 
    }

    setLoading(true);
    setResult(null);
    try {
      const res = await api.post("/accounts/check", {
        owner_id: OWNER_ID,
        platform,
        handle: cleanHandle,
        limit: 25
      });
      setResult(res.data);
    } catch (e) {
      setResult({
        error: e.response?.data?.detail || e.message || "Failed to check account",
        found: 0,
        matched: 0
      });
    } finally {
      setLoading(false);
    }
  };

  const addToWatchlist = async (accPlatform, accHandle, accLabel = null) => {
    try {
      await api.post("/accounts", {
        owner_id: OWNER_ID,
        platform: accPlatform,
        handle: accHandle,
        label: accLabel
      });
      fetchWatchlist();
    } catch (e) {
      alert("Failed to add to watchlist or already exists.");
    }
  };

  const removeFromWatchlist = async (id) => {
    if (!window.confirm("Remove this account from watchlist?")) return;
    try {
      await api.delete(`/accounts/${id}`);
      fetchWatchlist();
    } catch (e) {
      console.error("Delete failed", e);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white" style={{ letterSpacing: "-0.5px" }}>
          Targeted Account Search
        </h1>
        <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.45)" }}>
          Suspect a specific account? Check their recent posts immediately and add them to your watchlist.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col - Check Form */}
        <div className="lg:col-span-1 space-y-6">
          <form 
            onSubmit={runCheck}
            className="rounded-2xl p-5 space-y-4"
            style={{ background: "rgba(30,41,59,0.6)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            <div>
              <label className="text-xs font-medium block mb-2" style={{ color: "rgba(255,255,255,0.5)" }}>
                Platform
              </label>
              <div className="grid grid-cols-2 gap-2">
                {PLATFORMS.map((p) => (
                  <button
                    type="button"
                    key={p}
                    onClick={() => setPlatform(p)}
                    className="py-2 rounded-xl text-xs font-medium capitalize transition-all"
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

            <div>
              <label className="text-xs font-medium block mb-2" style={{ color: "rgba(255,255,255,0.5)" }}>
                Account Handle
              </label>
              <input
                type="text"
                placeholder="e.g. someaccount"
                value={handle}
                onChange={(e) => setHandle(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-sm"
                style={{
                  background: "rgba(15,23,42,0.6)",
                  border: `1px solid ${handle ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.12)"}`,
                  color: "white",
                  outline: "none",
                }}
              />
            </div>

            <button
              type="submit"
              disabled={!canRun || loading}
              className="w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2"
              style={{
                background: canRun && !loading
                  ? "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)"
                  : "rgba(59,130,246,0.15)",
                color: canRun && !loading ? "white" : "rgba(255,255,255,0.3)",
                border: "none",
                cursor: canRun && !loading ? "pointer" : "not-allowed",
              }}
            >
              {loading ? (
                <><Loader2 size={16} className="animate-spin" /> Checking @{handle}...</>
              ) : (
                <><Search size={16} /> Check Account</>
              )}
            </button>
          </form>

          {/* Result Card */}
          {result && (
            <div
              className="rounded-2xl p-5 space-y-4 fade-in"
              style={{
                background: "rgba(30,41,59,0.8)",
                border: result.error
                  ? "1px solid rgba(234,179,8,0.3)" // Yellow warning for error
                  : result.matched > 0
                    ? "1px solid rgba(239,68,68,0.3)" // Red for violations
                    : "1px solid rgba(16,185,129,0.3)", // Green for clean
              }}
            >
              {result.error ? (
                <>
                  <p className="font-bold text-sm text-yellow-500">⚠️ Check Failed</p>
                  <p className="text-xs text-white/70">{result.error}</p>
                </>
              ) : (
                <>
                  {result.matched > 0 ? (
                    <div className="space-y-3">
                      <p className="font-bold text-base text-red-500 flex items-center gap-2">
                        ⚠️ {result.matched} Match{result.matched !== 1 ? 'es' : ''} Found
                      </p>
                      <p className="text-xs text-white/60">
                        Scanned {result.found} recent items.
                      </p>
                      <Link 
                        to={`/alerts?platform=${result.platform}`}
                        className="block w-full text-center py-2 rounded-lg text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20"
                      >
                        View new alerts in Feed →
                      </Link>
                    </div>
                  ) : (
                    <div className="flex items-start gap-3">
                      <CheckCircle size={20} className="text-emerald-500 flex-shrink-0" />
                      <div>
                        <p className="font-semibold text-emerald-500">All Clean</p>
                        <p className="text-xs mt-1 text-white/60">
                          Scanned {result.found} recent items. No matches found.
                        </p>
                      </div>
                    </div>
                  )}
                </>
              )}

              <div className="pt-4 mt-2" style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }}>
                <button
                  onClick={() => addToWatchlist(result.platform, result.handle)}
                  className="w-full py-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors hover:bg-white/5 text-white/70 border border-white/10"
                >
                  <Plus size={14} /> Add @{result.handle} to Watchlist
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Col - Watchlist */}
        <div className="lg:col-span-2">
          <div className="rounded-2xl overflow-hidden" style={{ background: "rgba(30,41,59,0.4)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="p-4 border-b border-white/10 flex justify-between items-center">
              <h2 className="font-semibold text-sm text-white flex items-center gap-2">
                <Clock size={16} className="text-blue-400"/> Watchlist
              </h2>
              <span className="text-xs text-white/50">{watchlist.length} Accounts</span>
            </div>
            
            <div className="p-0">
              {loadingList ? (
                <div className="p-8 text-center text-sm text-white/40 flex justify-center">
                  <Loader2 className="animate-spin" size={20} />
                </div>
              ) : watchlist.length === 0 ? (
                <div className="p-8 text-center text-sm text-white/40">
                  No accounts in watchlist.
                </div>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase bg-white/5 text-white/40">
                    <tr>
                      <th className="px-4 py-3 font-medium">Platform</th>
                      <th className="px-4 py-3 font-medium">Handle</th>
                      <th className="px-4 py-3 font-medium">Added</th>
                      <th className="px-4 py-3 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {watchlist.map(w => (
                      <tr key={w.id} className="hover:bg-white/5 transition-colors">
                        <td className="px-4 py-3"><PlatformBadge platform={w.platform} /></td>
                        <td className="px-4 py-3 font-medium">@{w.handle}</td>
                        <td className="px-4 py-3 text-xs text-white/40">
                          {new Date(w.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => {
                                setPlatform(w.platform);
                                setHandle(w.handle);
                                // Scroll to top if on mobile
                                window.scrollTo({ top: 0, behavior: 'smooth' });
                              }}
                              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20"
                            >
                              Check Now
                            </button>
                            <button
                              onClick={() => removeFromWatchlist(w.id)}
                              className="p-1.5 rounded-lg text-red-400 hover:bg-red-500/20 transition-colors"
                              title="Remove"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
