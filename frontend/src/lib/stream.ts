export async function submitEARequestStream(
  query: string, 
  authToken: string, 
  onEvent: (data: any) => void,
  onComplete: (data: any) => void,
  onError: (error: string) => void
) {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || (process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:8000');
  
  try {
    const res = await fetch(`${backendUrl}/stream_request?query=${encodeURIComponent(query)}`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${authToken}`,
        "Accept": "text/event-stream"
      }
    });

    if (!res.ok) {
      const err = await res.text().catch(() => "Unknown error");
      throw new Error(`API error ${res.status}: ${err}`);
    }

    if (!res.body) {
      throw new Error("No response body");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      
      buffer = lines.pop() || "";
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const dataStr = line.slice(6);
            const data = JSON.parse(dataStr);
            if (data.status === 'final') {
              onComplete(data.data);
            } else {
              onEvent(data);
            }
          } catch (e) {
            console.error("Failed to parse SSE line:", line);
          }
        }
      }
    }
  } catch (err: any) {
    onError(err.message || "Failed to connect to stream");
  }
}
