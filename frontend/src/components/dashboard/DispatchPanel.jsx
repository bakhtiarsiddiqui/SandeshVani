import { useEffect, useRef, useState } from 'react';
import Button from '../ui/Button';
import StatusBadge from '../ui/StatusBadge';
import DispatchGauge from './DispatchGauge';

const fmt = (n) => Math.round(n).toLocaleString('en-IN');

export default function DispatchPanel({ title, subtitle, channels = [] }) {
  const initialDelivered = Object.fromEntries(
    channels.map((channel) => [channel.id, channel.delivered ?? 0]),
  );
  const [delivered, setDelivered] = useState(initialDelivered);
  const deliveredRef = useRef(initialDelivered);
  const [running, setRunning] = useState(false);
  const timer = useRef(null);

  useEffect(() => () => clearInterval(timer.current), []);

  const runSimulation = () => {
    clearInterval(timer.current);
    const zero = Object.fromEntries(channels.map((channel) => [channel.id, 0]));
    const speed = Object.fromEntries(
      channels.map((channel) => [channel.id, 0.02 + Math.random() * 0.035]),
    );
    deliveredRef.current = zero;
    setDelivered(zero);
    setRunning(true);

    timer.current = setInterval(() => {
      const previous = deliveredRef.current;
      const next = {};
      let complete = true;

      for (const channel of channels) {
        const count = Math.min(
          channel.total,
          (previous[channel.id] ?? 0) + channel.total * speed[channel.id],
        );
        next[channel.id] = count;
        if (count < channel.total) complete = false;
      }

      // Compute outside a state updater so the updater remains pure under Strict Mode.
      deliveredRef.current = next;
      setDelivered(next);

      if (complete) {
        clearInterval(timer.current);
        setRunning(false);
      }
    }, 150);
  };

  const total = channels.reduce((sum, channel) => sum + channel.total, 0);
  const sent = channels.reduce((sum, channel) => sum + (delivered[channel.id] ?? 0), 0);
  const pct = total > 0 ? Math.min(100, (sent / total) * 100) : 0;

  return (
    <section className="glow rounded-xl border border-base-300 bg-base-100 p-6" aria-labelledby="dispatch-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="dispatch-title" className="text-base font-bold">{title}</h2>
          <p className="mt-0.5 text-sm text-base-content/70">{subtitle}</p>
        </div>
        <StatusBadge status="mock_sandbox" />
      </div>

      <div className="mt-6 flex flex-col items-center gap-8 sm:flex-row">
        <DispatchGauge pct={pct} />
        <ul className="w-full flex-1 space-y-4">
          {channels.map((channel) => {
            const count = delivered[channel.id] ?? 0;
            return (
              <li key={channel.id}>
                <div className="flex items-baseline justify-between text-sm">
                  <span className="font-medium">{channel.label}</span>
                  <span className="tabular-nums text-xs text-base-content/70">
                    {fmt(count)} of {fmt(channel.total)}
                  </span>
                </div>
                <div
                  className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-base-300"
                  role="progressbar"
                  aria-label={`${channel.label} delivery progress`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={channel.total ? Math.round((count / channel.total) * 100) : 0}
                >
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
                    style={{ width: `${channel.total ? (count / channel.total) * 100 : 0}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-base-300 pt-4">
        <p className="text-xs text-base-content/60">
          Simulated numbers. No messages leave the system in sandbox mode.
        </p>
        <Button size="sm" variant="outline" onClick={runSimulation} disabled={running}>
          {running ? 'Dispatching…' : 'Run sandbox dispatch'}
        </Button>
      </div>
    </section>
  );
}
