import { useState, useRef } from "react";
import { Upload, X, FileText } from "lucide-react";

export default function ChatInput({ username = "User", onResponse, sessionId = "default" }) {
  const [input, setInput]     = useState("");
  const [file, setFile]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  const acceptFile = (f) => {
    if (f && f.type === "application/pdf") setFile(f);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    acceptFile(dropped);
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    const question = input;

    setLoading(true);
    setInput("");
    setFile(null);

    try {
      const form = new FormData();
      form.append("question", question);
      form.append("session_id", sessionId);
      if (file) form.append("file", file);

      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        body: form,
      });

      const data = await res.json();
      if (onResponse) onResponse(question, data);
    } catch (err) {
      console.error("Backend error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full flex flex-col items-center gap-2">

      {/* File badge */}
      {file && (
        <div className="w-full max-w-3xl flex items-center gap-2 px-3 py-2 bg-slate-800 border border-indigo-700 rounded-xl">
          <FileText size={14} className="text-indigo-400 flex-shrink-0" />
          <span className="text-sm text-slate-300 truncate flex-1">{file.name}</span>
          <button
            onClick={() => setFile(null)}
            className="text-slate-500 hover:text-slate-300 transition flex-shrink-0"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Input box — also the drop target */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`w-full max-w-3xl bg-slate-900 border rounded-2xl p-3 flex items-center gap-3 shadow-lg transition-colors ${
          dragging
            ? "border-indigo-500 bg-slate-800"
            : "border-slate-700"
        }`}
      >
        {/* Upload button */}
        <label className="cursor-pointer flex items-center justify-center w-9 h-9 rounded-lg bg-slate-800 hover:bg-slate-700 transition flex-shrink-0">
          <Upload size={16} className="text-slate-300" />
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => acceptFile(e.target.files[0])}
          />
        </label>

        <input
          value={dragging ? "" : input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={dragging ? "Drop PDF here..." : "Search papers, ask questions..."}
          className="flex-1 bg-transparent outline-none text-white px-2 text-[15px] placeholder:text-slate-500"
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          disabled={loading || dragging}
        />

        <button
          onClick={handleSend}
          disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2 rounded-xl text-[15px] flex-shrink-0 transition-colors"
        >
          {loading ? "Thinking..." : "Send"}
        </button>
      </div>

      {dragging && (
        <p className="text-xs text-indigo-400">Release to attach PDF</p>
      )}

    </div>
  );
}
