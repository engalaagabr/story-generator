import { useEffect, useState } from 'react';
import { ArrowRight, Check, Feather, GitBranch, LoaderCircle, Sparkles } from 'lucide-react';
import { api, errorMessage, type StoryJob } from '../lib/api';
import { clearJob } from '../lib/storage';
import { navigate } from '../lib/navigation';
import { BackLink, ErrorPanel } from './Shared';

export function Generation({ id }: { id: string }) {
  const [job, setJob] = useState<StoryJob | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const interval = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let timer: number | undefined;
    let polls = 0;
    async function poll() {
      try {
        const result = await api.job(id, controller.signal);
        if (controller.signal.aborted) return;
        setJob(result);
        if (result.status === 'completed') {
          clearJob(id);
          if (!result.story_id) throw new Error('Your story finished without a readable story ID. Please start a new story.');
          navigate(`/stories/${result.story_id}`, true);
        } else if (result.status === 'failed') {
          clearJob(id);
        } else if (result.status !== 'pending' && result.status !== 'processing') {
          throw new Error('The story service returned an unexpected job status.');
        } else if (++polls >= 150) {
          setError('This is taking longer than expected. Your job is still saved. Check again to see whether it has finished.');
        } else {
          timer = window.setTimeout(poll, 2000);
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(errorMessage(err));
      }
    }
    void poll();
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [id, attempt]);

  const failed = job?.status === 'failed';
  return <section className="generation-page"><BackLink />
    <div className="generation-card"><div className={`generation-symbol ${failed ? 'paused' : ''}`}><Feather size={38} strokeWidth={1.3} /><span>✧</span></div>
      <span className="eyebrow">{failed ? 'LET’S TURN A NEW PAGE' : 'YOUR IMAGINATION IS TAKING SHAPE'}</span>
      <h1>{failed ? 'This story needs a fresh start.' : 'A world is being written.'}</h1>
      <p className="generation-description">{failed ? 'Your idea is still here. You can return to the studio and give it another try.' : 'Characters are finding their voices. Paths are unfolding. Your next adventure is on its way.'}</p>
      {!failed && <ol className="generation-steps" aria-label="Generation progress">
        <li className="done"><Check size={18} /><div><strong>Your idea, received</strong><span>The beginning of something good.</span></div></li>
        <li className={job?.status === 'processing' ? 'current' : ''}>{job?.status === 'processing' ? <LoaderCircle className="spin" size={18} /> : <Feather size={18} />}<div><strong>Writing your world</strong><span>A story with different paths and endings.</span></div></li>
        <li><GitBranch size={18} /><div><strong>Your adventure awaits</strong><span>You’ll be the one making the choices.</span></div></li>
      </ol>}
      <div aria-live="polite">{failed ? <ErrorPanel title="We couldn’t finish this story." message={job.error || 'Generation failed. Please try another theme.'} />
        : error ? <ErrorPanel message={error} retry={() => { setError(''); setAttempt(value => value + 1); }} />
        : <p className="generation-status"><Sparkles size={15} />{job?.status === 'processing' ? 'Creating your story' : 'Waiting for the storyteller'}<span aria-hidden="true">· {elapsed}s elapsed</span></p>}</div>
      {failed ? <a href="#/" className="primary-button">Return to your idea <ArrowRight size={17} /></a> : <p className="small-muted">You can leave this page and resume from the studio.</p>}
    </div>
  </section>;
}
