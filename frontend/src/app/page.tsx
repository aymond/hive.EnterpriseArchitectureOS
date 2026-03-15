"use client";

import React, { useState, useEffect } from "react";
import { submitEARequest, fetchProposals, getProposalById } from "./actions";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Mermaid from "@/components/Mermaid";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [proposals, setProposals] = useState<any[]>([]);
  const [showRepo, setShowRepo] = useState(false);

  useEffect(() => {
    loadProposals();
  }, []);

  const loadProposals = async () => {
    const res = await fetchProposals();
    if (res.success) setProposals(res.data);
  };

  const handleSelectProposal = async (id: string) => {
    setLoading(true);
    setError(null);
    const res = await getProposalById(id);
    if (res.success) {
      setResult({
        ...res.data,
        engaged_domains: [], 
        quality_check: "APPROVED",
        status: "HISTORICAL"
      });
      setShowRepo(false);
    } else {
      setError("Failed to load historical proposal.");
    }
    setLoading(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const res = await submitEARequest(query);

    if (res.success) {
      setResult(res.data);
      loadProposals();
    } else {
      setError(res.error || "An unknown error occurred while connecting to the Agents.");
    }
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-50 flex font-sans selection:bg-indigo-500/30 overflow-hidden">
      
      {/* Sidebar Repository Panel */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-80 bg-neutral-900 border-r border-neutral-800 transform transition-transform duration-300 ease-in-out ${showRepo ? "translate-x-0" : "-translate-x-full"} shadow-2xl overflow-hidden flex flex-col`}>
        <div className="p-6 border-b border-neutral-800 flex justify-between items-center bg-neutral-900/50 backdrop-blur-md">
          <h2 className="font-bold text-lg text-indigo-400">Reports Repository</h2>
          <button onClick={() => setShowRepo(false)} className="text-neutral-500 hover:text-white transition p-1 hover:bg-neutral-800 rounded-lg">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-hide">
          {proposals.length === 0 ? (
            <div className="text-center py-20 px-6">
              <div className="w-12 h-12 rounded-2xl bg-neutral-800 text-neutral-600 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
              </div>
              <p className="text-neutral-500 italic text-sm">No proposals saved yet.</p>
            </div>
          ) : (
            proposals.map((p) => (
              <button
                key={p.id}
                onClick={() => handleSelectProposal(p.id)}
                className="w-full text-left p-4 rounded-xl bg-neutral-950/50 border border-neutral-800 hover:border-indigo-500/50 hover:bg-neutral-800 transition group"
              >
                <p className="text-neutral-300 text-sm font-medium line-clamp-2 group-hover:text-indigo-300 transition mb-2">{p.query}</p>
                <div className="flex items-center gap-2 text-neutral-600 text-[10px] font-bold tracking-widest uppercase">
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                  {new Date(p.timestamp).toLocaleDateString()}
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto relative scroll-smooth h-screen">
        
        {/* Repository Toggle Button - Fixed Floating */}
        <button 
          onClick={() => setShowRepo(true)}
          className="fixed top-8 left-8 z-40 p-4 rounded-2xl bg-neutral-900/80 backdrop-blur-md border border-neutral-800 text-neutral-400 hover:text-indigo-400 hover:border-indigo-500/50 transition duration-300 shadow-2xl group flex items-center gap-3"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <span className="max-w-0 overflow-hidden whitespace-nowrap group-hover:max-w-xs transition-all duration-500 ease-in-out font-bold text-xs tracking-widest uppercase">Repository</span>
        </button>

        <div className="w-full flex justify-center">
          <div className="max-w-5xl w-full space-y-16 px-6 py-12 md:py-24">
            
            {/* Header */}
            <header className="space-y-8 text-center max-w-3xl mx-auto">
              <div className="inline-flex items-center justify-center p-4 mb-4 rounded-3xl bg-indigo-500/10 text-indigo-400 ring-1 ring-inset ring-indigo-500/20 shadow-indigo-500/5 animate-pulse">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
              </div>
              <div className="space-y-4">
                <h1 className="text-4xl md:text-5xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-br from-white via-indigo-200 to-indigo-500 leading-tight">
                  Enterprise Architecture OS
                </h1>
                <p className="text-neutral-500 max-w-2xl mx-auto text-lg md:text-xl font-medium tracking-tight leading-relaxed">
                  Deploy your multi-agent architecture team to map capabilities, ensure governance, and source the best vendors.
                </p>
              </div>
            </header>

          {/* Search Input Section */}
          <form onSubmit={handleSubmit} className="relative group max-w-3xl mx-auto">
            <div className="absolute -inset-1 rounded-[2.5rem] bg-gradient-to-r from-indigo-500 via-cyan-500 to-emerald-500 opacity-20 blur-2xl transition duration-1000 group-hover:opacity-40"></div>
            <div className="relative flex flex-col md:flex-row items-center bg-neutral-900/80 backdrop-blur-xl rounded-[2rem] p-3 ring-1 ring-neutral-800 shadow-3xl hover:ring-neutral-700 transition duration-500">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="E.g., We need to build a new KYC capability..."
                className="w-full bg-transparent border-0 text-neutral-100 placeholder-neutral-600 px-6 py-4 md:py-3 focus:ring-0 outline-none text-xl font-light"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="w-full md:w-auto mt-2 md:mt-0 ml-0 md:ml-3 bg-white text-black hover:bg-neutral-200 px-10 py-4 rounded-2xl font-black text-xs tracking-[0.2em] uppercase transition-all shadow-2xl disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-3 active:scale-95"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 rounded-full border-2 border-neutral-900/20 border-t-neutral-900 animate-spin"></div>
                    Processing
                  </>
                ) : (
                  "Architect"
                )}
              </button>
            </div>
          </form>

          {/* Error Feed */}
          {error && (
            <div className="max-w-3xl mx-auto p-5 rounded-3xl bg-red-500/5 border border-red-500/20 text-red-400 flex items-center gap-4 animate-in fade-in slide-in-from-top-4 duration-500">
              <div className="p-2 bg-red-500/10 rounded-xl">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="font-semibold text-sm tracking-tight">{error}</p>
            </div>
          )}

          {/* Dynamic Result Display */}
          {result && (
            <div className="space-y-12 animate-in fade-in slide-in-from-bottom-12 duration-1000 ease-out py-8 border-t border-neutral-800/30">
              
              {/* Metrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                <StatusCard 
                  label="Context" 
                  value={result.engaged_domains?.length ? `${result.engaged_domains.length} Domains` : "Repository"} 
                  sub={result.engaged_domains?.join(", ") || "Archived Document"}
                />
                <StatusCard 
                  label="Governance" 
                  value={result.quality_check} 
                  status={result.quality_check === "APPROVED" ? "success" : "error"}
                />
                <StatusCard 
                  label="Origin" 
                  value={result.status === "HISTORICAL" ? "ARCHIVE" : "LIVE"} 
                  status="neutral"
                />
              </div>
              
              {/* Document Container */}
              <div className="bg-neutral-900/40 border border-neutral-800 rounded-[3rem] shadow-3xl relative overflow-hidden backdrop-blur-sm group/doc">
                <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-indigo-500/50 via-cyan-500/50 to-emerald-500/50 opacity-30 group-hover/doc:opacity-100 transition duration-1000"></div>
                
                <div className="p-10 md:p-20">
                  <header className="mb-16 pb-12 border-b border-neutral-800/40 flex flex-col md:flex-row justify-between items-start md:items-end gap-8">
                    <div className="space-y-4">
                      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 text-[10px] font-black tracking-widest uppercase mb-2 ring-1 ring-indigo-500/20">
                        {result.status === "HISTORICAL" ? "Verified Archive" : "Strategic Analysis"}
                      </div>
                      <h2 className="text-4xl md:text-5xl font-black text-white tracking-tighter leading-none">
                        EA Architecture Proposal
                      </h2>
                      {result.status === "HISTORICAL" && (
                        <p className="text-neutral-500 font-mono text-xs">COMMITTED: {new Date(result.timestamp).toUTCString()}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-4">
                      <DownloadButton text={result.content || result.response} filename={`ea-${result.id || "live"}.md`} />
                      <CopyButton text={result.content || result.response} />
                    </div>
                  </header>
                  
                  {/* Markdown Renderer with Styles */}
                  <div className="prose prose-invert prose-indigo max-w-none 
                                  selection:bg-indigo-500/40
                                  prose-headings:font-black prose-headings:tracking-tighter prose-headings:text-white
                                  prose-p:text-neutral-400 prose-p:leading-relaxed prose-p:text-lg prose-p:mb-10
                                  prose-li:text-neutral-400 prose-li:my-2 prose-li:text-lg
                                  prose-strong:text-white prose-strong:bg-white/5 prose-strong:px-1 prose-strong:rounded
                                  marker:text-indigo-500">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({node, ...props}) => <h1 className="text-6xl font-black mb-12 mt-4 border-b-2 border-neutral-800 pb-8 tracking-tighter" {...props} />,
                        h2: ({node, ...props}) => <h2 className="text-3xl font-black mb-8 mt-20 text-indigo-400 flex items-center gap-4 uppercase tracking-widest leading-none outline-none" {...props} />,
                        h3: ({node, ...props}) => <h3 className="text-2xl font-bold mb-6 mt-12 text-neutral-100 tracking-tight" {...props} />,
                        p: ({node, ...props}) => <p className="mb-10 leading-[1.8] text-neutral-400 font-medium text-lg" {...props} />,
                        ul: ({node, ...props}) => <ul className="list-none mb-10 space-y-4" {...props} />,
                        li: ({node, ...props}) => (
                          <li className="flex gap-4 items-start translate-x-2">
                             <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-3 flex-shrink-0 animate-pulse"></div>
                             <span {...props} />
                          </li>
                        ),
                        blockquote: ({node, ...props}) => (
                          <blockquote className="border-l-8 border-indigo-500 bg-indigo-500/5 px-10 py-8 rounded-3xl my-16 italic text-neutral-300 text-xl font-light leading-relaxed" {...props} />
                        ),
                        code: ({node, className, children, ...props}: any) => {
                          const match = /language-(\w+)/.exec(className || '');
                          const isMermaid = match?.[1] === 'mermaid';
                          
                          if (isMermaid) {
                            return <Mermaid chart={String(children).replace(/\n$/, '')} />;
                          }
                          
                          return (
                            <code className="bg-neutral-800/80 text-cyan-300 px-2 py-1 rounded-lg font-mono text-sm border border-neutral-700 shadow-inner" {...props}>
                              {children}
                            </code>
                          );
                        },
                        pre: ({node, children, ...props}: any) => {
                          // Check if any child is a Mermaid component to avoid wrapping in <pre>
                          const isMermaid = React.Children.toArray(children).some((child: any) => 
                            child.props?.className?.includes('language-mermaid')
                          );
                          
                          if (isMermaid) return <>{children}</>;
                          
                          return (
                            <pre className="bg-neutral-950/80 backdrop-blur-md p-10 rounded-[2.5rem] border border-neutral-800 my-16 overflow-x-auto shadow-4xl" {...props}>
                              {children}
                            </pre>
                          );
                        },
                      }}
                    >
                      {result.content || result.response || ""}
                    </ReactMarkdown>
                  </div>

                  <footer className="mt-24 pt-10 border-t border-neutral-800/40 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                      <span className="text-[10px] font-black uppercase tracking-[0.3em] text-neutral-600">Enterprise Orchestrator Active</span>
                    </div>
                    <span className="text-[10px] font-black uppercase tracking-[0.3em] text-neutral-700">© 2026 ARCHITECTURE OS</span>
                  </footer>
                </div>
              </div>
            </div>
          )}
          </div>
        </div>
      </div>
    </main>
  );
}

function DownloadButton({ text, filename }: { text: string, filename: string }) {
  const handleDownload = () => {
    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button 
      onClick={handleDownload}
      className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-neutral-800/50 text-neutral-400 border border-neutral-700 hover:border-indigo-500/50 hover:text-indigo-400 transition-all duration-300 font-bold text-xs tracking-widest uppercase shadow-xl active:scale-95"
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      Export
    </button>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button 
      onClick={handleCopy}
      className={`flex items-center gap-2 transition-all duration-300 px-6 py-3 rounded-2xl border font-bold text-xs tracking-widest uppercase shadow-xl active:scale-95 ${
        copied 
        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" 
        : "bg-neutral-800/50 text-neutral-400 border-neutral-700 hover:border-indigo-500/50 hover:text-indigo-400"
      }`}
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        {copied ? (
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        ) : (
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
        )}
      </svg>
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function StatusCard({ label, value, sub, status = "neutral" }: { label: string, value: string | number, sub?: string, status?: "success" | "error" | "neutral" }) {
  const colors = {
    success: "text-emerald-400 bg-emerald-400/5 border-emerald-500/20 shadow-emerald-500/5",
    error: "text-red-400 bg-red-400/5 border-red-500/20 shadow-red-500/5",
    neutral: "text-indigo-400 bg-indigo-400/5 border-indigo-500/20 shadow-indigo-500/5",
  };
  
  return (
    <div className="bg-neutral-900/40 backdrop-blur-md rounded-[2rem] p-8 border border-neutral-800 flex flex-col justify-between transition hover:border-neutral-700 hover:bg-neutral-900 group shadow-2xl">
      <div className="space-y-4">
        <span className="text-neutral-600 text-[10px] font-black tracking-[0.3em] uppercase group-hover:text-neutral-500 transition">{label}</span>
        <div className={`p-4 rounded-2xl border flex items-center justify-center font-black tracking-tighter text-2xl ${colors[status]}`}>
          {value}
        </div>
      </div>
      {sub && <p className="text-neutral-500 text-xs mt-6 font-medium leading-relaxed italic">{sub}</p>}
    </div>
  );
}
