import useCountUp from '../../hooks/useCountUp';

export default function StatTile({ label, value, decimals = 0, suffix = '', hint, needsAction = false }) {
  const shown = useCountUp(value, { decimals });
  const text = Number(shown).toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return (
    <div className="glow bg-base-100 p-5">
      <p className="text-sm text-base-content/70">{label}</p>
      <p
        className={`mt-1 text-3xl font-extrabold tracking-tight tabular-nums ${
          needsAction ? 'text-primary' : 'text-base-content'
        }`}
      >
        {text}
        {suffix}
      </p>
      {hint && <p className="mt-1 text-xs text-base-content/60">{hint}</p>}
    </div>
  );
}
