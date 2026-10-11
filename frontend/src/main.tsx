import { createRoot } from 'react-dom/client';
import App from './App';
import { readWorkspace } from './workspace';
import './styles.css';

const root = document.getElementById('astro-root');
if (root) {
  try {
    // Read the complete server-rendered workspace before React takes ownership.
    // If bootstrap fails, leave the working native HTML forms/reports in place.
    const initial = readWorkspace(document);
    createRoot(root).render(<App initial={initial} />);
  } catch (error) {
    console.error('Could not start the astrology UI.', error);
  }
}
