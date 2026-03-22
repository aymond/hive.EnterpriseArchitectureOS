"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useEffect, useState, useCallback } from "react";
import { fetchCapabilityDetail } from "@/app/actions";
import { ArrowLeft } from "lucide-react";

export default function CapabilityDetailPage() {
  const params = useParams();
  const domainSlug = typeof params.domainSlug === "string" ? params.domainSlug : "";
  const capabilitySlug =
    typeof params.capabilitySlug === "string" ? params.capabilitySlug : "";
  const { token, isLoading } = useAuth();

  const [domainName, setDomainName] = useState("");
  const [capName, setCapName] = useState("");
  const [description, setDescription] = useState("");
  const [parentName, setParentName] = useState<string | null>(null);
  const [sources, setSources] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    if (!token || !domainSlug || !capabilitySlug) return;
    setErr(null);
    setNotFound(false);
    const res = await fetchCapabilityDetail(domainSlug, capabilitySlug, token);
    if (res.success) {
      setDomainName(res.data.domain.name);
      setCapName(res.data.capability.name);
      setDescription(res.data.capability.description);
      setParentName(res.data.capability.parent_name);
      setSources(res.data.capability.sources || []);
    } else if (res.notFound) {
      setNotFound(true);
    } else {
      setErr(res.error);
    }
  }, [token, domainSlug, capabilitySlug]);

  useEffect(() => {
    load();
  }, [load]);

  if (isLoading) {
    return null;
  }

  if (notFound) {
    return (
      <div className="p-10 max-w-lg">
        <h1 className="text-xl font-bold text-white mb-2">Capability not found</h1>
        <Link
          href={`/capabilities/${domainSlug}`}
          className="text-indigo-400 text-sm hover:underline inline-flex items-center gap-1 mt-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to domain
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8 md:p-12 max-w-2xl">
      <Link
        href={`/capabilities/${domainSlug}`}
        className="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-widest text-neutral-500 hover:text-indigo-400 mb-8"
      >
        <ArrowLeft className="w-3 h-3" />
        {domainName || "Domain"}
      </Link>

      <header className="mb-8">
        <h1 className="text-3xl font-black tracking-tight text-white mb-3">{capName}</h1>
        <div className="flex flex-wrap gap-1">
          {sources.map((s) => (
            <span
              key={s}
              className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-neutral-800 text-neutral-400"
            >
              {s}
            </span>
          ))}
        </div>
      </header>

      {err && <p className="text-sm text-red-400 mb-4">{err}</p>}

      {parentName && (
        <p className="text-sm text-neutral-400 mb-4">
          <span className="text-neutral-500">Parent capability:</span> {parentName}
        </p>
      )}

      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/40 p-6">
        {description ? (
          <p className="text-neutral-300 text-sm leading-relaxed whitespace-pre-wrap">
            {description}
          </p>
        ) : (
          <p className="text-neutral-500 text-sm italic">No description in catalog or graph.</p>
        )}
      </div>

      <p className="text-xs text-neutral-600 mt-8 leading-relaxed">
        Tenant-specific data comes from your Neo4j graph; static registry entries are merged for
        exploration. Domain administration per tenant may arrive in a future release.
      </p>
    </div>
  );
}
