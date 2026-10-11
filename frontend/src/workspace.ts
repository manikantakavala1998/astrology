import type { Bootstrap, Section, Workspace } from './types';

export const navigationGroups: { id: Section['group']; label: string | null }[] = [
  { id: 'chart', label: 'Parasara Method' },
  { id: 'bhrigu', label: 'Bhrigu Method' },
  { id: 'brihat', label: 'Varahamihira Method' },
  { id: 'jaimini', label: 'Jaimini Method' },
  { id: 'analysis', label: 'Analysis' },
  { id: 'more', label: 'More' },
];

export const sections: Section[] = [
  { id: 'chart', label: 'Birth chart', emoji: '🔮', group: 'chart', title: 'Your cosmic blueprint.', description: 'Your sky at the moment of birth.' },
  { id: 'panchanga', label: 'Panchanga', emoji: '📅', group: 'chart', title: 'The five parts of your birth day.', description: 'Tithi, vara, nakshatra, yoga, and karana.' },
  { id: 'aspects', label: 'Aspects', emoji: '🔭', group: 'chart', title: 'Planetary Aspects', description: 'Vedic sign-based aspects and Western angular connections between your planets.' },
  { id: 'balas', label: 'Strengths', emoji: '⚖️', group: 'chart', title: 'Every strength, clearly explained.', description: 'Separate strength views, full names and calculation breakdowns.' },
  { id: 'dasha', label: 'Dasha', emoji: '⏳', group: 'chart', title: 'The rhythm of your life.', description: 'Explore every Vimshottari mahadasha and its sub-periods.' },
  { id: 'divisional', label: 'Divisional charts', emoji: '📁', group: 'chart', title: 'A deeper view of your chart.', description: 'Bhava Chalit and the complete divisional chart collection.' },
  { id: 'ashtakavarga', label: 'Ashtakavarga', emoji: '📊', group: 'chart', title: 'Strength across your sky.', description: 'Samudaya, planetary bindus, and Bhava Ashtakavarga.' },
  { id: 'laghu-parashari', label: 'Laghu Parashari', emoji: '📖', group: 'chart', title: 'Understand your planets.', description: 'Ascendant-based roles, yoga conditions and Vimshottari period rules from your birth details.' },
  { id: 'bcp', label: 'Bhrigu Chakra Paddhati', emoji: '🔮', group: 'bhrigu', title: 'Your Bhrigu Chakra Paddhati.', description: 'Explore the activated house for each year of life and its cycle ruler.' },
  { id: 'bsp', label: 'Bhrigu Sarala Paddhati', emoji: '📜', group: 'bhrigu', title: 'Your Bhrigu Sarala Paddhati.', description: 'Age-based planetary rules and permanent house indications from your birth chart.' },
  { id: 'padma', label: 'Padma Chakra Paddhati', emoji: '🌷', group: 'bhrigu', title: 'Your Padma Chakra Paddhati.', description: 'The complete year-by-year Padma Chakra Paddhati.' },
  { id: 'brihat-jataka', label: 'Brihat Jataka', emoji: '📚', group: 'brihat', title: 'Varahamihira’s Brihat Jataka.', description: 'Predictions, dasha periods, strengths, yogas and Ashtakavarga calculated from your birth details.' },
  { id: 'jaimini', label: 'Jaimini North', emoji: '🪐', group: 'jaimini', title: 'Your Jaimini North chart.', description: 'Karakas, sign aspects, Arudha padas and dasha periods from your birth details.' },
  { id: 'jaimini2', label: 'Jaimini South', emoji: '📖', group: 'jaimini', title: 'Your Jaimini South chart.', description: 'Sampath Kumar’s book conventions, calculations and predictions from your birth details.' },
  { id: 'shani', label: 'Shani', emoji: '⚽', group: 'analysis', title: 'Your Saturn story.', description: 'Natal afflictions and the full Saturn transit timeline.' },
  { id: 'dosha', label: 'Doshas', emoji: '🐊', group: 'analysis', title: 'Understand the finer details.', description: 'Kalasarpa, Kuja, Guru Chandala, and Punarphoo analyses.' },
  { id: 'compat', label: 'Compatibility', emoji: '💜', group: 'analysis', title: 'Two charts, one connection.', description: 'Ashtakoot Guna Milan and Mangal Dosha matching.' },
  { id: 'classic-predictions', label: 'Classic predictions', emoji: '📜', group: 'more', title: 'Classic predictions.', description: 'A place for future classical readings.', pending: true },
  { id: 'yogas', label: 'Yogas', emoji: '✨', group: 'more', title: 'Planetary combinations.', description: 'Yogas will appear here when available.', pending: true },
  { id: 'tools', label: 'Tools', emoji: '🔧', group: 'more', title: 'Your astrology toolkit.', description: 'A place for future tools.', pending: true },
];

export function readWorkspace(doc: Document): Workspace {
  const root = doc.getElementById('astro-root');
  const bootstrap = doc.getElementById('astro-state');
  if (!root || !bootstrap?.textContent) throw new Error('The chart response could not be loaded. Please try again.');
  const state = JSON.parse(bootstrap.textContent) as Bootstrap;
  const page = root.querySelector('.page');
  const sections: Record<string, string> = {};
  root.querySelectorAll<HTMLElement>('.tabs-wrapper > .tab-panel').forEach((panel) => {
    sections[panel.id.replace('panel-', '')] = panel.innerHTML;
  });
  return {
    state,
    sections,
    formHtml: state.page === 'workspace' && page
      ? Array.from(page.children).filter((node) => !node.classList.contains('tabs-wrapper')).map((node) => node.outerHTML).join('')
      : '',
    detailHtml: state.page === 'dasha' ? page?.innerHTML ?? '' : '',
  };
}

// Dates from the engine are birth-place local datetimes, not UTC instants.
// Format the date portion directly so the browser's timezone cannot shift it.
export function formatDate(value: string, short = false): string {
  const [year, month, day] = value.slice(0, 10).split('-').map(Number);
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: short ? undefined : 'numeric', timeZone: 'UTC',
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

export function formatTime(value: string): string {
  const [hour, minute] = value.split(':').map(Number);
  return `${String(hour % 12 || 12).padStart(2, '0')}:${String(minute).padStart(2, '0')} ${hour < 12 ? 'AM' : 'PM'}`;
}

export function formatOffset(hours: number): string {
  const minutes = Math.round(Math.abs(hours) * 60);
  return `UTC ${hours < 0 ? '−' : '+'}${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
}
