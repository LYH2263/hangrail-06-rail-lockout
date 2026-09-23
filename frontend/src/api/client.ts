export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let text = await res.text();
    try {
      const data = JSON.parse(text);
      if (typeof data.detail === "string") text = data.detail;
      else if (Array.isArray(data.detail)) text = JSON.stringify(data.detail);
    } catch {
      // 非 JSON 响应时保留原文
    }
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
