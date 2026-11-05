import generated from '../../../backend/tests/fixtures/branching_story.json';
import type { Story, StoryJob } from '../lib/api';

export const story: Story = {
  id: 7,
  title: generated.title,
  created_at: '2026-11-05T10:00:00Z',
  session_id: 'test-session',
  root_node: generated.nodes[0],
  all_nodes: Object.fromEntries(generated.nodes.map(node => [String(node.id), node])),
};
export const job: StoryJob = {
  job_id: 'test-job', status: 'pending', story_id: null,
  created_at: '2026-11-05T10:00:00Z', completed_at: null, error: null,
};
export function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
}
