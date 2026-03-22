"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { fetchCapabilityDomains } from "@/app/actions";

export default function CapabilitiesIndexPage() {
  const { token, isLoading } = useAuth();
  const router = useRouter();
  const [empty, setEmpty] = useState(false);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  useEffect(() => {
    if (isLoading || !token) return;
    (async () => {
      const res = await fetchCapabilityDomains(token);
      if (res.success) {
        if (res.domains.length > 0) {
          router.replace(`/capabilities/${res.domains[0].slug}`);
        } else {
          setEmpty(true);
        }
      } else {
        setLoadErr(res.error);
      }
    })();
  }, [isLoading, token, router]);

  if (loadErr) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] px-6 text-center">
        <p className="text-red-400/90 text-sm">{loadErr}</p>
      </div>
    );
  }

  if (empty) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] px-6 text-center max-w-md mx-auto">
        <p className="text-neutral-300 text-sm mb-2">No domains in your catalog yet.</p>
        <p className="text-neutral-500 text-xs mb-6">
          Sync the capability registry to Neo4j or run an EA request so domains and capabilities appear
          for your tenant.
        </p>
        <Link href="/" className="text-indigo-400 text-sm hover:underline">
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-6 text-center">
      <p className="text-neutral-500 text-sm">Opening capability domains…</p>
    </div>
  );
}
