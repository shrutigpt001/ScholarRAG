import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Sidebar from "./components/Sidebar";
import ChatInput from "./components/ChatInput";
import SourcesPanel from "./components/SourcesPanel";

function makeSessionId() {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

const markdownComponents = {
  p: ({ children }) => (
    <p className="mb-3 last:mb-0 leading-8 text-slate-200 text-[15px]">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="text-white font-semibold">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="text-slate-300 italic">{children}</em>
  ),
  h1: ({ children }) => (
    <h1 className="text-3xl font-bold text-white mt-6 mb-3 pb-1 border-b border-slate-700">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-2xl font-bold text-white mt-5 mb-2">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-xl font-semibold text-white mt-4 mb-2">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-lg font-semibold text-slate-100 mt-3 mb-1">{children}</h4>
  ),
  ul: ({ children }) => (
    <ul className="list-disc pl-6 space-y-2 mb-3 text-slate-200 text-[15px]">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal pl-6 space-y-2 mb-3 text-slate-200 text-[15px]">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="leading-7">{children}</li>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-indigo-500 pl-4 my-3 text-slate-400 italic text-[15px]">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="border-slate-700 my-4" />,
  pre: ({ children }) => (
    <pre className="bg-slate-900 border border-slate-700 rounded-xl p-4 overflow-x-auto mb-3 my-2 text-sm font-mono">
      {children}
    </pre>
  ),
  code: ({ className, children }) => {
    const isBlock = /language-(\w+)/.exec(className || "");
    return isBlock ? (
      <code className="text-green-300 font-mono text-sm">{children}</code>
    ) : (
      <code className="bg-slate-700 text-indigo-300 px-1.5 py-0.5 rounded text-sm font-mono">
        {children}
      </code>
    );
  },
  table: ({ children }) => (
    <div className="overflow-x-auto mb-4 rounded-lg border border-slate-700">
      <table className="w-full border-collapse text-[15px]">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-slate-800">{children}</thead>
  ),
  tbody: ({ children }) => (
    <tbody className="divide-y divide-slate-700">{children}</tbody>
  ),
  tr: ({ children }) => (
    <tr className="border-b border-slate-700 hover:bg-slate-800/40 transition-colors">{children}</tr>
  ),
  th: ({ children }) => (
    <th className="px-4 py-2.5 text-left font-semibold text-white text-sm uppercase tracking-wider">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-2.5 text-slate-300">{children}</td>
  ),
};

export default function App() {
  const [user, setUser]         = useState(null);
  const [messages, setMessages] = useState([]);
  const [sources, setSources]   = useState([]);
  const [history, setHistory]   = useState([]);
  const sessionId               = useRef(makeSessionId());
  const bottomRef               = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleResponse = (question, data) => {
    setMessages((prev) => {
      const updated = [
        ...prev,
        { role: "user", text: question },
        { role: "assistant", text: data.answer },
      ];

      setHistory((prevH) => {
        const idx = prevH.findIndex((h) => h.id === sessionId.current);
        if (idx === -1) {
          return [
            { id: sessionId.current, title: question.slice(0, 40), messages: updated, sources: data.sources },
            ...prevH,
          ];
        }
        const copy = [...prevH];
        copy[idx] = { ...copy[idx], messages: updated, sources: data.sources };
        return copy;
      });

      return updated;
    });
    setSources(data.sources);
  };

  const handleNewChat = async () => {
    await fetch("http://localhost:8000/clear", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ session_id: sessionId.current }),
    }).catch(() => {});

    sessionId.current = makeSessionId();
    setMessages([]);
    setSources([]);
  };

  const handleLoadHistory = (entry) => {
    sessionId.current = entry.id;
    setMessages(entry.messages);
    setSources(entry.sources);
  };

  return (
    <div className="flex h-screen bg-slate-950 text-white">

      <Sidebar
        user={user}
        setUser={setUser}
        onNewChat={handleNewChat}
        history={history}
        onLoadHistory={handleLoadHistory}
        activeId={sessionId.current}
      />

      {/* Center chat area */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <h2 className="text-4xl font-bold text-slate-200">
                Good to see you
              </h2>
              <p className="text-slate-500 text-base">What do you want to know today?</p>
            </div>
          ) : (
            <div className="py-6">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`px-6 py-3 ${
                    msg.role === "user"
                      ? "flex justify-end"
                      : "flex justify-start"
                  }`}
                >
                  {msg.role === "assistant" ? (
                    <div className="flex gap-4 w-full max-w-3xl">
                      {/* Avatar */}
                      <div className="w-8 h-8 rounded-full bg-indigo-600 flex-shrink-0 flex items-center justify-center mt-0.5 shadow-lg">
                        <span className="text-white text-xs font-bold">S</span>
                      </div>
                      {/* Content — no box, clean text */}
                      <div className="flex-1 min-w-0 text-base">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={markdownComponents}
                        >
                          {msg.text}
                        </ReactMarkdown>
                      </div>
                    </div>
                  ) : (
                    <div className="max-w-xl bg-slate-700/70 text-white px-4 py-3 rounded-2xl text-[15px] leading-relaxed">
                      {msg.text}
                    </div>
                  )}
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input at bottom */}
        <div className="px-6 pb-6 pt-2 border-t border-slate-800/50">
          <ChatInput
            username={user ? user.name : "Guest"}
            onResponse={handleResponse}
            sessionId={sessionId.current}
          />
        </div>
      </div>

      <SourcesPanel sources={sources} />

    </div>
  );
}
