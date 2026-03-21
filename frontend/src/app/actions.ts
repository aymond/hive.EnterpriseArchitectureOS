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
    return { success: true, hasKey: data.has_openai_key, hasTavilyKey: data.has_tavily_key };
  } catch (error: any) {
    return { success: false, error: error.message };
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
