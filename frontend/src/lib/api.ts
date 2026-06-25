const BASE = 'http://localhost:8000/api';

export interface SavedDraft {
	id: number;
	platform: string;
	post_type: string | null;
	post_types_json: string | null;
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
	mode: 'fast' | 'balanced' | 'polish' = 'balanced',
): Promise<{ drafts: Draft[]; run_id: string; post_types: Record<string, string>; router_reasoning: string }> {
	const res = await fetch(`${BASE}/generate`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			context,
			platforms,
			image_description: imageDescription ?? null,
			research,
			mode,
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

export async function regenerateDraft(
	id: number,
	platform: string,
	postType: string,
): Promise<SavedDraft> {
	const res = await fetch(`${BASE}/drafts/${id}/regenerate`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ platform, post_type: postType }),
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.detail ?? 'Regenerate failed');
	}
	const data = await res.json();
	return data.draft_output as SavedDraft;
}

export interface Revision {
	id: string;
	draft_id: number;
	revision_number: number;
	content: string;
	refinement_instruction: string | null;
	model_used: string;
	tier: number;
	is_current: boolean;
	created_at: string;
	tokens_in: number | null;
	tokens_out: number | null;
	cost_usd: number | null;
	latency_ms: number | null;
	adherence_passed: boolean | null;
}

export async function listRevisions(
	draftId: number,
): Promise<{ revisions: Revision[]; total: number; refinement_count: number; soft_limit: number }> {
	const res = await fetch(`${BASE}/drafts/${draftId}/revisions`);
	if (!res.ok) throw new Error('Failed to load revisions');
	return res.json();
}

export async function refineInstruction(
	draftId: number,
	instruction: string,
): Promise<{ revision: Revision; warning: string | null }> {
	const res = await fetch(`${BASE}/drafts/${draftId}/refine`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ instruction }),
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.detail ?? 'Refinement failed');
	}
	return res.json();
}

export async function revertRevision(
	draftId: number,
	revisionNumber: number,
): Promise<{ current_revision: Revision }> {
	const res = await fetch(`${BASE}/drafts/${draftId}/revert`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ revision_number: revisionNumber }),
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.detail ?? 'Revert failed');
	}
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

export interface Stats {
	totals: {
		calls: number;
		prompt_tokens: number;
		completion_tokens: number;
		total_tokens: number;
		cost_usd: number;
	};
	by_model: { model: string; calls: number; tokens: number; cost_usd: number }[];
	by_node: { node: string; calls: number; tokens: number; cost_usd: number }[];
	by_day: { date: string; calls: number; cost_usd: number; tokens: number }[];
	drafts: Record<string, number>;
}

export async function getStats(): Promise<Stats> {
	const res = await fetch(`${BASE}/stats`);
	if (!res.ok) throw new Error('Failed to load stats');
	return res.json();
}
