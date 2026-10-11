/** Enhance the native birthplace fields without changing submitted values. */
export function enhanceBirthPlaceInputs(root: HTMLElement): () => void {
  const cleanups: (() => void)[] = [];
  root.querySelectorAll<HTMLElement>('[data-birth-location]').forEach(group => {
    const state = group.querySelector<HTMLSelectElement>('[data-birth-state]');
    const city = group.querySelector<HTMLInputElement>('[data-birth-city]');
    const hint = group.querySelector<HTMLElement>('[data-birth-location-hint]');
    if (!state || !city || !hint) return;
    function update() {
      const other = state!.value === 'other';
      city!.placeholder = other ? 'Enter city, region and country' : 'Enter your city or town';
      hint!.textContent = other ? 'Enter the city, region and country.' : 'Select your state, then enter your city or town.';
    }
    function change() { update(); city!.focus(); }
    update();
    state.addEventListener('change', change);
    cleanups.push(() => state.removeEventListener('change', change));
  });
  return () => cleanups.forEach(cleanup => cleanup());
}
