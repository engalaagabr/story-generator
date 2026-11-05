import { AlertCircle, ArrowLeft, BookOpen, RefreshCw } from 'lucide-react';

export function ErrorPanel({ message, retry, title = 'A small plot twist.' }: {
  message: string; retry?: () => void; title?: string;
}) {
  return <div className="error-panel" role="alert">
    <AlertCircle size={21} aria-hidden="true" />
    <div><strong>{title}</strong><p>{message}</p>
      {retry && <button className="text-button" onClick={retry}><RefreshCw size={15} /> Try again</button>}
    </div>
  </div>;
}

export function LoadingStory() {
  return <div className="loading-story" role="status"><BookOpen className="gently-pulse" size={36} />
    <h1>Opening your story…</h1><p>A new world is just a page away.</p>
  </div>;
}

export function BackLink() {
  return <a className="back-link" href="#/"><ArrowLeft size={16} /> Back to the studio</a>;
}
