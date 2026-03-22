"use server"

export async function submitEARequest(query: string, authToken: string) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  
  try {
    const res = await fetch(`${backendUrl}/request?query=${encodeURIComponent(query)}`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${authToken}`
      },
      cache: 'no-store'
    });
    
    if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
    }
    
    const data = await res.json();
    return { success: true, data };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}

export async function fetchProposals(authToken: string) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/proposals`, { 
      headers: {
        "Authorization": `Bearer ${authToken}`
      },
      cache: 'no-store' 
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`${res.status}: ${body || res.statusText}`);
    }
    const data = await res.json();
    return { success: true, data };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}

export async function getProposalById(id: string, authToken: string) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/proposals/${id}`, { 
      headers: {
        "Authorization": `Bearer ${authToken}`
      },
      cache: 'no-store' 
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`${res.status}: ${body || res.statusText}`);
    }
    const data = await res.json();
    return { success: true, data };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}

export async function fetchApiKeyStatus(authToken: string) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/auth/api-keys/status`, { 
      headers: { "Authorization": `Bearer ${authToken}` },
      cache: 'no-store' 
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();
    return {
      success: true,
      hasKey: data.has_openai_key,
      hasTavilyKey: data.has_tavily_key,
      requiresOpenAiApiKey: data.requires_openai_api_key ?? true,
      llmProvider: data.llm_provider as string | undefined,
    };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}

export async function fetchLlmModels() {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/auth/llm-models`, { cache: "no-store" });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();
    return {
      success: true as const,
      models: data.models as string[],
      defaultModel: data.default as string,
    };
  } catch (error: any) {
    return { success: false as const, error: error.message };
  }
}

export async function updateLlmModel(authToken: string, llm_model: string) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/auth/llm-model`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${authToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ llm_model }),
    });
    if (!res.ok) {
      const errBody = await res.text().catch(() => "");
      throw new Error(errBody || `API error: ${res.status}`);
    }
    return { success: true as const };
  } catch (error: any) {
    return { success: false as const, error: error.message };
  }
}

export type LlmConfigResponse = {
  providers: { id: string; label: string }[];
  openai_models: string[];
  default_openai_model: string;
  default_compatible_model: string;
  example_compatible_base_url: string;
  example_compatible_base_url_docker?: string;
  compatible_base_url_hint?: string;
};

export async function fetchLlmConfig() {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/auth/llm-config`, { cache: "no-store" });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = (await res.json()) as LlmConfigResponse;
    return { success: true as const, config: data };
  } catch (error: any) {
    return { success: false as const, error: error.message };
  }
}

export async function updateLlmSettings(
  authToken: string,
  payload: { llm_provider: string; llm_model: string; openai_base_url?: string }
) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/auth/llm-settings`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${authToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errBody = await res.text().catch(() => "");
      throw new Error(errBody || `API error: ${res.status}`);
    }
    return { success: true as const };
  } catch (error: any) {
    return { success: false as const, error: error.message };
  }
}

export async function updateProfile(
  authToken: string,
  payload: { full_name: string; email: string }
) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/auth/profile`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${authToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || res.statusText);
      throw new Error(detail || `API error: ${res.status}`);
    }
    return {
      success: true as const,
      user: data.user,
      access_token: data.access_token as string | undefined,
    };
  } catch (error: any) {
    return { success: false as const, error: error.message };
  }
}

export async function changePassword(
  authToken: string,
  payload: { current_password: string; new_password: string }
) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/auth/password`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${authToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || res.statusText);
      throw new Error(detail || `API error: ${res.status}`);
    }
    return { success: true as const };
  } catch (error: any) {
    return { success: false as const, error: error.message };
  }
}

export type CapabilityDomainSummary = {
  name: string;
  slug: string;
  purpose: string;
  capability_count: number;
};

export async function fetchCapabilityDomains(authToken: string) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/capabilities/domains`, {
      headers: { Authorization: `Bearer ${authToken}` },
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`${res.status}: ${body || res.statusText}`);
    }
    const data = (await res.json()) as { domains: CapabilityDomainSummary[] };
    return { success: true as const, domains: data.domains };
  } catch (error: any) {
    return { success: false as const, error: error.message };
  }
}

export type CatalogCapability = {
  name: string;
  slug: string;
  description: string;
  parent_name: string | null;
  sources: string[];
};

export async function fetchCapabilitiesForDomain(domainSlug: string, authToken: string) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(
      `${backendUrl}/capabilities/domains/${encodeURIComponent(domainSlug)}`,
      {
        headers: { Authorization: `Bearer ${authToken}` },
        cache: "no-store",
      }
    );
    if (res.status === 404) {
      return { success: false as const, notFound: true as const, error: "Domain not found" };
    }
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`${res.status}: ${body || res.statusText}`);
    }
    const data = (await res.json()) as {
      domain: { name: string; slug: string; purpose: string };
      capabilities: CatalogCapability[];
    };
    return { success: true as const, data };
  } catch (error: any) {
    return { success: false as const, notFound: false as const, error: error.message };
  }
}

export async function fetchCapabilityDetail(
  domainSlug: string,
  capabilitySlug: string,
  authToken: string
) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(
      `${backendUrl}/capabilities/domains/${encodeURIComponent(domainSlug)}/capabilities/${encodeURIComponent(capabilitySlug)}`,
      {
        headers: { Authorization: `Bearer ${authToken}` },
        cache: "no-store",
      }
    );
    if (res.status === 404) {
      return { success: false as const, notFound: true as const, error: "Not found" };
    }
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`${res.status}: ${body || res.statusText}`);
    }
    const data = (await res.json()) as {
      domain: { name: string; slug: string; purpose: string };
      capability: {
        name: string;
        slug: string;
        description: string;
        parent_name: string | null;
        sources: string[];
      };
    };
    return { success: true as const, data };
  } catch (error: any) {
    return { success: false as const, notFound: false as const, error: error.message };
  }
}

export async function updateApiKey(authToken: string, apiKey: string, tavilyKey: string) {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
  try {
    const payload: any = {};
    if (apiKey) payload.openai_api_key = apiKey;
    if (tavilyKey) payload.tavily_api_key = tavilyKey;
    
    const res = await fetch(`${backendUrl}/auth/api-keys`, { 
      method: "PUT",
      headers: { 
        "Authorization": `Bearer ${authToken}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return { success: true };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}
