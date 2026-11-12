import PageHeader from '../components/layout/PageHeader';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import StatTile from '../components/dashboard/StatTile';
import DispatchPanel from '../components/dashboard/DispatchPanel';
import ApprovalQueue from '../components/dashboard/ApprovalQueue';

// SAMPLE DATA ONLY. The backend has no campaign/delivery endpoints yet, so these shapes are
// placeholders, not a contract. When the OpenAPI contract lands, pass real data and isSample={false}.
const SAMPLE = {
  stats: { campaigns: 128, recipients: 1240500, deliveryRate: 96.4, awaiting: 3 },
  dispatch: {
    title: 'Dengue prevention advisory',
    subtitle: 'Meerut district, sent to 132,600 recipients',
    channels: [
      { id: 'sms', label: 'SMS', total: 48200, delivered: 47310 },
      { id: 'email', label: 'Email', total: 31500, delivered: 30140 },
      { id: 'whatsapp', label: 'WhatsApp', total: 40100, delivered: 39620 },
      { id: 'push', label: 'Push', total: 12800, delivered: 11890 },
    ],
  },
  approvals: [
    { id: 'a1', title: 'Polio drive reminder, Block 4', requestedBy: 'Anita Rao', requestedAt: '2 hours ago' },
    { id: 'a2', title: 'Vaccination camp schedule', requestedBy: 'Imran Qureshi', requestedAt: 'yesterday' },
    { id: 'a3', title: 'Heatwave safety notice', requestedBy: 'Anita Rao', requestedAt: 'yesterday' },
  ],
  campaigns: [
    { id: 'c1', name: 'Dengue prevention advisory', channels: ['SMS', 'Email', 'WhatsApp', 'Push'], recipients: 132600, status: 'delivered', updated: '12 Nov, 10:40' },
    { id: 'c2', name: 'Polio drive reminder, Block 4', channels: ['SMS', 'WhatsApp'], recipients: 48200, status: 'pending', updated: '12 Nov, 09:15' },
    { id: 'c3', name: 'Vaccination camp schedule', channels: ['SMS'], recipients: 21900, status: 'pending', updated: '11 Nov, 17:02' },
    { id: 'c4', name: 'Water quality bulletin', channels: ['Email', 'Push'], recipients: 9400, status: 'approved', updated: '11 Nov, 12:30' },
    { id: 'c5', name: 'Flu season guidance', channels: ['SMS', 'Email'], recipients: 60300, status: 'draft', updated: '10 Nov, 16:48' },
    { id: 'c6', name: 'Clinic timing change', channels: ['SMS'], recipients: 3100, status: 'rejected', updated: '9 Nov, 11:05' },
  ],
};

const COLUMNS = [
  { key: 'name', header: 'Campaign', render: (r) => <span className="font-semibold text-base-content">{r.name}</span> },
  { key: 'channels', header: 'Channels', render: (r) => r.channels.join(', ') },
  { key: 'recipients', header: 'Recipients', render: (r) => <span className="tabular-nums">{r.recipients.toLocaleString('en-IN')}</span> },
  { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
  { key: 'updated', header: 'Updated' },
];

export default function Overview({
  stats,
  dispatch,
  approvals,
  campaigns,
  isLoading = false,
  error = null,
  onRetry,
  actions,
  isSample = true,
  onApprove,
  onReject,
}) {
  // Never fall back to demonstration data when a caller has switched to live mode.
  const resolvedStats = stats ?? (isSample ? SAMPLE.stats : { campaigns: 0, recipients: 0, deliveryRate: 0, awaiting: 0 });
  const resolvedDispatch = dispatch ?? (isSample ? SAMPLE.dispatch : { title: 'No dispatch activity', subtitle: 'No dispatch data is available yet.', channels: [] });
  const resolvedApprovals = approvals ?? (isSample ? SAMPLE.approvals : []);
  const resolvedCampaigns = campaigns ?? (isSample ? SAMPLE.campaigns : []);

  return (
    <>
      <PageHeader
        title="Overview"
        subtitle="What has gone out, what is on its way, and what needs your decision."
        breadcrumbs={['Platform', 'Overview']}
        actions={actions}
        badge={isSample ? <StatusBadge status="mock_sandbox" label="Sample data" /> : null}
      />

      {/* One panel, four numbers: the dividers are the cell gaps */}
      {isLoading ? (
        <div role="status" aria-live="polite" className="rounded-xl border border-base-300 bg-base-100 p-6 text-sm text-base-content/70">
          Loading workspace metrics…
        </div>
      ) : (
        <section aria-label="Key numbers" className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-base-300 bg-base-300 lg:grid-cols-4">
          <StatTile label="Campaigns sent" value={resolvedStats.campaigns} hint="Since the workspace was created" />
          <StatTile label="Recipients reached" value={resolvedStats.recipients} hint="Across all channels" />
          <StatTile label="Delivery rate" value={resolvedStats.deliveryRate} decimals={1} suffix="%" hint="Last 30 days" />
          <StatTile label="Awaiting approval" value={resolvedStats.awaiting} needsAction={resolvedStats.awaiting > 0} hint="Needs a reviewer" />
        </section>
      )}

      {isLoading ? (
        <div role="status" aria-live="polite" className="rounded-xl border border-base-300 bg-base-100 p-6 text-sm text-base-content/70">
          Loading dispatch and approval data…
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <DispatchPanel title={resolvedDispatch.title} subtitle={resolvedDispatch.subtitle} channels={resolvedDispatch.channels} />
          </div>
          <ApprovalQueue items={resolvedApprovals} onApprove={onApprove} onReject={onReject} />
        </div>
      )}

      <section aria-labelledby="recent-title" className="space-y-3">
        <h2 id="recent-title" className="text-base font-bold">Recent campaigns</h2>
        <DataTable
          columns={COLUMNS}
          data={resolvedCampaigns}
          isLoading={isLoading}
          error={error}
          onRetry={onRetry}
          emptyTitle="No campaigns yet"
          emptyDescription="Create your first campaign to start reaching your audience."
        />
      </section>
    </>
  );
}
