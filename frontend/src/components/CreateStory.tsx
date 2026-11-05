import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowRight, BookOpen, Compass, Feather, Leaf, Lightbulb, Orbit, Shuffle, Sparkles, WandSparkles } from 'lucide-react';
import { api, errorMessage } from '../lib/api';
import { activeJob, draft, draftLanguage, library, saveDraft, saveJob, saveLanguage } from '../lib/storage';
import { navigate } from '../lib/navigation';
import { ErrorPanel } from './Shared';

const seeds = [
  { name: 'Enchanted forest', genre: 'FANTASY', icon: Leaf, color: 'forest', text: 'Deep in an enchanted forest, you discover a door carved into an ancient tree. It only opens for someone who has lost something important.' },
  { name: 'Beyond the stars', genre: 'SCI-FI', icon: Orbit, color: 'space', text: 'You are the last awake passenger on a spaceship. An unfamiliar signal is coming from a planet that does not appear on any map.' },
  { name: 'The last train', genre: 'MYSTERY', icon: Compass, color: 'mystery', text: 'You board the last train home and find a letter addressed to you, dated tomorrow. At the next station, everyone else disappears.' },
];

function StoryIllustration() {
  return <div className="story-illustration" aria-hidden="true">
    <div className="illustration-orbit orbit-one" /><div className="illustration-orbit orbit-two" />
    <span className="floating-star star-one">✧</span><span className="floating-star star-two">✳</span>
    <div className="illustration-tag tag-top"><span /> A world of your own</div>
    <div className="book-stack book-back" /><div className="book-stack book-middle" />
    <div className="book-cover"><span className="book-edition">THE UNWRITTEN COLLECTION</span><div className="book-frame"><span>What</span><em>if?</em><Sparkles size={27} strokeWidth={1} /></div><span className="book-author">AN ADVENTURE BY YOU</span></div>
    <div className="illustration-tag tag-bottom"><Feather size={15} /> Every choice is a new chapter.</div>
    <span className="illustration-caption">YOUR IMAGINATION. YOUR WAY.</span>
  </div>;
}

export function CreateStory() {
  const [theme, setTheme] = useState(draft);
  const [language, setLanguage] = useState(draftLanguage);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const textarea = useRef<HTMLTextAreaElement>(null);
  const request = useRef<AbortController | null>(null);
  const lock = useRef(false);
  const recent = library().slice(0, 3);
  const pendingJob = activeJob();

  useEffect(() => () => request.current?.abort(), []);
  function updateTheme(value: string) { setTheme(value); saveDraft(value); setError(''); }
  function useSeed(text: string) { updateTheme(text); textarea.current?.focus(); }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!theme.trim() || lock.current) return;
    lock.current = true;
    setSubmitting(true); setError('');
    const controller = new AbortController();
    request.current = controller;
    try {
      const job = await api.create(`${theme.trim()}\n\nWrite the story, its title, and all choices in ${language}.`, controller.signal);
      saveJob(job.job_id);
      navigate(`/jobs/${job.job_id}`);
    } catch (err) {
      if (!controller.signal.aborted) setError(errorMessage(err));
    } finally {
      lock.current = false;
      if (!controller.signal.aborted) setSubmitting(false);
    }
  }

  return <>
    <section className="hero">
      <div className="hero-copy"><div className="eyebrow"><span className="little-line" /> A LITTLE IDEA. A WHOLE ADVENTURE.</div>
        <h1>It all starts<br />with a <em>what if.</em><span className="title-spark">✧</span></h1>
        <p>Dream up a world. Follow your curiosity.<br className="desktop-break" /> Create a story where <strong>your choices</strong> write the ending.</p>
        <div className="hero-note"><span className="tiny-book"><BookOpen size={16} /></span> One prompt. Many paths. Entirely yours.</div>
      </div>
      <StoryIllustration />
    </section>

    {pendingJob && <a className="resume-banner" href={`#/jobs/${pendingJob}`}><Sparkles size={18} /><span>You have a story in progress. <strong>Pick up where you left off.</strong></span><ArrowRight size={18} /></a>}

    <section className="studio-grid" aria-label="Story studio">
      <form className="composer" onSubmit={submit} aria-busy={submitting}>
        <div className="card-heading"><span className="section-icon"><Feather size={21} /></span><div><h2>Set the scene</h2><p>Every great story begins with a little possibility.</p></div><span className="step-label">01 / CREATE</span></div>
        <label className="field-label" htmlFor="theme">What’s your story about?</label>
        <div className="textarea-wrap"><textarea ref={textarea} id="theme" dir="auto" maxLength={1000} required value={theme} disabled={submitting} onChange={event => updateTheme(event.target.value)} placeholder="What if you discovered a little bookshop that only appears on rainy days…" aria-describedby="theme-hint" />
          <span className="character-count">{theme.length} / 1,000</span>
        </div>
        <div className="field-help" id="theme-hint"><Lightbulb size={14} /> A place, a character, a curious situation. Let your imagination wander.</div>
        <div className="composer-options"><label htmlFor="language">Story language <select id="language" value={language} onChange={event => { setLanguage(event.target.value); saveLanguage(event.target.value); }} disabled={submitting}><option>English</option><option value="Arabic">العربية</option></select></label>
          <button className="text-button" type="button" disabled={submitting} onClick={() => useSeed(seeds[Math.floor(Math.random() * seeds.length)].text)}><Shuffle size={15} /> Surprise me</button></div>
        {error && <ErrorPanel message={error} />}
        <button className="primary-button create-button" type="submit" disabled={!theme.trim() || submitting}><WandSparkles size={19} />{submitting ? 'Starting your story…' : 'Bring my story to life'}<ArrowRight size={18} /></button>
        <p className="composer-footnote">Made with a little AI and a lot of your imagination.</p>
      </form>

      <aside className="inspiration"><div className="aside-heading"><span className="eyebrow">A SPARK OF INSPIRATION</span><Sparkles size={18} /></div><h2>Not sure where to begin?</h2><p>Borrow a little spark. Make it your own.</p>
        <div className="seed-list">{seeds.map(seed => <button className={`seed-card ${seed.color}`} key={seed.name} onClick={() => useSeed(seed.text)} disabled={submitting}><span className="seed-icon"><seed.icon size={23} strokeWidth={1.5} /></span><span><small>{seed.genre}</small><strong>{seed.name}</strong></span><ArrowRight size={17} /></button>)}</div>
        <div className="inspiration-footer"><span>✧</span><p>There’s no wrong beginning.<br />Only a story waiting to be told.</p></div>
      </aside>
    </section>

    <section className="how-it-works" aria-label="How it works"><div className="how-intro"><span className="eyebrow">A LITTLE MAGIC, THREE STEPS</span><h2>From a spark to a story.</h2></div>
      {[['01', 'Imagine a world', 'Give your story a starting point.'], ['02', 'Choose your path', 'Decide what happens next.'], ['03', 'Find your ending', 'Then go back and try another.']].map(([number, title, text]) => <div className="how-step" key={number}><span>{number}</span><div><h3>{title}</h3><p>{text}</p></div></div>)}
    </section>

    {recent.length > 0 && <section className="recent-section"><div className="section-title"><h2>Your recent adventures</h2><a className="text-button" href="#/library">View library <ArrowRight size={16} /></a></div><div className="recent-grid">{recent.map(story => <a className="recent-card" key={story.id} href={`#/stories/${story.id}`}><BookOpen size={21} /><h3 dir="auto">{story.title}</h3><span>{story.nodeCount} story moments <ArrowRight size={16} /></span></a>)}</div></section>}
  </>;
}
