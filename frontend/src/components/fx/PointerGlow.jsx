import { useEffect } from 'react';

/**
 * Mount once (main.jsx). Handles, via event delegation:
 *  - .glow      -> writes --x/--y so the CSS spotlight follows the cursor
 *  - .magnetic  -> nudges the button toward the cursor
 *  - any form submit -> fires "sv:dispatch" so the auth backdrop sends a signal ring
 */
export default function PointerGlow() {
  useEffect(() => {
    const onSubmit = () => window.dispatchEvent(new Event('sv:dispatch'));
    document.addEventListener('submit', onSubmit, true);

    const finePointer = window.matchMedia('(pointer: fine)').matches;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!finePointer || reduceMotion) {
      return () => document.removeEventListener('submit', onSubmit, true);
    }

    let frame = 0;
    let ev = null;

    const apply = () => {
      frame = 0;
      const target = ev && ev.target instanceof Element ? ev.target : null;
      if (!target) return;

      const glow = target.closest('.glow');
      if (glow) {
        const b = glow.getBoundingClientRect();
        glow.style.setProperty('--x', `${ev.clientX - b.left}px`);
        glow.style.setProperty('--y', `${ev.clientY - b.top}px`);
      }

      const mag = target.closest('.magnetic');
      if (mag && !mag.disabled) {
        const b = mag.getBoundingClientRect();
        const dx = (ev.clientX - (b.left + b.width / 2)) / b.width;
        const dy = (ev.clientY - (b.top + b.height / 2)) / b.height;
        mag.style.transform = `translate(${dx * 8}px, ${dy * 6}px)`;
      }
    };

    const onMove = (e) => {
      ev = e;
      if (!frame) frame = requestAnimationFrame(apply);
    };

    const onOut = (e) => {
      const m = e.target instanceof Element ? e.target.closest('.magnetic') : null;
      if (m && !m.contains(e.relatedTarget)) m.style.transform = '';
    };

    document.addEventListener('pointermove', onMove, { passive: true });
    document.addEventListener('pointerout', onOut, { passive: true });
    return () => {
      document.removeEventListener('submit', onSubmit, true);
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerout', onOut);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return null;
}
