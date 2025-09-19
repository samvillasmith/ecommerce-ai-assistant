/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const CHAT_ENDPOINT = `${API_BASE}/chat`;

type ChatResponse = { response: string; history: string[] };
type Bubble = { role: "user" | "assistant" | "system" | "other"; text: string };

/** Price formatting with ".99" rule */
function formatPricesSmart(text: string): string {
  const RE = /(\$)?\s*(\d{1,3}(?:[,\.\s]\d{3})+|\d{3,})(?:[,\.\s]\d+)?(?!\d)/g;
  return text.replace(RE, (_, dollar: string | undefined, num: string) => {
    const digits = num.replace(/[,\.\s]/g, "");
    if (!/^\d+$/.test(digits)) return `${dollar ?? ""}${num}`;
    if (digits.endsWith("99") && digits.length >= 3) {
      const head = digits.slice(0, -2) || "0";
      const headGrouped = Number.parseInt(head, 10).toLocaleString("en-US");
      return `${dollar ?? ""}${headGrouped}.99`;
    }
    const n = Number.parseInt(digits, 10);
    return `${dollar ?? ""}${n.toLocaleString("en-US")}`;
  });
}

function parseHistory(history: string[]): Bubble[] {
  return (history ?? []).map((line) => {
    const idx = line.indexOf(":");
    if (idx === -1) return { role: "other", text: formatPricesSmart(line) };
    const roleRaw = line.slice(0, idx).trim().toLowerCase();
    const text = formatPricesSmart(line.slice(idx + 1).trim());
    if (roleRaw.startsWith("user")) return { role: "user", text };
    if (roleRaw.startsWith("assistant")) return { role: "assistant", text };
    if (roleRaw.startsWith("system")) return { role: "system", text };
    return { role: "other", text };
  });
}

function normalizeHistoryLines(lines: string[] | null | undefined): string[] | null {
  if (!Array.isArray(lines)) return null;
  return lines.map((line) => {
    const idx = line.indexOf(":");
    if (idx === -1) return formatPricesSmart(line);
    const role = line.slice(0, idx + 1);
    const text = line.slice(idx + 1);
    return `${role} ${formatPricesSmart(text.trim())}`;
  });
}

function cx(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

export default function ChatHome() {
  const [history, setHistory] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // restore history per-tab
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("chat_history");
      if (saved) {
        const parsed = JSON.parse(saved) as string[];
        setHistory(normalizeHistoryLines(parsed) ?? []);
      }
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

      const lastUser = optimistic[optimistic.length - 1];
      const serverRaw = Array.isArray(data.history) ? data.history : null;
      const serverHist = normalizeHistoryLines(serverRaw);
      const serverHasOurUser =
        !!serverHist && serverHist.some((l) => l.trim().toLowerCase() === lastUser.trim().toLowerCase());

      if (serverHist && serverHist.length && serverHasOurUser) {
        setHistory(serverHist);
      } else {
        const responseText =
          typeof data.response === "string" && data.response.trim().length
            ? formatPricesSmart(data.response.trim())
            : "(no response)";
        setHistory([...optimistic, `Assistant: ${responseText}`]);
      }
    } catch (e: any) {
      setError(e?.message ?? "Request failed");
      setHistory((prev) => prev.slice(0, -1)); // rollback optimistic message
    } finally {
      setPending(false);
      scrollToBottom();
    }
  }, [history, input, pending, scrollToBottom]);

  return (
    <div className="min-h-screen bg-white">
      {/* Clean, minimal header */}
      <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <div className="h-10 w-10 rounded-lg bg-black grid place-items-center text-white font-bold text-sm">
                SA
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">Shopping Assistant</h1>
                <p className="text-xs text-gray-500">AI-powered product search</p>
              </div>
            </div>
            
            <nav className="hidden md:flex items-center gap-6">
              <button className="text-sm font-medium text-gray-900 pb-2 border-b-2 border-black">
                Chat
              </button>
              <button className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
                Products
              </button>
              <button className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
                Orders
              </button>
              <button className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
                Account
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Simple hero section */}
      <section className="bg-gray-50 border-b border-gray-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8">
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold text-gray-900 tracking-tight">
              Find what you&apos;re looking for
            </h2>
            <p className="mt-2 text-base text-gray-600">
              Search our entire catalog by brand, style, color, or price. Get instant, accurate results.
            </p>
            <div className="flex gap-3 mt-4">
              <span className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-green-50 text-green-700 font-medium">
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Free shipping over $50
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 font-medium">
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                30-day returns
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Main chat interface */}
      <main className="mx-auto max-w-4xl px-4 sm:px-6 py-6">
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          
          {/* Messages area */}
          <div ref={scrollRef} className="h-[calc(100vh-360px)] overflow-y-auto" aria-live="polite">
            {bubbles.length === 0 ? (
              <div className="h-full flex items-center justify-center p-8">
                <div className="text-center max-w-md">
                  <div className="mb-6">
                    <svg className="w-16 h-16 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    Start a conversation
                  </h3>
                  <p className="text-sm text-gray-500 mb-6">
                    Ask about specific products or browse by category
                  </p>
                  <div className="grid grid-cols-2 gap-3 text-left">
                    <button 
                      onClick={() => setInput("Show me all Nike shoes under $100")}
                      className="p-3 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all text-left group"
                    >
                      <div className="font-medium text-sm text-gray-900 group-hover:text-black">Popular searches</div>
                      <div className="text-xs text-gray-500 mt-1">Nike under $100</div>
                    </button>
                    <button 
                      onClick={() => setInput("Do you have any Vans in black?")}
                      className="p-3 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all text-left group"
                    >
                      <div className="font-medium text-sm text-gray-900 group-hover:text-black">By color</div>
                      <div className="text-xs text-gray-500 mt-1">Black Vans</div>
                    </button>
                    <button 
                      onClick={() => setInput("What running shoes do you have?")}
                      className="p-3 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all text-left group"
                    >
                      <div className="font-medium text-sm text-gray-900 group-hover:text-black">By category</div>
                      <div className="text-xs text-gray-500 mt-1">Running shoes</div>
                    </button>
                    <button 
                      onClick={() => setInput("Show me your newest arrivals")}
                      className="p-3 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all text-left group"
                    >
                      <div className="font-medium text-sm text-gray-900 group-hover:text-black">New releases</div>
                      <div className="text-xs text-gray-500 mt-1">Latest arrivals</div>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 sm:p-6 space-y-4">
                {bubbles.map((b, i) => (
                  <div key={i} className={cx("flex gap-3", b.role === "user" ? "justify-end" : "justify-start")}>
                    {b.role !== "user" && (
                      <div className="shrink-0 h-8 w-8 rounded-lg bg-black grid place-items-center text-white text-xs font-bold">
                        SA
                      </div>
                    )}
                    <div
                      className={cx(
                        "max-w-[75%] px-4 py-2.5 rounded-2xl text-sm",
                        b.role === "user"
                          ? "bg-black text-white"
                          : "bg-gray-100 text-gray-900"
                      )}
                    >
                      {formatPricesSmart(b.text)}
                    </div>
                    {b.role === "user" && (
                      <div className="shrink-0 h-8 w-8 rounded-lg bg-gray-200 grid place-items-center text-gray-600 text-xs font-bold">
                        U
                      </div>
                    )}
                  </div>
                ))}
                {pending && (
                  <div className="flex gap-3">
                    <div className="shrink-0 h-8 w-8 rounded-lg bg-black grid place-items-center text-white text-xs font-bold">
                      SA
                    </div>
                    <div className="px-4 py-2.5 rounded-2xl bg-gray-100 text-gray-500 text-sm flex items-center gap-2">
                      <span className="inline-flex gap-1">
                        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse"></span>
                        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{animationDelay: '200ms'}}></span>
                        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{animationDelay: '400ms'}}></span>
                      </span>
                      Searching catalog...
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Error message */}
          {error && (
            <div className="px-4 sm:px-6">
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex items-start gap-2">
                <svg className="w-4 h-4 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                {error}
              </div>
            </div>
          )}

          {/* Input area */}
          <div className="border-t border-gray-200 p-4 sm:p-6 bg-gray-50">
            <div className="flex gap-3">
              <input
                className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 placeholder-gray-400 outline-none focus:border-gray-400 focus:ring-1 focus:ring-gray-400 transition-all"
                placeholder="Ask about products, brands, or categories..."
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
                className="px-6 py-3 rounded-xl bg-black hover:bg-gray-800 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Send
              </button>
            </div>
            
            <div className="mt-3 flex flex-wrap gap-2">
              {["Shoes under $60", "Nike running", "Adidas originals", "New arrivals"].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-xs text-gray-600 hover:border-gray-300 hover:text-gray-900 transition-all"
                >
                  {suggestion}
                </button>
              ))}
            </div>
            
            <p className="mt-3 text-center text-xs text-gray-400">
              AI responses are based on current inventory • Prices and availability subject to change
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}