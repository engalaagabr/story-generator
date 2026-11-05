import { useEffect, useState } from 'react';
import { BookOpen, Feather, LibraryBig, Sparkles } from 'lucide-react';
import { CreateStory } from './components/CreateStory';
import { Generation } from './components/Generation';
import { Reader } from './components/Reader';
import { Library } from './components/Library';
import { ErrorPanel } from './components/Shared';
import { api } from './lib/api';
import { useRoute } from './lib/navigation';

function ServiceStatus() {
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  useEffect(() => {
    const controller = new AbortController();
    const check = () => api.health(controller.signal)
      .then(result => { if (!controller.signal.aborted) setStatus(result.status === 'ok' && result.database === 'ok' ? 'online' : 'offline'); })
      .catch(() => { if (!controller.signal.aborted) setStatus('offline'); });
    void check();
    const interval = window.setInterval(check, 30_000);
    return () => { controller.abort(); window.clearInterval(interval); };
  }, []);
  return <div className={`service-status ${status}`} role="status"><span />{status === 'online' ? 'Ready for your imagination' : status === 'offline' ? 'Story service unavailable' : 'Connecting to the studio'}</div>;
}

export default function App() {
  const path = useRoute();
  const storyMatch = path.match(/^\/stories\/([1-9]\d*)$/);
  const jobMatch = path.match(/^\/jobs\/([a-zA-Z0-9-]+)$/);
  const isLibrary = path === '/library';
  useEffect(() => {
    document.title = `${isLibrary ? 'Your library' : storyMatch ? 'Your adventure' : jobMatch ? 'Creating your story' : 'Story studio'} — Fable`;
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [path]); // Route changes reset the reading viewport, never individual choices.

  return <div className="app-shell"><a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); document.getElementById('main-content')?.focus(); }}>Skip to content</a>
    <header className="site-header"><div className="header-inner"><a href="#/" className="brand" aria-label="Fable home"><span className="brand-icon"><BookOpen size={22} strokeWidth={1.7} /></span><span>fable<span className="brand-period">.</span></span></a><nav aria-label="Main navigation"><a href="#/" className={!isLibrary ? 'active' : ''} aria-current={path === '/' ? 'page' : undefined}><Feather size={15} /> Story studio</a><a href="#/library" className={isLibrary ? 'active' : ''} aria-current={isLibrary ? 'page' : undefined}><LibraryBig size={15} /> My library</a></nav><span className="header-note"><Sparkles size={15} /> A story only you can tell.</span></div></header>
    <main id="main-content" className="main-container" tabIndex={-1}>{path === '/' ? <CreateStory /> : isLibrary ? <Library /> : jobMatch ? <Generation key={jobMatch[1]} id={jobMatch[1]} /> : storyMatch && Number.isSafeInteger(Number(storyMatch[1])) ? <Reader key={storyMatch[1]} id={Number(storyMatch[1])} /> : <div className="page-section"><ErrorPanel title="This page hasn’t been written." message="Follow a different path back to the story studio." /><a className="primary-button" href="#/">Back to the studio</a></div>}</main>
    <footer className="site-footer"><div><span className="footer-brand">fable.</span><span>For the wonderfully curious.</span></div><ServiceStatus /><span className="footer-ending">Your next chapter is up to you. <span>✧</span></span></footer>
  </div>;
}
