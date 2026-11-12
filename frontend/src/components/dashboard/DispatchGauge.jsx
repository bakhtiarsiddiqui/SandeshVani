const DOTS = 60;

/** Delivery progress as a ring of recipients that light up: the same motif as the sign-in scene. */
export default function DispatchGauge({ pct, size = 188 }) {
  const c = size / 2;
  const r = size / 2 - 10;
  const safePct = Number.isFinite(pct) ? Math.min(100, Math.max(0, pct)) : 0;
  const lit = Math.round((safePct / 100) * DOTS);

  return (
    <div
      role="progressbar"
      aria-label="Delivery progress"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(safePct)}
      className="relative shrink-0"
      style={{ width: size, height: size }}
    >
      <svg viewBox={`0 0 ${size} ${size}`} className="absolute inset-0 -rotate-90" aria-hidden="true">
        {Array.from({ length: DOTS }, (_, i) => {
          const a = (i / DOTS) * 2 * Math.PI;
          const on = i < lit;
          return (
            <circle
              key={i}
              cx={c + r * Math.cos(a)}
              cy={c + r * Math.sin(a)}
              r={on ? 3.2 : 2.2}
              className={`transition-colors duration-300 ${on ? 'fill-primary' : 'fill-base-300'}`}
              style={{ transitionDelay: `${i * 6}ms` }}
            />
          );
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-extrabold tabular-nums leading-none">
          {Math.round(safePct)}
          <span className="text-xl font-bold text-base-content/60">%</span>
        </span>
        <span className="mt-1 text-xs text-base-content/60">delivered</span>
      </div>
    </div>
  );
}
