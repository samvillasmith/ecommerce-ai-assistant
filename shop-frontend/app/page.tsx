/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const CHAT_ENDPOINT = `${API_BASE}/chat`;

type ChatResponse = { response: string; history: string[] };
type Bubble = { role: "user" | "assistant" | "system" | "other"; text: string };

// --- helpers -----------------------------------------------------------------
function parseHistory(history: string[]): Bubble[] {
  return (history ?? []).map((line) => {
    const [prefix, ...rest] = line.split(":");
    const text = rest.join(":").trim();
    const role = prefix?.trim().toLowerCase();
    if (role?.startsWith("user")) return { role: "user", text };
    if (role?.startsWith("assistant")) return { role: "assistant", text };
    if (role?.startsWith("system")) return { role: "system", text };
    return { role: "other", text: line };
  });
}

function classNames(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

export default function ChatHome() {
  const [history, setHistory] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Restore history per-tab so refreshes keep the convo
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("chat_history");
      if (saved) setHistory(JSON.parse(saved));
    } catch {}
  }, []);
  useEffect(() => {
    try {
      sessionStorage.setItem("chat_history", JSON.stringify(history));
    } catch {}
  }, [history]);

  const bubbles = useMemo(() => parseHistory(history), [history]);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  }, []);

  const send = useCallback(async () => {
    const query = input.trim();
    if (!query || pending) return;
    setError(null);
    setPending(true);

    // optimistic user message
    const optimistic = [...history, `User: ${query}`];
    setHistory(optimistic);
    setInput("");

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30_000);

      const res = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, history }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(body || `HTTP ${res.status}`);
      }

      const data: ChatResponse = await res.json();

// Robust merge: if server returned a usable history that includes our last user line, trust it.
// Otherwise, keep our optimistic history and append the assistant reply.
      const lastUser = optimistic[optimistic.length - 1];
      const serverHist = Array.isArray(data.history) ? data.history : null;
      const serverHasOurUser =
        !!serverHist && serverHist.some((l) => l.trim().toLowerCase() === lastUser.trim().toLowerCase());

      if (serverHist && serverHist.length && serverHasOurUser) {
        setHistory(serverHist);
      } else {
        // synthesize the assistant bubble if needed
        const assistantLine =
          typeof data.response === "string" && data.response.trim().length
            ? `Assistant: ${data.response.trim()}`
            : `Assistant: (no response)`;
        setHistory([...optimistic, assistantLine]);
      }

    } catch (e: any) {
      setError(e?.message ?? "Request failed");
      setHistory((prev) => prev.slice(0, -1)); // rollback optimistic user msg
    } finally {
      setPending(false);
      scrollToBottom();
    }
  }, [history, input, pending, scrollToBottom]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  return (
    <div
      className={classNames(
        "min-h-screen text-neutral-900 dark:text-neutral-100",
        // subtle gradient bg
        "bg-[radial-gradient(90rem_50rem_at_10%_0%,#eaeaea,transparent),radial-gradient(90rem_60rem_at_90%_10%,#f7f7f7,transparent)]",
        "dark:bg-[radial-gradient(90rem_50rem_at_10%_0%,#0f0f10,transparent),radial-gradient(90rem_60rem_at_90%_10%,#0a0a0b,transparent)]"
      )}
    >
      {/* Top bar */}
      <header className="sticky top-0 z-10 border-b border-black/5 dark:border-white/10 backdrop-blur bg-white/70 dark:bg-black/40">
        <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-2xl bg-black dark:bg-white text-white dark:text-black grid place-items-center font-bold shadow-sm">
              SA
            </div>
            <div>
              <h1 className="text-base font-semibold leading-tight">Shop Assistant</h1>
              <p className="text-xs text-neutral-500">
                Answers only from your product catalog
              </p>
            </div>
          </div>
          <code className="hidden md:block text-[10px] text-neutral-500">
            {CHAT_ENDPOINT}
          </code>
        </div>
      </header>

      {/* Chat card */}
      <main className="mx-auto w-full max-w-5xl px-4 py-6">
        <div className="rounded-3xl border border-black/5 dark:border-white/10 bg-white/70 dark:bg-black/40 shadow-lg backdrop-blur">
          {/* message list */}
          <div
            ref={scrollRef}
            className="h-[calc(100vh-260px)] overflow-y-auto p-5 sm:p-6"
            aria-live="polite"
          >
            {bubbles.length === 0 ? (
              <div className="h-full grid place-items-center text-center">
                <div className="space-y-2">
                  <h2 className="text-xl font-semibold">Ask about products</h2>
                  <p className="text-sm text-neutral-500">
                    Try <span className="font-mono">“red running shoes under $100”</span> or{" "}
                    <span className="font-mono">“what colors does Stan Smith come in?”</span>
                  </p>
                </div>
              </div>
            ) : (
              <ul className="space-y-3">
                {bubbles.map((b, i) => (
                  <li key={i} className={classNames("flex", b.role === "user" ? "justify-end" : "justify-start")}>
                    <div
                      className={classNames(
                        "rounded-2xl px-4 py-2 shadow-sm max-w-[80%] whitespace-pre-wrap",
                        b.role === "user"
                          ? "bg-black text-white dark:bg-white dark:text-black"
                          : "bg-neutral-100/90 dark:bg-neutral-900/70"
                      )}
                    >
                      {b.text}
                    </div>
                  </li>
                ))}
                {pending && (
                  <li className="flex justify-start">
                    <div className="rounded-2xl px-4 py-2 shadow-sm max-w-[80%] bg-neutral-100/90 dark:bg-neutral-900/70 text-neutral-500 text-sm inline-flex items-center gap-2">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neutral-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-neutral-500" />
                      </span>
                      Thinking…
                    </div>
                  </li>
                )}
              </ul>
            )}
          </div>

          {/* error */}
          {error && (
            <div className="px-5 sm:px-6">
              <div className="mb-3 rounded-xl border border-red-200/70 bg-red-50/80 dark:bg-red-900/20 dark:border-red-900/40 p-3 text-sm text-red-700 dark:text-red-300">
                {error}
              </div>
            </div>
          )}

          {/* composer */}
          <div className="border-t border-black/5 dark:border-white/10 p-4 sm:p-5">
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-xl border border-black/10 dark:border-white/10 bg-white/70 dark:bg-black/30 px-4 py-3 outline-none focus:ring-2 focus:ring-black dark:focus:ring-white"
                placeholder="Ask about products…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                aria-label="Message"
                disabled={pending}
              />
              <button
                onClick={() => void send()}
                disabled={pending || input.trim().length === 0}
                className="rounded-xl bg-black dark:bg-white text-white dark:text-black px-5 py-3 font-medium disabled:opacity-40 shadow-sm"
              >
                Send
              </button>
            </div>
            <p className="mt-2 text-[11px] text-neutral-500">
              Grounded to your catalog. If it’s not in Pinecone/MySQL, the assistant will say so.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
