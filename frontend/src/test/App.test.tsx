import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import App from '../App';
import { Generation } from '../components/Generation';
import { job, json, story } from './fixtures';

function mockApi(handler: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    if (url === '/api/health') return json({ status: 'ok', database: 'ok' });
    return handler(url, init);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('Story studio integration', () => {
  it('creates an Arabic story, polls the job, reads choices, and restores reading progress', async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi(url => {
      if (url === '/api/story/create') return json(job);
      if (url === '/api/jobs/test-job') return json({ ...job, status: 'completed', story_id: 7 });
      if (url === '/api/story/7/complete') return json(story);
      throw new Error(`Unexpected request: ${url}`);
    });
    const view = render(<App />);
    expect(screen.getByRole('button', { name: /bring my story to life/i })).toBeDisabled();
    await user.type(screen.getByLabelText('What’s your story about?'), 'A secret space station');
    await user.selectOptions(screen.getByLabelText('Story language'), 'Arabic');
    await user.click(screen.getByRole('button', { name: /bring my story to life/i }));
    expect(await screen.findByRole('heading', { name: story.title })).toBeInTheDocument();
    const create = fetchMock.mock.calls.find(([url]) => url === '/api/story/create');
    expect(create?.[1]?.credentials).toBe('include');
    expect(JSON.parse(String(create?.[1]?.body)).theme).toContain('in Arabic');
    expect(JSON.parse(String(create?.[1]?.body)).theme).toContain('A secret space station');
    await user.click(screen.getByRole('button', { name: /Dock at the station/ }));
    expect(screen.getByText('Inside, you find a damaged escape shuttle.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Repair the shuttle/ }));
    expect(screen.getByText('You found a winning ending')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('fable:v1:path:7')!)).toEqual([10, 20, 40]);
    view.unmount();
    render(<App />);
    expect(await screen.findByText('You found a winning ending')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Explore another path/ }));
    await user.click(screen.getByRole('button', { name: /Fly into the asteroid field/ }));
    expect(screen.getByText('This path has come to an end')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Back one choice/ }));
    expect(screen.getByText(story.root_node.content)).toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: /My library/ }));
    expect(await screen.findByRole('heading', { name: story.title })).toBeInTheDocument();
    expect(screen.getByText('1 story saved in this browser')).toBeInTheDocument();
  });

  it('keeps the draft and displays a failed generation without repeated create requests', async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi(url => {
      if (url === '/api/story/create') return json(job);
      if (url === '/api/jobs/test-job') return json({ ...job, status: 'failed', error: 'Gemini quota or rate limit exceeded (HTTP 429).' });
      throw new Error(`Unexpected request: ${url}`);
    });
    render(<App />);
    await user.click(screen.getByRole('button', { name: /Enchanted forest/ }));
    await user.selectOptions(screen.getByLabelText('Story language'), 'Arabic');
    const theme = (screen.getByLabelText('What’s your story about?') as HTMLTextAreaElement).value;
    await user.click(screen.getByRole('button', { name: /bring my story to life/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Gemini quota');
    await user.click(screen.getByRole('link', { name: /Return to your idea/ }));
    await waitFor(() => expect(screen.getByLabelText('What’s your story about?')).toHaveValue(theme));
    expect(screen.getByLabelText('Story language')).toHaveValue('Arabic');
    expect(fetchMock.mock.calls.filter(([url]) => url === '/api/story/create')).toHaveLength(1);
  });

  it('polls processing jobs and stops polling after unmount', async () => {
    vi.useFakeTimers();
    const fetchMock = mockApi(() => json({ ...job, status: 'processing' }));
    const view = render(<Generation id="test-job" />);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(screen.getByText(/Creating your story/)).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    view.unmount();
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('retries a failed poll on the same job without creating another story', async () => {
    let polls = 0;
    const fetchMock = mockApi(url => {
      if (url === '/api/jobs/test-job') {
        if (++polls === 1) throw new TypeError('Network unavailable');
        return json({ ...job, status: 'failed', error: 'Generation failed.' });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    history.replaceState(null, '', '/#/jobs/test-job');
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach');
    fireEvent.click(screen.getByRole('button', { name: /Try again/ }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Generation failed.'));
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/story/create')).toBe(false);
  });

  it('handles a missing story and an empty local library', async () => {
    mockApi(() => json({ detail: 'Story not found' }, 404));
    history.replaceState(null, '', '/#/stories/99');
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Story not found');
    fireEvent.click(screen.getByRole('link', { name: /My library/ }));
    expect(await screen.findByText('Every library starts with one story.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Open a story by ID'), { target: { value: '99' } });
    fireEvent.click(screen.getByRole('button', { name: 'Open story' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Story not found');
  });
});
