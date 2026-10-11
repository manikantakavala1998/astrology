import { useEffect, useRef } from 'react';
import { enhanceBirthDateInputs } from './birthDateInputs';
import { enhanceBirthPlaceInputs } from './birthPlaceInputs';

interface Props { html: string; className?: string }

/** Only accepts autoescaped HTML from this application's own Jinja reports.
 * Keeping these reports intact preserves every calculation, source note,
 * table, held-chart notice, and native form during the UI migration.
 */
export function ServerReport({ html, className = '' }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const cleanupBirthDates = enhanceBirthDateInputs(node);
    const cleanupBirthPlaces = enhanceBirthPlaceInputs(node);
    node.querySelectorAll('.error').forEach((error) => error.setAttribute('role', 'alert'));

    node.querySelectorAll<HTMLTableElement>('table').forEach((table) => {
      if (table.parentElement?.classList.contains('table-scroll')) return;
      const wrapper = document.createElement('div');
      wrapper.className = 'table-scroll';
      wrapper.setAttribute('role', 'region');
      wrapper.setAttribute('aria-label', `${table.closest('.panel')?.querySelector('h2, h3')?.textContent?.trim() ?? 'Report'} table`);
      wrapper.tabIndex = 0;
      table.before(wrapper);
      wrapper.append(table);
    });

    // Preserve the native radio-backed report controls, while making their
    // visual tabs proper keyboard-accessible buttons.
    node.querySelectorAll<HTMLLabelElement>('label.subtab-label').forEach((label) => {
      const radio = node.querySelector<HTMLInputElement>(`#${label.htmlFor}`);
      if (!radio) return;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = label.className;
      button.innerHTML = label.innerHTML;
      button.dataset.radio = radio.id;
      button.id = `${radio.id}-control`;
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-selected', String(radio.checked));
      const panel = label.nextElementSibling as HTMLElement | null;
      if (panel?.classList.contains('subtab-panel')) {
        panel.id ||= `${radio.id}-content`;
        panel.setAttribute('role', 'tabpanel');
        panel.setAttribute('aria-labelledby', button.id);
        button.setAttribute('aria-controls', panel.id);
      }
      label.replaceWith(button);
    });

    function selectTab(button: HTMLButtonElement) {
      const radio = node!.querySelector<HTMLInputElement>(`#${button.dataset.radio}`);
      if (!radio) return;
      radio.checked = true;
      radio.dispatchEvent(new Event('change', { bubbles: true }));
      node!.querySelectorAll<HTMLButtonElement>('button[data-radio]').forEach((tab) => {
        const input = node!.querySelector<HTMLInputElement>(`#${tab.dataset.radio}`);
        tab.setAttribute('aria-selected', String(input?.checked ?? false));
      });
    }

    function click(event: MouseEvent) {
      const target = (event.target as HTMLElement).closest<HTMLButtonElement>('button[data-radio]');
      if (target && node!.contains(target)) selectTab(target);
    }

    function keydown(event: KeyboardEvent) {
      const target = (event.target as HTMLElement).closest<HTMLButtonElement>('button[data-radio]');
      if (!target || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      const radio = node!.querySelector<HTMLInputElement>(`#${target.dataset.radio}`);
      const tabs = Array.from(node!.querySelectorAll<HTMLButtonElement>('button[data-radio]')).filter((button) => {
        return node!.querySelector<HTMLInputElement>(`#${button.dataset.radio}`)?.name === radio?.name;
      });
      const index = tabs.indexOf(target);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
        : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      event.preventDefault();
      selectTab(tabs[next]);
      tabs[next].focus();
    }

    node.addEventListener('click', click);
    node.addEventListener('keydown', keydown);
    return () => {
      cleanupBirthDates();
      cleanupBirthPlaces();
      node.removeEventListener('click', click);
      node.removeEventListener('keydown', keydown);
    };
  }, [html]);

  return <div ref={ref} className={`server-report ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
}
