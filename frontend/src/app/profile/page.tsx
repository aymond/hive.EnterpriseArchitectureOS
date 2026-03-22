'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { User, Mail, Database, LogOut, ArrowLeft, Shield, Cpu } from 'lucide-react';
import Link from 'next/link';
import { fetchLlmModels, updateLlmModel } from '@/app/actions';

export default function ProfilePage() {
  const { user, token, logout, isLoading, refreshProfile } = useAuth();
  const [llmModels, setLlmModels] = useState<string[]>([]);
  const [llmDefault, setLlmDefault] = useState('gpt-4o');
  const [selectedLlm, setSelectedLlm] = useState('gpt-4o');
  const [llmSaving, setLlmSaving] = useState(false);
  const [llmMessage, setLlmMessage] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const res = await fetchLlmModels();
      if (res.success) {
        setLlmModels(res.models);
        setLlmDefault(res.defaultModel);
      }
    })();
  }, []);

  useEffect(() => {
    if (user?.llm_model) {
      setSelectedLlm(user.llm_model);
    }
  }, [user?.llm_model]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-[#050505] flex flex-col items-center justify-center p-4">
        <h1 className="text-xl text-white font-bold mb-4">Unauthenticated</h1>
        <Link href="/login" className="bg-blue-600 px-6 py-2 rounded-xl text-white font-semibold">
          Go to Login
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-300 p-6 selection:bg-blue-500/30">
      <div className="max-w-2xl mx-auto space-y-8 mt-12">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors group">
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
            <span>Dashboard</span>
          </Link>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-red-500 hover:text-red-400 font-semibold transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>
        </div>

        {/* Profile Card */}
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600/20 to-indigo-600/20 rounded-3xl blur opacity-75"></div>
          <div className="relative bg-zinc-900/90 border border-white/5 rounded-3xl p-10 backdrop-blur-xl">
            <div className="flex items-center gap-6 mb-12">
              <div className="w-24 h-24 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center text-white text-3xl font-bold shadow-2xl shadow-blue-500/20">
                {user.full_name?.charAt(0) || user.email?.charAt(0).toUpperCase()}
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">{user.full_name}</h1>
                <p className="text-zinc-500 flex items-center gap-1.5 mt-1">
                  <Shield className="w-4 h-4" />
                  Enterprise Architect
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Email Address</label>
                <div className="flex items-center gap-3 bg-black/40 border border-white/5 p-4 rounded-xl">
                  <Mail className="w-5 h-5 text-blue-400" />
                  <span className="text-white font-medium">{user.email}</span>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Tenant ID</label>
                <div className="flex items-center gap-3 bg-black/40 border border-white/5 p-4 rounded-xl">
                  <Database className="w-5 h-5 text-indigo-400" />
                  <span className="text-white font-medium">{user.tenant_id}</span>
                </div>
              </div>
            </div>

            <div className="mt-12 p-6 bg-blue-600/5 border border-blue-500/10 rounded-2xl">
              <h3 className="text-white font-semibold mb-2">SaaS Context</h3>
              <p className="text-sm text-zinc-400 leading-relaxed">
                Your account is currently scoped to the <span className="text-blue-400 font-mono">{user.tenant_id}</span> organization. 
                All architectural reports and capability maps are strictly isolated to this tenant.
              </p>
            </div>

            <div className="mt-10 p-6 bg-zinc-950/80 border border-white/10 rounded-2xl space-y-4">
              <div className="flex items-center gap-2 text-white font-semibold">
                <Cpu className="w-5 h-5 text-indigo-400" />
                LLM model
              </div>
              <p className="text-sm text-zinc-400 leading-relaxed">
                Choose which OpenAI chat model runs for all agents (coordinator, domains, research, quality, persistence, discovery). Default:{' '}
                <span className="text-indigo-400 font-mono">{llmDefault}</span>.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
                <select
                  value={selectedLlm}
                  onChange={(e) => setSelectedLlm(e.target.value)}
                  className="flex-1 bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  disabled={!llmModels.length}
                >
                  {(llmModels.length ? llmModels : [selectedLlm]).map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={llmSaving || !token || selectedLlm === user?.llm_model}
                  onClick={async () => {
                    if (!token) return;
                    setLlmSaving(true);
                    setLlmMessage(null);
                    const res = await updateLlmModel(token, selectedLlm);
                    setLlmSaving(false);
                    if (res.success) {
                      setLlmMessage('Saved.');
                      await refreshProfile();
                    } else {
                      setLlmMessage(res.error || 'Save failed');
                    }
                  }}
                  className="px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
                >
                  {llmSaving ? 'Saving…' : 'Save model'}
                </button>
              </div>
              {llmMessage && (
                <p className={`text-sm ${llmMessage === 'Saved.' ? 'text-emerald-400' : 'text-red-400'}`}>{llmMessage}</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
