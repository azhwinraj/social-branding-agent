const BASE = 'http://localhost:8000/api';

export async function healthCheck(): Promise<{ status: string; service: string }> {
	const res = await fetch(`${BASE}/health`);
	if (!res.ok) throw new Error('Backend unreachable');
	return res.json();
}

export async function generate(context: string, platforms: string[]): Promise<{ drafts: unknown[]; run_id: string }> {
	const res = await fetch(`${BASE}/generate`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ context, platforms }),
	});
	if (!res.ok) throw new Error('Generate failed');
	return res.json();
}
