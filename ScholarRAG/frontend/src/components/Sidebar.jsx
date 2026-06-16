import {
  Search,
  FileText,
  FolderOpen,
  Pin,
  History,
  Star,
  PlusSquare,
  Clock,
  Menu,
} from "lucide-react";
import { FaBookOpen } from "react-icons/fa";
import { useState } from "react";

export default function Sidebar({ user, setUser, onNewChat, history = [], onLoadHistory, activeId }) {
  const [open, setOpen] = useState(true);

  const [loginOpen, setLoginOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = () => {
  if (name && email && password) {
    setUser({
      name,
      email,
    });

    setLoginOpen(false);

    setName("");
    setEmail("");
    setPassword("");
  }
};

  return (
    <div className="flex h-full">
      {/* SIDEBAR */}
      <div
        className={`h-full bg-slate-950 border-r border-slate-800 p-5 flex flex-col transition-all duration-300 ${
          open ? "w-72" : "w-0 overflow-hidden p-0"
        }`}
      >
        {/* HEADER */}
        <div className="flex items-center justify-between mb-10">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
              <FaBookOpen className="text-2xl text-white" />
            </div>

            <div>
              <h1 className="text-2xl font-extrabold text-white">
                ScholarRAG
              </h1>
              <p className="text-xs text-slate-400">
                Research Intelligence Platform
              </p>
            </div>
          </div>

          <button
            onClick={() => setOpen(!open)}
            className="text-white text-xl"
          >
            <Menu />
          </button>
        </div>
        
        <p className="text-xs uppercase tracking-widest text-slate-500 mb-3">
          Workspace
        </p>

        {/* NAVIGATION */}
        <div className="space-y-1 mt-2">
          <div
            className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 cursor-pointer"
            onClick={onNewChat}
          >
            <PlusSquare size={18} />
            <span>New Chat</span>
          </div>

          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 cursor-pointer">
            <Search size={18} />
            <span>Search Papers</span>
          </div>

          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 cursor-pointer">
            <FileText size={18} />
            <span>Documents</span>
          </div>

          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 cursor-pointer">
            <FolderOpen size={18} />
            <span>Collections</span>
          </div>

          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 cursor-pointer">
            <Pin size={18} />
            <span>Pinned</span>
          </div>

          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 cursor-pointer">
            <History size={18} />
            <span>Recent Activity</span>
          </div>

          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 cursor-pointer">
            <Star size={18} />
            <span>Favorites</span>
          </div>
        </div>

        {/* HISTORY */}
        <div className="mt-6 flex-1 overflow-y-auto">
          <h3 className="text-xs font-bold text-slate-300 mb-2 px-3">
            HISTORY
          </h3>

          <div className="space-y-1">
            {history.length === 0 ? (
              <p className="text-xs text-slate-600 px-3">No chats yet.</p>
            ) : (
              history.map((entry) => (
                <div
                  key={entry.id}
                  onClick={() => onLoadHistory(entry)}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer ${
                    entry.id === activeId ? "bg-slate-800" : "hover:bg-slate-900"
                  }`}
                >
                  <Clock size={15} className="text-slate-400 shrink-0" />
                  <span className="text-slate-300 text-sm truncate">{entry.title}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* PROFILE */}
        <div className="mt-auto pt-4">
          <div className="bg-slate-900 p-3 rounded-xl flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-white">
              {user ? user.email[0].toUpperCase() : "G"}
            </div>

            <div className="flex flex-col flex-1">
              <p className="font-medium text-white">
                {user ? user.name : "Guest"}
              </p>

              <p className="text-xs text-slate-400">Researcher</p>

              {!user ? (
                <button
                  onClick={() => setLoginOpen(true)}
                  className="text-xs text-indigo-400 text-left mt-1"
                >
                  Login
                </button>
              ) : (
                <button
                  onClick={() => setUser(null)}
                  className="text-xs text-red-400 text-left mt-1"
                >
                  Logout
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* LOGIN MODAL */}
      {loginOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-slate-900 p-6 rounded-xl w-80">
            <h2 className="text-white text-xl mb-4 font-bold">Login</h2>

            <input
  type="text"
  placeholder="Full Name"
  value={name}
  onChange={(e) => setName(e.target.value)}
  className="w-full p-2 mb-3 rounded bg-slate-800 text-white"
/>
            <input
              type="text"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-2 mb-3 rounded bg-slate-800 text-white"
            />

            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-2 mb-4 rounded bg-slate-800 text-white"
            />

            <button
              onClick={handleLogin}
              className="w-full bg-green-600 hover:bg-green-700 py-2 rounded text-white"
            >
              Sign In
            </button>

            <button
              onClick={() => setLoginOpen(false)}
              className="w-full mt-2 text-sm text-slate-400"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}