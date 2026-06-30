import { useState, useRef } from "react";
import { Upload, Film, Image, X } from "lucide-react";

export default function DragDropZone({ onFile, accept = "image/*,video/*" }) {
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState(null);
  const inputRef = useRef();

  const handleFile = (file) => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview({ url, type: file.type, name: file.name, size: file.size });
    onFile(file);
  };

  const clearFile = (e) => {
    e.stopPropagation();
    setPreview(null);
    onFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragEnter={() => setDragging(true)}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFile(e.dataTransfer.files[0]);
      }}
      className="relative rounded-2xl p-8 text-center cursor-pointer select-none"
      style={{
        border: `2px dashed ${dragging ? "#3B82F6" : preview ? "#10B981" : "rgba(255,255,255,0.15)"}`,
        background: dragging
          ? "rgba(59,130,246,0.08)"
          : preview
          ? "rgba(16,185,129,0.06)"
          : "rgba(30,41,59,0.4)",
        transition: "all 0.2s ease",
        boxShadow: dragging ? "0 0 24px rgba(59,130,246,0.2)" : "none",
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0])}
      />

      {preview ? (
        <div className="space-y-3">
          {/* Preview */}
          {preview.type.startsWith("image") ? (
            <img
              src={preview.url}
              alt="preview"
              className="max-h-52 mx-auto rounded-xl object-cover"
              style={{ boxShadow: "0 4px 24px rgba(0,0,0,0.5)" }}
            />
          ) : (
            <div className="relative max-w-sm mx-auto">
              <video
                src={preview.url}
                controls
                className="max-h-48 mx-auto rounded-xl w-full"
                style={{ boxShadow: "0 4px 24px rgba(0,0,0,0.5)" }}
              />
            </div>
          )}

          {/* File info */}
          <div className="flex items-center justify-center gap-2">
            {preview.type.startsWith("image") ? (
              <Image size={14} className="text-accent" style={{ color: "#10B981" }} />
            ) : (
              <Film size={14} style={{ color: "#10B981" }} />
            )}
            <span className="text-sm font-medium text-white truncate max-w-xs">
              {preview.name}
            </span>
            <span className="text-xs text-white/40">
              {formatSize(preview.size)}
            </span>
          </div>

          {/* Clear button */}
          <button
            onClick={clearFile}
            className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium"
            style={{
              background: "rgba(239,68,68,0.12)",
              color: "#EF4444",
              border: "1px solid rgba(239,68,68,0.25)",
            }}
          >
            <X size={12} /> Remove
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Upload icon */}
          <div
            className="w-16 h-16 mx-auto rounded-2xl flex items-center justify-center"
            style={{
              background: "rgba(59,130,246,0.1)",
              border: "1px solid rgba(59,130,246,0.2)",
            }}
          >
            <Upload
              size={28}
              style={{ color: dragging ? "#3B82F6" : "rgba(255,255,255,0.35)" }}
            />
          </div>

          <div>
            <p className="font-semibold text-white/80">
              {dragging ? "Drop to upload" : "Drop file here or click to browse"}
            </p>
            <p className="text-sm text-white/35 mt-1">
              Supported: JPG, PNG, GIF, MP4, MOV, WebM
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
