import Button from '../ui/Button';
import EmptyState from '../ui/EmptyState';

export default function ApprovalQueue({ items = [], onApprove, onReject }) {
  const canApprove = typeof onApprove === 'function';
  const canReject = typeof onReject === 'function';

  return (
    <section className="glow rounded-xl border border-base-300 bg-base-100 p-6" aria-labelledby="approvals-title">
      <div className="flex items-baseline justify-between">
        <h2 id="approvals-title" className="text-base font-bold">Approvals queue</h2>
        <span className="text-xs text-base-content/60 tabular-nums">{items.length} waiting</span>
      </div>

      {items.length === 0 ? (
        <EmptyState
          className="mt-4"
          title="Nothing to approve"
          description="Campaigns show up here once a drafter submits them for review."
        />
      ) : (
        <ul className="mt-4 divide-y divide-base-300">
          {items.map((item) => (
            <li key={item.id} className="py-3 first:pt-0 last:pb-0">
              <p className="text-sm font-semibold">{item.title}</p>
              <p className="mt-0.5 text-xs text-base-content/60">
                {item.requestedBy}, {item.requestedAt}
              </p>
              <div className="mt-2.5 flex gap-2">
                <Button
                  size="sm"
                  disabled={!canApprove}
                  title={canApprove ? undefined : "Approval actions are not connected yet."}
                  onClick={() => onApprove?.(item.id)}
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!canReject}
                  title={canReject ? undefined : "Rejection actions are not connected yet."}
                  onClick={() => onReject?.(item.id)}
                >
                  Reject
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {items.length > 0 && (!canApprove || !canReject) && (
        <p className="mt-4 border-t border-base-300 pt-3 text-xs text-base-content/70">
          Review actions are unavailable in this prototype. No approval state will be changed.
        </p>
      )}
    </section>
  );
}
