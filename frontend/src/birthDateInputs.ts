function isoDate(value: string): string {
  const parts = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
  if (!parts) return '';
  const [day, month, year] = parts.slice(1).map(Number);
  if (year < 1 || month < 1 || month > 12 || day < 1) return '';
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return '';
  return `${parts[3]}-${parts[2]}-${parts[1]}`;
}

export function enhanceBirthDateInputs(root: HTMLElement): () => void {
  const cleanups: (() => void)[] = [];
  root.querySelectorAll<HTMLInputElement>('input[data-birth-date]').forEach(input => {
    const control = input.closest('.birth-date-control');
    const calendar = control?.querySelector<HTMLInputElement>('.birth-date-calendar');
    const picker = control?.querySelector<HTMLButtonElement>('.birth-date-picker');
    if (!calendar || !picker) return;
    function sync() {
      // Eight digits can be entered on a phone's numeric keyboard.
      if (/^\d{8}$/.test(input.value)) input.value = `${input.value.slice(0, 2)}/${input.value.slice(2, 4)}/${input.value.slice(4)}`;
      const iso = isoDate(input.value);
      calendar!.value = iso;
      input.setCustomValidity(input.value && !iso ? 'Enter a valid date as DD/MM/YYYY, for example 04/09/1998.' : '');
    }
    function choose() { sync(); calendar!.showPicker(); }
    function selected() {
      if (!calendar!.value) return;
      const [year, month, day] = calendar!.value.split('-');
      input.value = `${day}/${month}/${year}`;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      input.focus();
    }
    picker.hidden = typeof calendar.showPicker !== 'function';
    input.addEventListener('input', sync);
    picker.addEventListener('click', choose);
    calendar.addEventListener('change', selected);
    sync();
    cleanups.push(() => {
      input.removeEventListener('input', sync);
      picker.removeEventListener('click', choose);
      calendar.removeEventListener('change', selected);
    });
  });
  return () => cleanups.forEach(cleanup => cleanup());
}
