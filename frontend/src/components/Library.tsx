import { ArrowRight, BookOpen, LibraryBig, Search, Sparkles } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { activeJob, library } from '../lib/storage';
import { navigate } from '../lib/navigation';

export function Library() {
  const stories = library();
  const pending = activeJob();
  const [storyId, setStoryId] = useState('');
  function openStory(event: FormEvent) {
    event.preventDefault();
    const id = Number(storyId);
    if (Number.isSafeInteger(id) && id > 0) navigate(`/stories/${id}`);
  }
  return <section className="library-page"><div className="library-heading"><div><span className="eyebrow">THE WORLDS YOU’VE OPENED</span><h1>Your little <em>library.</em></h1><p>Good stories are always worth coming back to.</p></div><a className="primary-button" href="#/"><Sparkles size={17} /> New story</a></div>
    {pending && <a className="resume-banner" href={`#/jobs/${pending}`}><Sparkles size={18} /><span>A new adventure is in progress. <strong>Check on your story.</strong></span><ArrowRight size={18} /></a>}
    <div className="library-controls"><span>{stories.length} {stories.length === 1 ? 'story' : 'stories'} saved in this browser</span><form onSubmit={openStory}><label className="sr-only" htmlFor="story-id">Open a story by ID</label><Search size={16} /><input id="story-id" type="number" min="1" step="1" required value={storyId} onChange={event => setStoryId(event.target.value)} placeholder="Open by story ID" /><button type="submit" aria-label="Open story" disabled={!storyId || Number(storyId) < 1}><ArrowRight size={18} /></button></form></div>
    {stories.length ? <div className="library-grid">{stories.map((story, index) => <a className={`library-card cover-${index % 3}`} href={`#/stories/${story.id}`} key={story.id}><div className="library-cover"><span className="cover-volume">FABLE / VOLUME {String(index + 1).padStart(2, '0')}</span><BookOpen size={48} strokeWidth={1} /><span className="cover-star">✧</span><h2 dir="auto">{story.title}</h2></div><div className="library-card-footer"><span>{story.nodeCount} story moments</span><span>Continue <ArrowRight size={16} /></span></div></a>)}</div>
      : <div className="empty-library"><span className="empty-icon"><LibraryBig size={40} strokeWidth={1.3} /></span><h2>Every library starts with one story.</h2><p>Your adventures will find a home here.<br />Let’s write the first one.</p><a className="primary-button" href="#/">Create my first story <ArrowRight size={17} /></a></div>}
    <p className="library-disclaimer">This library remembers stories you open on this device. Already have a story? Enter its ID above or open its link.</p>
  </section>;
}
