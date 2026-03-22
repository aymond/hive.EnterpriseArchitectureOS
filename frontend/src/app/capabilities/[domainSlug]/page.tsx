"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useEffect, useState, useCallback } from "react";
import {
  fetchCapabilitiesForDomain,
  fetchApiKeyStatus,
  type CatalogCapability,
} from "@/app/actions";
import { submitEARequestStream } from "@/lib/stream";
import { Plus, ExternalLink, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function buildScopedQuery(domainName: string, userNotes: string): string {
  const notes = userNotes.trim() || "(none)";
  return `Enterprise Architecture request — scoped to the tenant capability map.

Target domain: ${domainName}

Task: Design and document a NEW capability for this domain. Describe the business need, candidate capability name, how it relates to existing capabilities in the domain, and key processes or applications.

Produce the full EA analysis (capability model, processes, technology landscape where relevant, governance notes) so results can align with our knowledge graph.

Additional context from the user:
${notes}`;
}

export default function DomainCapabilitiesPage() {
  const params = useParams();
  const domainSlug = typeof params.domainSlug === "string" ? params.domainSlug : "";
  const { token, isLoading } = useAuth();
  const router = useRouter();

  const [domainName, setDomainName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [caps, setCaps] = useState<CatalogCapability[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const [showBuild, setShowBuild] = useState(false);
  const [notes, setNotes] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamErr, setStreamErr] = useState<string | null>(null);
  const [nodes, setNodes] = useState<{ node: string; duration?: number }[]>([]);
  const [finalText, setFinalText] = useState<string | null>(null);

  const [hasApiKey, setHasApiKey] = useState(false);
  const [hasTavilyKey, setHasTavilyKey] = useState(false);
  const [requiresOpenAiApiKey, setRequiresOpenAiApiKey] = useState(true);

  const load = useCallback(async () => {
    if (!token || !domainSlug) return;
    setErr(null);
    setNotFound(false);
    const res = await fetchCapabilitiesForDomain(domainSlug, token);
    if (res.success) {
      setDomainName(res.data.domain.name);
      setPurpose(res.data.domain.purpose || "");
      setCaps(res.data.capabilities);
    } else if (res.notFound) {
      setNotFound(true);
    } else {
      setErr(res.error);
    }
  }, [token, domainSlug]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!token) return;
    (async () => {
      const s = await fetchApiKeyStatus(token);
      if (s.success) {
        setHasApiKey(s.hasKey);
        setHasTavilyKey(s.hasTavilyKey || false);
        setRequiresOpenAiApiKey(s.requiresOpenAiApiKey ?? true);
      }
    })();
  }, [token]);

  const openBuild = () => {
    setStreamErr(null);
    setNodes([]);
    setFinalText(null);
    setShowBuild(true);
  };

  const runBuild = () => {
    if (!token || !domainName) return;
    const needOpenAi = requiresOpenAiApiKey && !hasApiKey;
    if (needOpenAi || !hasTavilyKey) {
      router.push("/profile#integrations");
      return;
    }
    const q = buildScopedQuery(domainName, notes);
    setStreaming(true);
    setStreamErr(null);
    setNodes([]);
    setFinalText(null);
    submitEARequestStream(
      q,
      token,
      (event) => {
        setNodes((prev) => [...prev, { node: event.node, duration: event.duration_ms }]);
      },
      (finalData) => {
        const payload = finalData.data ? finalData.data : finalData;
        setFinalText(payload.response || "");
        setStreaming(false);
      },
      (e) => {
        setStreamErr(e);
        setStreaming(false);
      }
    );
  };

  if (isLoading) {
    return null;
  }

  if (notFound) {
    return (
      <div className="p-10 max-w-lg">
        <h1 className="text-xl font-bold text-white mb-2">Domain not found</h1>
        <p className="text-neutral-500 text-sm mb-6">
          This URL may be invalid or the domain is not in your tenant catalog.
        </p>
        <Link href="/capabilities" className="text-indigo-400 text-sm hover:underline">
          Back to capabilities
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8 md:p-12 max-w-4xl">
      <header className="mb-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 mb-2">
          Domain
        </p>
        <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white mb-3">
          {domainName || "…"}
        </h1>
        {purpose ? (
          <p className="text-neutral-400 text-sm md:text-base leading-relaxed max-w-2xl">
            {purpose}
          </p>
        ) : null}
        <button
          type="button"
          onClick={openBuild}
          className="mt-6 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-indigo-600 to-cyan-600 px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 hover:opacity-95"
        >
          <Plus className="w-4 h-4" />
          Build new capability
        </button>
      </header>

      {err && (
        <p className="text-sm text-red-400/90 mb-6">{err}</p>
      )}

      <section>
        <h2 className="text-xs font-bold uppercase tracking-widest text-neutral-500 mb-4">
          Catalog ({caps.length})
        </h2>
        {caps.length === 0 ? (
          <p className="text-neutral-500 text-sm italic">
            No capabilities yet for this domain in the registry or graph. Use “Build new capability” to add via the agent pipeline.
          </p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {caps.map((c) => (
              <li key={c.slug}>
                <Link
                  href={`/capabilities/${domainSlug}/${c.slug}`}
                  className="block rounded-2xl border border-neutral-800 bg-neutral-900/40 p-4 hover:border-indigo-500/40 transition group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-neutral-100 group-hover:text-indigo-200">
                      {c.name}
                    </span>
                    <ExternalLink className="w-4 h-4 text-neutral-600 group-hover:text-indigo-400 shrink-0" />
                  </div>
                  {c.parent_name ? (
                    <p className="text-[11px] text-neutral-500 mt-1">
                      Under: {c.parent_name}
                    </p>
                  ) : null}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {c.sources.map((s) => (
                      <span
                        key={s}
                        className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {showBuild && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-neutral-800 bg-neutral-900 shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-4 border-b border-neutral-800">
              <h3 className="font-bold text-white">Build new capability</h3>
              <button
                type="button"
                onClick={() => !streaming && setShowBuild(false)}
                className="p-1 rounded-lg text-neutral-500 hover:text-white hover:bg-neutral-800"
                disabled={streaming}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 space-y-4">
              <p className="text-xs text-neutral-500">
                Runs the same multi-agent pipeline as the dashboard, with the query scoped to{" "}
                <span className="text-neutral-300">{domainName}</span>.
              </p>
              <label className="block text-xs font-bold uppercase tracking-widest text-neutral-500">
                Optional context
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  disabled={streaming}
                  placeholder="Business driver, constraints, stakeholders…"
                  className="mt-2 w-full rounded-xl bg-neutral-950 border border-neutral-800 text-sm text-neutral-200 p-3 focus:ring-1 focus:ring-indigo-500 outline-none resize-none"
                />
              </label>
              {!streaming && !finalText && (
                <button
                  type="button"
                  onClick={runBuild}
                  className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-bold text-white hover:bg-indigo-500"
                >
                  Start agent pipeline
                </button>
              )}
              {streamErr && (
                <p className="text-sm text-red-400">{streamErr}</p>
              )}
              {nodes.length > 0 && (
                <div className="text-xs text-neutral-500 space-y-1 max-h-24 overflow-y-auto">
                  {nodes.map((n, i) => (
                    <div key={`${n.node}-${i}`}>
                      {n.node}
                      {n.duration != null ? ` · ${n.duration}ms` : ""}
                    </div>
                  ))}
                </div>
              )}
              {finalText && (
                <div className="prose prose-invert prose-sm max-w-none border-t border-neutral-800 pt-4">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalText}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
