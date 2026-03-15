"use server"

export async function submitEARequest(query: string) {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  
  try {
    const res = await fetch(`${backendUrl}/request?query=${encodeURIComponent(query)}`, {
      method: "POST",
      headers: {
        "X-Tenant-ID": "default-tenant"
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
export async function fetchProposals() {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  try {
    console.log(`[ACTION] Fetching proposals from ${backendUrl}...`);
    const res = await fetch(`${backendUrl}/proposals`, { 
      headers: {
        "X-Tenant-ID": "default-tenant"
      },
      cache: 'no-store' 
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();
    console.log(`[ACTION] Successfully fetched ${Array.isArray(data) ? data.length : 'invalid'} proposals.`);
    return { success: true, data };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}

export async function getProposalById(id: string) {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/proposals/${id}`, { 
      headers: {
        "X-Tenant-ID": "default-tenant"
      },
      cache: 'no-store' 
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();
    return { success: true, data };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}
