const BASE = 'http://localhost:8000/api';

export interface SavedDraft {
	id: number;
	platform: string;
	content: string;
	context_input: string;
	status: string;
	total_cost_usd: number;
	created_at: string;
	scheduled_at: string | null;
}

export async function healthCheck(): Promise<{ status: string; service: string }> {
	const res = await fetch(`${BASE}/health`);
	if (!res.ok) throw new Error('Backend unreachable');
	return res.json();
}

export interface Draft {
	platform: string;
	content: string;
	model: string;
	prompt_tokens: number;
	completion_tokens: number;
	cost_usd: number;
}

export async function generate(
	context: string,
	platforms: string[],
	imageDescription?: string,
	research: 'auto' | 'on' | 'off' = 'auto',
): Promise<{ drafts: Draft[]; run_id: string }> {
	const res = await fetch(`${BASE}/generate`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			context,
			platforms,
			image_description: imageDescription ?? null,
			research,
		}),
	});
	if (!res.ok) throw new Error('Generate failed');
	return res.json();
}

export async function listDrafts(): Promise<SavedDraft[]> {
	const res = await fetch(`${BASE}/drafts`);
	if (!res.ok) throw new Error('Failed to load drafts');
	return res.json();
}

export async function scheduleDraft(id: number, scheduledAt: Date): Promise<void> {
	const res = await fetch(`${BASE}/drafts/${id}/schedule`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ scheduled_at: scheduledAt.toISOString() }),
	});
	if (!res.ok) throw new Error('Schedule failed');
}
