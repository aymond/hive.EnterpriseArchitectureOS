'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { User, Database, LogOut, ArrowLeft, Shield, Cpu, KeyRound, Lock } from 'lucide-react';
import Link from 'next/link';
import {
  fetchLlmConfig,
  updateLlmSettings,
  updateProfile,
  changePassword,
  updateApiKey,
  fetchApiKeyStatus,
  type LlmConfigResponse,
} from '@/app/actions';
import { getLlmModelHistory, rememberLlmModel } from '@/lib/llmModelHistory';

const OPENAI_COMPATIBLE = 'openai_compatible';

function ProfileContent() {
  const searchParams = useSearchParams();
  const { user, token, logout, isLoading, refreshProfile, updateSessionToken } = useAuth();

  const [llmConfig, setLlmConfig] = useState<LlmConfigResponse | null>(null);
  const [llmProvider, setLlmProvider] = useState('openai');
  const [openaiBaseUrl, setOpenaiBaseUrl] = useState('');
  const [llmModel, setLlmModel] = useState('gpt-4o');
  const [llmSaving, setLlmSaving] = useState(false);
  const [llmMessage, setLlmMessage] = useState<string | null>(null);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);

  const [apiKeyInput, setApiKeyInput] = useState('');
  const [tavilyKeyInput, setTavilyKeyInput] = useState('');
  const [hasOpenAiKey, setHasOpenAiKey] = useState(false);
  const [hasTavilyKey, setHasTavilyKey] = useState(false);
  const [requiresOpenAiApiKey, setRequiresOpenAiApiKey] = useState(true);
  const [keysSaving, setKeysSaving] = useState(false);
  const [keysMessage, setKeysMessage] = useState<string | null>(null);
  const [modelHistory, setModelHistory] = useState<string[]>([]);

  useEffect(() => {
    setModelHistory(getLlmModelHistory());
  }, []);

  useEffect(() => {
    (async () => {
      const res = await fetchLlmConfig();
      if (res.success) setLlmConfig(res.config);
    })();
  }, []);

  useEffect(() => {
    if (!user || !token) return;
    (async () => {
      const st = await fetchApiKeyStatus(token);
      if (st.success) {
        setHasOpenAiKey(st.hasKey);
        setHasTavilyKey(st.hasTavilyKey || false);
        setRequiresOpenAiApiKey(st.requiresOpenAiApiKey ?? true);
      }
    })();
  }, [user, token]);

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name || '');
    setEmail(user.email || '');
  }, [user?.full_name, user?.email]);

  // Sync LLM fields only from server — do not depend on llmConfig (avoids wiping the model when config loads).
  useEffect(() => {
    if (!user) return;
    setLlmProvider(user.llm_provider || 'openai');
    setOpenaiBaseUrl(user.openai_base_url || '');
    const m = user.llm_model;
    if (typeof m === 'string' && m.trim()) {
      setLlmModel(m.trim());
    }
  }, [user?.llm_provider, user?.openai_base_url, user?.llm_model]);

  // Defaults only when the server has no saved model yet and config is ready.
  useEffect(() => {
    if (!user || !llmConfig) return;
    const m = user.llm_model;
    if (typeof m === 'string' && m.trim()) return;
    const p = user.llm_provider || 'openai';
    setLlmModel(
      p === OPENAI_COMPATIBLE
        ? llmConfig.default_compatible_model || 'llama3.2'
        : llmConfig.default_openai_model || 'gpt-4o'
    );
  }, [user, llmConfig, user?.llm_model, user?.llm_provider]);

  useEffect(() => {
    const hash = typeof window !== 'undefined' ? window.location.hash.slice(1) : '';
    const section = hash || searchParams.get('section') || '';
    if (!section) return;
    const el = document.getElementById(section);
    if (el) setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
  }, [searchParams]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!user || !token) {
    return (
      <div className="min-h-screen bg-[#050505] flex flex-col items-center justify-center p-4">
        <h1 className="text-xl text-white font-bold mb-4">Unauthenticated</h1>
        <Link href="/login" className="bg-blue-600 px-6 py-2 rounded-xl text-white font-semibold">
          Go to Login
        </Link>
      </div>
    );
  }

  const sectionClass =
    'mt-10 p-6 bg-zinc-950/80 border border-white/10 rounded-2xl space-y-4 scroll-mt-24';

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-300 p-6 selection:bg-blue-500/30">
      <div className="max-w-2xl mx-auto space-y-8 mt-12">
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

        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600/20 to-indigo-600/20 rounded-3xl blur opacity-75" />
          <div className="relative bg-zinc-900/90 border border-white/5 rounded-3xl p-10 backdrop-blur-xl">
            <div className="flex items-center gap-6 mb-10">
              <div className="w-24 h-24 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center text-white text-3xl font-bold shadow-2xl shadow-blue-500/20">
                {user.full_name?.charAt(0) || user.email?.charAt(0).toUpperCase()}
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Account &amp; settings</h1>
                <p className="text-zinc-500 flex items-center gap-1.5 mt-1">
                  <Shield className="w-4 h-4" />
                  Profile, security, API keys, and LLM
                </p>
              </div>
            </div>

            <div id="account" className={sectionClass}>
              <div className="flex items-center gap-2 text-white font-semibold">
                <User className="w-5 h-5 text-blue-400" />
                Profile
              </div>
              <p className="text-sm text-zinc-400 leading-relaxed">
                Your display name and sign-in email. Email is normalized to lowercase. Changing email re-issues your session token.
              </p>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Full name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Tenant</label>
                <div className="flex items-center gap-3 bg-black/40 border border-white/5 p-4 rounded-xl">
                  <Database className="w-5 h-5 text-indigo-400" />
                  <span className="text-white font-medium">{user.tenant_id}</span>
                </div>
                <p className="text-xs text-zinc-500">Tenant scope is fixed for this account. Contact an admin to move organizations.</p>
              </div>
              <button
                type="button"
                disabled={
                  profileSaving ||
                  !fullName.trim() ||
                  !email.trim() ||
                  (fullName.trim() === (user.full_name || '') && email.trim().toLowerCase() === (user.email || '').toLowerCase())
                }
                onClick={async () => {
                  setProfileSaving(true);
                  setProfileMessage(null);
                  const res = await updateProfile(token, { full_name: fullName.trim(), email: email.trim() });
                  setProfileSaving(false);
                  if (res.success) {
                    setProfileMessage('Saved.');
                    if (res.access_token) await updateSessionToken(res.access_token);
                    else await refreshProfile();
                  } else {
                    setProfileMessage(res.error || 'Save failed');
                  }
                }}
                className="px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                {profileSaving ? 'Saving…' : 'Save profile'}
              </button>
              {profileMessage && (
                <p className={`text-sm ${profileMessage === 'Saved.' ? 'text-emerald-400' : 'text-red-400'}`}>{profileMessage}</p>
              )}
            </div>

            <div id="security" className={sectionClass}>
              <div className="flex items-center gap-2 text-white font-semibold">
                <Lock className="w-5 h-5 text-amber-400" />
                Password
              </div>
              <p className="text-sm text-zinc-400 leading-relaxed">
                At least 12 characters, with at least one letter and one number. Passwords are hashed with bcrypt (cost 12) — never stored in plain text.
              </p>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Current password</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                  className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">New password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                  className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Confirm new password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
              <button
                type="button"
                disabled={
                  passwordSaving ||
                  !currentPassword ||
                  !newPassword ||
                  newPassword !== confirmPassword
                }
                onClick={async () => {
                  if (newPassword !== confirmPassword) {
                    setPasswordMessage('New passwords do not match.');
                    return;
                  }
                  setPasswordSaving(true);
                  setPasswordMessage(null);
                  const res = await changePassword(token, {
                    current_password: currentPassword,
                    new_password: newPassword,
                  });
                  setPasswordSaving(false);
                  if (res.success) {
                    setPasswordMessage('Password updated.');
                    setCurrentPassword('');
                    setNewPassword('');
                    setConfirmPassword('');
                  } else {
                    setPasswordMessage(res.error || 'Update failed');
                  }
                }}
                className="px-6 py-3 rounded-xl bg-amber-600/90 text-white font-semibold text-sm hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                {passwordSaving ? 'Updating…' : 'Change password'}
              </button>
              {passwordMessage && (
                <p className={`text-sm ${passwordMessage === 'Password updated.' ? 'text-emerald-400' : 'text-red-400'}`}>{passwordMessage}</p>
              )}
            </div>

            <div id="integrations" className={sectionClass}>
              <div className="flex items-center gap-2 text-white font-semibold">
                <KeyRound className="w-5 h-5 text-emerald-400" />
                API keys
              </div>
              <p className="text-sm text-zinc-400 leading-relaxed">
                Keys are encrypted with Fernet (AES) before storage. Only new values you type are sent; leave blank to keep an existing key unchanged.
              </p>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">OpenAI API key</label>
                <input
                  type="password"
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  placeholder={hasOpenAiKey ? '•••••••• (enter only to replace)' : 'sk-...'}
                  className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none font-mono text-sm"
                />
                {!requiresOpenAiApiKey && (
                  <p className="text-xs text-zinc-500">
                    Optional with a local LLM — add one if you switch back to OpenAI cloud or use OpenAI-only features.
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Tavily search API key</label>
                <input
                  type="password"
                  value={tavilyKeyInput}
                  onChange={(e) => setTavilyKeyInput(e.target.value)}
                  placeholder={hasTavilyKey ? '•••••••• (enter only to replace)' : 'tvly-...'}
                  className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none font-mono text-sm"
                />
              </div>
              <button
                type="button"
                disabled={keysSaving || (!apiKeyInput.trim() && !tavilyKeyInput.trim())}
                onClick={async () => {
                  setKeysSaving(true);
                  setKeysMessage(null);
                  const kr = await updateApiKey(token, apiKeyInput.trim(), tavilyKeyInput.trim());
                  setKeysSaving(false);
                  if (!kr.success) {
                    setKeysMessage(kr.error || 'Save failed');
                    return;
                  }
                  setKeysMessage('Saved.');
                  setApiKeyInput('');
                  setTavilyKeyInput('');
                  const st = await fetchApiKeyStatus(token);
                  if (st.success) {
                    setHasOpenAiKey(st.hasKey);
                    setHasTavilyKey(st.hasTavilyKey || false);
                  }
                }}
                className="px-6 py-3 rounded-xl bg-emerald-600 text-white font-semibold text-sm hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                {keysSaving ? 'Saving…' : 'Save API keys'}
              </button>
              {keysMessage && (
                <p className={`text-sm ${keysMessage === 'Saved.' ? 'text-emerald-400' : 'text-red-400'}`}>{keysMessage}</p>
              )}
            </div>

            <div id="llm" className={sectionClass}>
              <div className="flex items-center gap-2 text-white font-semibold">
                <Cpu className="w-5 h-5 text-indigo-400" />
                LLM backend
              </div>
              <p className="text-sm text-zinc-400 leading-relaxed">
                OpenAI cloud or an OpenAI-compatible server (Ollama, LM Studio, vLLM) via a{' '}
                <code className="text-indigo-300">/v1</code> base URL.
              </p>
              <div className="space-y-3">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Provider</label>
                <select
                  value={llmProvider}
                  onChange={(e) => {
                    const p = e.target.value;
                    setLlmProvider(p);
                    if (p === OPENAI_COMPATIBLE) {
                      setLlmModel((m) => m || llmConfig?.default_compatible_model || 'llama3.2');
                      if (!openaiBaseUrl.trim() && llmConfig?.example_compatible_base_url) {
                        setOpenaiBaseUrl(llmConfig.example_compatible_base_url);
                      }
                    } else {
                      setLlmModel((m) => {
                        const allowed = llmConfig?.openai_models || [];
                        if (allowed.includes(m)) return m;
                        return llmConfig?.default_openai_model || 'gpt-4o';
                      });
                    }
                  }}
                  className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  disabled={!llmConfig}
                >
                  {(llmConfig?.providers || []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>
              {llmProvider === OPENAI_COMPATIBLE && (
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Base URL</label>
                  <input
                    type="url"
                    value={openaiBaseUrl}
                    onChange={(e) => setOpenaiBaseUrl(e.target.value)}
                    placeholder={llmConfig?.example_compatible_base_url || 'http://localhost:11434/v1'}
                    className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none font-mono text-sm"
                  />
                  <p className="text-xs text-zinc-500 leading-relaxed">
                    {llmConfig?.compatible_base_url_hint}
                  </p>
                  <p className="text-xs text-zinc-500">
                    API on this machine:{' '}
                    <span className="text-zinc-400 font-mono">{llmConfig?.example_compatible_base_url}</span>
                    {llmConfig?.example_compatible_base_url_docker && (
                      <>
                        <br />
                        API in Docker, Ollama on host:{' '}
                        <span className="text-zinc-400 font-mono">{llmConfig.example_compatible_base_url_docker}</span>
                      </>
                    )}
                  </p>
                </div>
              )}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest ml-1">Model</label>
                {llmProvider === OPENAI_COMPATIBLE ? (
                  <>
                    <datalist id="compatible-llm-model-history">
                      {modelHistory.map((m) => (
                        <option key={m} value={m} />
                      ))}
                    </datalist>
                    <input
                      type="text"
                      list="compatible-llm-model-history"
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      placeholder={llmConfig?.default_compatible_model || 'e.g. llama3:8b'}
                      className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none font-mono text-sm"
                    />
                    {modelHistory.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600 w-full">Recent</span>
                        {modelHistory.slice(0, 10).map((m) => (
                          <button
                            key={m}
                            type="button"
                            onClick={() => setLlmModel(m)}
                            className="text-xs px-2.5 py-1 rounded-lg bg-zinc-800 border border-white/10 text-zinc-300 hover:border-indigo-500/50 hover:text-white transition"
                          >
                            {m}
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <select
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      className="w-full bg-black/50 border border-white/10 text-white rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                      disabled={!llmConfig?.openai_models?.length}
                    >
                      {(llmConfig?.openai_models || [llmModel]).map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                    {(() => {
                      const allowed = llmConfig?.openai_models || [];
                      const recent = modelHistory.filter((m) => allowed.includes(m));
                      if (!recent.length) return null;
                      return (
                        <div className="flex flex-wrap gap-2 pt-1">
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600 w-full">Recent</span>
                          {recent.slice(0, 8).map((m) => (
                            <button
                              key={m}
                              type="button"
                              onClick={() => setLlmModel(m)}
                              className="text-xs px-2.5 py-1 rounded-lg bg-zinc-800 border border-white/10 text-zinc-300 hover:border-indigo-500/50 hover:text-white transition"
                            >
                              {m}
                            </button>
                          ))}
                        </div>
                      );
                    })()}
                  </>
                )}
              </div>
              <button
                type="button"
                disabled={
                  llmSaving ||
                  !token ||
                  (llmProvider === user?.llm_provider &&
                    openaiBaseUrl.trim() === (user?.openai_base_url || '').trim() &&
                    llmModel.trim() === (user?.llm_model || '').trim())
                }
                onClick={async () => {
                  setLlmSaving(true);
                  setLlmMessage(null);
                  const res = await updateLlmSettings(token, {
                    llm_provider: llmProvider,
                    llm_model: llmModel.trim(),
                    openai_base_url: llmProvider === OPENAI_COMPATIBLE ? openaiBaseUrl.trim() : undefined,
                  });
                  setLlmSaving(false);
                  if (res.success) {
                    setLlmMessage('Saved.');
                    rememberLlmModel(llmModel.trim());
                    setModelHistory(getLlmModelHistory());
                    await refreshProfile();
                  } else {
                    setLlmMessage(res.error || 'Save failed');
                  }
                }}
                className="px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                {llmSaving ? 'Saving…' : 'Save LLM settings'}
              </button>
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

export default function ProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#050505] flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
        </div>
      }
    >
      <ProfileContent />
    </Suspense>
  );
}
