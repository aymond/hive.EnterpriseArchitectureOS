"use server"

export async function submitEARequest(query: string, authToken: string) {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  
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
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/proposals`, { 
      headers: {
        "Authorization": `Bearer ${authToken}`
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

export async function getProposalById(id: string, authToken: string) {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/proposals/${id}`, { 
      headers: {
        "Authorization": `Bearer ${authToken}`
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
