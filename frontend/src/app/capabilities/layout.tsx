"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import { fetchCapabilityDomains, type CapabilityDomainSummary } from "@/app/actions";
import { Layers, LogOut, Home } from "lucide-react";

export default function CapabilitiesLayout({ children }: { children: React.ReactNode }) {
  const { user, token, logout, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [domains, setDomains] = useState<CapabilityDomainSummary[]>([]);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  useEffect(() => {
    if (isLoading || !token) return;
    (async () => {
      const res = await fetchCapabilityDomains(token);
      if (res.success) {
        setDomains(res.domains);
        setLoadErr(null);
      } else {
        setLoadErr(res.error);
      }
    })();
  }, [token, isLoading]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-white">
        <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
        <p className="text-neutral-500 font-medium tracking-wide">Loading…</p>
      </div>
    );
  }

  const activeSlug = pathname?.split("/capabilities/")[1]?.split("/")[0] || "";

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-50 flex font-sans">
      <aside className="w-64 shrink-0 border-r border-neutral-800 bg-neutral-900/50 flex flex-col">
        <div className="p-4 border-b border-neutral-800 flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-400" />
          <span className="font-bold text-sm tracking-tight">Capabilities</span>
        </div>
        <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {loadErr && (
            <p className="text-xs text-red-400/90 px-2 py-2">{loadErr}</p>
          )}
          {domains.map((d) => {
            const active = activeSlug === d.slug;
            return (
              <Link
                key={d.slug}
                href={`/capabilities/${d.slug}`}
                className={`block rounded-lg px-3 py-2 text-sm transition ${
                  active
                    ? "bg-indigo-500/15 text-indigo-200 ring-1 ring-indigo-500/30"
                    : "text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200"
                }`}
              >
                <span className="font-medium">{d.name}</span>
                <span className="block text-[10px] text-neutral-500 mt-0.5">
                  {d.capability_count} capability{d.capability_count === 1 ? "" : "ies"}
                </span>
              </Link>
            );
          })}
        </nav>
        <div className="p-2 border-t border-neutral-800 space-y-1">
          <Link
            href="/"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-800 hover:text-white"
          >
            <Home className="w-4 h-4" />
            Dashboard
          </Link>
          <button
            type="button"
            onClick={logout}
            className="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-neutral-500 hover:bg-neutral-800 hover:text-red-400"
          >
            <LogOut className="w-4 h-4" />
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto min-h-screen">{children}</main>
    </div>
  );
}
