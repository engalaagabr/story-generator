export interface StoryOption { text: string; node_id: number | null }
export interface StoryNode {
  id: number;
  content: string;
  is_ending: boolean;
  is_winning_ending: boolean;
  options: StoryOption[];
}
export interface Story {
  id: number;
  title: string;
  created_at: string;
  session_id: string | null;
  root_node: StoryNode;
  all_nodes: Record<string, StoryNode>;
}
export interface StoryJob {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  story_id: number | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  init.signal?.addEventListener('abort', abort, { once: true });
  if (init.signal?.aborted) controller.abort();
  const timeout = window.setTimeout(abort, 20_000);
  try {
    const response = await fetch(`/api${path}`, {
      ...init,
      credentials: 'include',
      signal: controller.signal,
      headers: { Accept: 'application/json', ...init.headers },
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = typeof data?.detail === 'string' ? data.detail : null;
      throw new Error(detail || (response.status >= 500
        ? 'The story service is unavailable. Please try again in a moment.'
        : `The request could not be completed (${response.status}).`));
    }
    if (data === null) throw new Error('The story service returned an unreadable response. Please retry.');
    return data as T;
  } catch (error) {
    if (init.signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    if (controller.signal.aborted) throw new Error('The connection timed out. Please try again.');
    if (error instanceof TypeError) throw new Error('Unable to reach the story service. Check your connection and try again.');
    throw error;
  } finally {
    window.clearTimeout(timeout);
    init.signal?.removeEventListener('abort', abort);
  }
}

export const api = {
  health: (signal?: AbortSignal) => request<{ status: string; database: string }>('/health', { signal }),
  create: (theme: string, signal?: AbortSignal) => request<StoryJob>('/story/create', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ theme }), signal,
  }),
  job: (id: string, signal?: AbortSignal) => request<StoryJob>(`/jobs/${encodeURIComponent(id)}`, { signal }),
  story: (id: number, signal?: AbortSignal) => request<Story>(`/story/${id}/complete`, { signal }),
};

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}
