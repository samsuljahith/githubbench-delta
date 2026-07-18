export type Health = { service: string; status: 'up' | 'down' | 'degraded' };

export async function fetchHealth(baseUrl: string): Promise<Health[]> {
  const res = await fetch(`${baseUrl}/health`);
  if (!res.ok) throw new Error('health fetch failed');
  return res.json();
}
