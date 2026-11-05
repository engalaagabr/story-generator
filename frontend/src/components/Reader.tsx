import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, BookOpen, Check, Flag, GitBranch, RotateCcw, Share2, Sparkles } from 'lucide-react';
import { api, errorMessage, type Story } from '../lib/api';
import { remember, savePath, storyPath } from '../lib/storage';
import { BackLink, ErrorPanel, LoadingStory } from './Shared';

export function Reader({ id }: { id: number }) {
  const [story, setStory] = useState<Story | null>(null);
  const [path, setPath] = useState<number[]>([]);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [shareMessage, setShareMessage] = useState('');
  const contentHeading = useRef<HTMLHeadingElement>(null);
  const shareTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    const controller = new AbortController();
    api.story(id, controller.signal).then(result => {
      if (controller.signal.aborted) return;
      if (!result.root_node || !result.all_nodes?.[String(result.root_node.id)]) throw new Error('This story is missing its first chapter.');
      setStory(result); setPath(storyPath(result)); remember(result);
    }).catch(err => { if (!controller.signal.aborted) setError(errorMessage(err)); });
    return () => controller.abort();
  }, [id, attempt]);
  useEffect(() => { if (story && path.length) savePath(story.id, path); }, [path, story]);
  useEffect(() => { if (path.length > 0) contentHeading.current?.focus({ preventScroll: true }); }, [path]);
  useEffect(() => () => window.clearTimeout(shareTimer.current), []);

  if (error) return <div className="page-section"><BackLink /><ErrorPanel message={error} retry={() => { setError(''); setAttempt(value => value + 1); }} /></div>;
  if (!story || !path.length) return <LoadingStory />;
  const node = story.all_nodes[String(path[path.length - 1])];
  if (!node) return <div className="page-section"><BackLink /><ErrorPanel message="This story path could not be found." retry={() => setPath([story.root_node.id])} /></div>;
  const ending = node.is_ending;
  const winning = ending && node.is_winning_ending;
  const endingCount = Object.values(story.all_nodes).filter(item => item.is_ending).length;

  async function share() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShareMessage('Story link copied');
    } catch { setShareMessage('Copy this page’s address to share your story.'); }
    window.clearTimeout(shareTimer.current);
    shareTimer.current = window.setTimeout(() => setShareMessage(''), 5000);
  }

  function choose(target: number | null) {
    if (target === null || !story?.all_nodes[String(target)]) return;
    setPath(previous => {
      const current = story.all_nodes[String(previous[previous.length - 1])];
      if (current.is_ending || !current.options.some(option => option.node_id === target)) return previous;
      return [...previous, target];
    });
  }

  return <section className="reader-page"><div className="reader-toolbar"><BackLink /><div className="share-group"><span role="status">{shareMessage}</span><button className="secondary-button" onClick={share}><Share2 size={15} /> Share story</button></div></div>
    <div className="reader-title"><span className="eyebrow"><BookOpen size={14} /> YOUR ADVENTURE</span><h1 dir="auto">{story.title}</h1><p>{endingCount} possible endings. This path is yours.</p></div>
    <div className="reader-grid">
      <article className={`story-page ${ending ? winning ? 'winning-page' : 'ending-page' : ''}`}>
        <div className="chapter-marker"><span>{ending ? <Flag size={18} /> : <FeatherMark />}</span><span>{ending ? 'THE END OF THIS PATH' : `CHAPTER ${String(path.length).padStart(2, '0')}`}</span><span className="chapter-line" /></div>
        <h2 className="reader-chapter-title" ref={contentHeading} tabIndex={-1}>{ending ? winning ? 'A little courage. A wonderful ending.' : 'Every ending holds a new beginning.' : path.length === 1 ? 'And so, your story begins.' : 'The story unfolds.'}</h2>
        <div className="story-content" dir="auto">{node.content.split(/\n+/).filter(Boolean).map((paragraph, index) => <p key={`${node.id}-${index}`}>{paragraph}</p>)}</div>
        {ending ? <div className="ending-actions"><div className={`ending-label ${winning ? 'success' : 'bittersweet'}`}>{winning ? <Sparkles size={17} /> : <Flag size={17} />}{winning ? 'You found a winning ending' : 'This path has come to an end'}</div><p>There’s more to this world. What might a different choice reveal?</p><button className="primary-button" onClick={() => setPath([story.root_node.id])}><RotateCcw size={17} /> Explore another path</button></div>
          : <div className="choices"><p className="eyebrow">WHAT WILL YOU DO?</p>{node.options.map((option, index) => {
            const valid = option.node_id !== null && !!story.all_nodes[String(option.node_id)];
            return <button key={`${node.id}-${index}`} className="choice-button" disabled={!valid} onClick={() => choose(option.node_id)}><span className="choice-number">{String(index + 1).padStart(2, '0')}</span><span dir="auto">{option.text}</span><ArrowRight size={18} /></button>;
          })}{node.options.some(option => option.node_id === null || !story.all_nodes[String(option.node_id)]) && <ErrorPanel message="One of this story’s paths is missing. Choose another option or restart the story." />}</div>}
        {path.length > 1 && <button className="back-choice text-button" onClick={() => setPath(previous => previous.slice(0, -1))}><ArrowLeft size={15} /> Back one choice</button>}
      </article>
      <aside className="journey-panel"><div className="aside-heading"><span className="eyebrow">YOUR JOURNEY</span><GitBranch size={18} /></div><h2>A path of your own.</h2><p>Every choice brought you here.</p><ol className="journey-list">{path.map((nodeId, index) => <li key={`${nodeId}-${index}`} className={index === path.length - 1 ? 'active' : ''}><button onClick={() => setPath(path.slice(0, index + 1))} aria-current={index === path.length - 1 ? 'step' : undefined}><span className="journey-dot">{index === path.length - 1 ? index + 1 : <Check size={12} />}</span><span><strong>{index === 0 ? 'The beginning' : story.all_nodes[String(nodeId)].is_ending ? 'Your ending' : `Chapter ${index + 1}`}</strong><small dir="auto">{index === 0 ? 'A world of possibilities' : story.all_nodes[String(path[index - 1])].options.find(option => option.node_id === nodeId)?.text}</small></span></button></li>)}</ol><div className="journey-note"><BookOpen size={20} /><p>Your place is saved in this browser.<br />Come back whenever curiosity calls.</p></div><a className="text-button" href="#/">Dream up a new story <ArrowRight size={15} /></a></aside>
    </div>
  </section>;
}

function FeatherMark() { return <span aria-hidden="true">✧</span>; }
