import { useEffect, useState } from 'react';

// Counts from 0 to target once (and again if target changes). Respects reduced motion.
export default function useCountUp(target, { duration = 900, decimals = 0 } = {}) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const total = reduce ? 0 : duration;
    let raf = 0;
    let start;
    const step = (now) => {
      if (start === undefined) start = now;
      const t = total === 0 ? 1 : Math.min((now - start) / total, 1);
      setValue(target * (1 - Math.pow(1 - t, 3)));
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return decimals ? value.toFixed(decimals) : Math.round(value);
}
