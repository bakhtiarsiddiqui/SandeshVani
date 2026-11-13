import { useState } from "react";
import PageHeader from "../../components/layout/PageHeader";
import DataTable from "../../components/ui/DataTable";
import StatusBadge from "../../components/ui/StatusBadge";
import Button from "../../components/ui/Button";
import StatTile from "../../components/dashboard/StatTile";

const CAMPAIGNS = [
  { id: "c1", name: "Dengue prevention advisory", channel: "SMS · WhatsApp · Email", audience: "Meerut district", recipients: "12,450", status: "draft" },
  { id: "c2", name: "Vaccination camp schedule", channel: "SMS · Push", audience: "Urban health centres", recipients: "8,200", status: "pending" },
  { id: "c3", name: "Water quality bulletin", channel: "Email", audience: "Ward 4 · Ward 7", recipients: "3,150", status: "approved" },
  { id: "c4", name: "Heatwave safety notice", channel: "SMS · WhatsApp", audience: "Registered residents", recipients: "18,900", status: "rejected" },
];
const CONTACTS = [
  { id: "a1", name: "Meera Singh", email: "meera.singh@example.test", phone: "+919876540001", district: "Meerut", language: "Hindi" },
  { id: "a2", name: "Arjun Verma", email: "arjun.verma@example.test", phone: "+919876540002", district: "Ghaziabad", language: "English" },
  { id: "a3", name: "Farah Khan", email: "farah.khan@example.test", phone: "+919876540003", district: "Meerut", language: "Hindi" },
];
const MEMBERS = [
  { id: "m1", name: "Anita Rao", email: "anita.rao@example.test", role: "Organization Administrator", status: "Active" },
  { id: "m2", name: "Imran Qureshi", email: "imran.qureshi@example.test", role: "Campaign Manager", status: "Active" },
  { id: "m3", name: "Kavya Sharma", email: "kavya.sharma@example.test", role: "Communication Team", status: "Active" },
  { id: "m4", name: "Rohan Das", email: "rohan.das@example.test", role: "Approver", status: "Invited" },
];
const POSTS = [
  { id: "p1", title: "Dengue prevention: घर के आसपास पानी जमा न होने दें", type: "Public advisory", language: "Hindi", status: "draft" },
  { id: "p2", title: "Vaccination camp schedule", type: "Announcement", language: "English", status: "pending" },
  { id: "p3", title: "Heatwave safety instructions", type: "Public advisory", language: "English + Hindi", status: "approved" },
];
const TEMPLATES = [
  { id: "t1", name: "Public health advisory", channel: "SMS", languages: "English · Hindi", version: "v1.2", status: "approved" },
  { id: "t2", name: "Department announcement", channel: "Email", languages: "English · Hindi", version: "v1.0", status: "draft" },
];
const APPROVALS = [
  { id: "r1", title: "Vaccination camp schedule", submittedBy: "Imran Qureshi", submittedAt: "13 Nov 2026 · 10:20", channels: "SMS · Push", status: "pending" },
  { id: "r2", title: "Dengue prevention advisory", submittedBy: "Kavya Sharma", submittedAt: "12 Nov 2026 · 16:45", channels: "SMS · WhatsApp · Email", status: "pending" },
];

function DemoNotice() {
  return <div className="rounded-lg border border-base-300 bg-base-100 px-4 py-3 text-xs text-base-content/70"><span className="font-semibold text-primary">SAMPLE DATA.</span> Interactions are local demonstrations only. They do not create backend records, approve real campaigns or send messages.</div>;
}
function Frame({ title, subtitle, stats = [], actions, children }) {
  return <div className="space-y-6"><PageHeader title={title} subtitle={subtitle} breadcrumbs={["Platform", title]} badge={<StatusBadge status="mock_sandbox" label="Sample data" />} actions={actions} />{stats.length > 0 && <section aria-label={title + " summary"} className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-base-300 bg-base-300 lg:grid-cols-4">{stats.map((stat) => <StatTile key={stat.label} {...stat} />)}</section>}<DemoNotice />{children}</div>;
}
function Section({ title, description, actions, children }) {
  return <section className="space-y-3"><div className="flex flex-wrap items-end justify-between gap-2"><div><h2 className="text-base font-bold">{title}</h2>{description && <p className="text-xs text-base-content/60 mt-0.5">{description}</p>}</div>{actions}</div>{children}</section>;
}
function DemoCreate({ title, label, onCancel, onSave }) {
  const [value, setValue] = useState("");
  return <form className="rounded-xl border border-base-300 bg-base-100 p-4 space-y-3" onSubmit={(event) => { event.preventDefault(); if (value.trim()) onSave(value.trim()); }}><h3 className="font-semibold text-sm">{title}</h3><label className="form-control w-full"><span className="label-text text-xs mb-1">{label}</span><input className="input input-bordered input-sm w-full bg-base-100" value={value} onChange={(event) => setValue(event.target.value)} autoFocus /></label><div className="flex justify-end gap-2"><Button size="sm" variant="ghost" onClick={onCancel}>Cancel</Button><Button size="sm" type="submit" disabled={!value.trim()}>Save sample item</Button></div></form>;
}
const CAMPAIGN_COLUMNS = [
  { key: "name", header: "Campaign", render: (row) => <span className="font-semibold text-base-content">{row.name}</span> },
  { key: "channel", header: "Channels" }, { key: "audience", header: "Audience" }, { key: "recipients", header: "Recipients" },
  { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
];
const CONTACT_COLUMNS = [{ key: "name", header: "Contact" }, { key: "email", header: "Email" }, { key: "phone", header: "Phone" }, { key: "district", header: "District" }, { key: "language", header: "Language" }];
const MEMBER_COLUMNS = [{ key: "name", header: "Member" }, { key: "email", header: "Email" }, { key: "role", header: "Assigned role" }, { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status === "Active" ? "approved" : "pending"} label={row.status} /> }];

export function OrganizationAdminWorkspace({ permissions = [] }) {
  const canMembers = permissions.includes("members:read");
  const canRoles = permissions.includes("roles:read");
  const canManage = permissions.includes("organization:update");
  const [tab, setTab] = useState(canMembers ? "members" : canRoles ? "roles" : "governance");
  const [members, setMembers] = useState(MEMBERS);
  const [showInvite, setShowInvite] = useState(false);
  const tabs = [...(canMembers ? [["members", "Members"]] : []), ...(canRoles ? [["roles", "Role assignments"]] : []), ...(canManage ? [["governance", "Governance"]] : [])];
  const current = tabs.some(([id]) => id === tab) ? tab : tabs[0]?.[0];
  return <Frame title="Organization Administration" subtitle="Manage your institution’s members, role assignments and tenant governance." stats={[
    { label: "Members", value: 24, hint: "Illustrative total" }, { label: "Organization roles", value: 4, hint: "Baseline role set" }, { label: "Pending invitations", value: 2, hint: "Sample records" }, { label: "Policy alerts", value: 0, hint: "Sample indicator" },
  ]}>
    <div className="flex flex-wrap gap-2" role="tablist" aria-label="Organization administration sections">{tabs.map(([id, label]) => <Button key={id} size="sm" variant={current === id ? "primary" : "ghost"} role="tab" aria-selected={current === id} onClick={() => setTab(id)}>{label}</Button>)}</div>
    {current === "members" && <Section title="Members" description="Synthetic directory for the active organization." actions={permissions.includes("members:create") ? <Button size="sm" onClick={() => setShowInvite((value) => !value)}>Invite member</Button> : null}>
      {showInvite && <DemoCreate title="Add demonstration member" label="Member name" onCancel={() => setShowInvite(false)} onSave={(name) => { setMembers((rows) => [...rows, { id: "m" + Date.now(), name, email: "new.member@example.test", role: "Unassigned", status: "Invited" }]); setShowInvite(false); }} />}
      <DataTable columns={MEMBER_COLUMNS} data={members} />
    </Section>}
    {current === "roles" && <Section title="Role assignments" description="Roles are assigned per organization. Platform roles cannot be granted by an organization administrator."><div className="grid gap-3 md:grid-cols-2">{[["Organization Administrator", "Organization settings, memberships and permitted role assignment."], ["Campaign Manager", "Audience workflows, campaign authoring and submission."], ["Communication Team", "Content preparation, templates and assigned audience access."], ["Approver", "Review assigned campaign versions and submit decisions."]].map(([name, detail]) => <div key={name} className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">{name}</h3><p className="mt-1 text-sm text-base-content/70">{detail}</p></div>)}</div></Section>}
    {current === "governance" && <Section title="Organization governance"><div className="grid gap-3 md:grid-cols-2"><div className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">Tenant boundary</h3><p className="mt-1 text-sm text-base-content/70">Member and role operations remain scoped to the active organization.</p></div><div className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">Access principles</h3><p className="mt-1 text-sm text-base-content/70">Multiple roles combine their server-issued permissions. Backend checks remain authoritative.</p></div></div></Section>}
  </Frame>;
}

export function CampaignManagerWorkspace({ permissions = [] }) {
  const canCreate = permissions.includes("campaigns:create");
  const [campaigns, setCampaigns] = useState(CAMPAIGNS);
  const [showCreate, setShowCreate] = useState(false);
  return <Frame title="Campaign Management" subtitle={canCreate ? "Prepare public-awareness campaigns, choose audiences and channels, and track review readiness." : "Review campaign information in read-only mode."} actions={canCreate ? <Button size="sm" onClick={() => setShowCreate((value) => !value)}>Create campaign</Button> : null} stats={[
    { label: "Campaigns", value: 18, hint: "Illustrative period" }, { label: "Drafts", value: 5, hint: "Sample status" }, { label: "Awaiting review", value: 3, hint: "Sample status" }, { label: "Channels", value: 4, hint: "Mock only" },
  ]}>
    {showCreate && <DemoCreate title="New campaign draft" label="Campaign name" onCancel={() => setShowCreate(false)} onSave={(name) => { setCampaigns((rows) => [{ id: "c" + Date.now(), name, channel: "Not selected", audience: "Not selected", recipients: "0", status: "draft" }, ...rows]); setShowCreate(false); }} />}
    <Section title="Campaign register" description="Campaign data is illustrative until campaign APIs are implemented."><DataTable columns={CAMPAIGN_COLUMNS} data={campaigns} /></Section>
    <Section title="Campaign preparation" description="The intended governed workflow. These steps do not persist or submit a campaign."><div className="grid gap-3 md:grid-cols-3">{[["1. Objective", "Define the public-awareness goal and owner."], ["2. Channels & content", "Choose mock channels and reviewed English/Hindi variants."], ["3. Audience & review", "Preview eligibility and submit an immutable version for approval."]].map(([title, body]) => <div key={title} className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm text-base-content/70">{body}</p></div>)}</div></Section>
  </Frame>;
}

export function CommunicationWorkspace({ permissions = [] }) {
  const canCreate = permissions.includes("templates:create");
  const [tab, setTab] = useState(canCreate ? "posts" : "templates");
  const [posts, setPosts] = useState(POSTS);
  const [templates, setTemplates] = useState(TEMPLATES);
  const [showCreate, setShowCreate] = useState(false);
  const current = canCreate ? tab : "templates";
  const save = (name) => {
    if (current === "posts") setPosts((rows) => [{ id: "p" + Date.now(), title: name, type: "Announcement", language: "English", status: "draft" }, ...rows]);
    else setTemplates((rows) => [{ id: "t" + Date.now(), name, channel: "SMS", languages: "English", version: "v0.1", status: "draft" }, ...rows]);
    setShowCreate(false);
  };
  return <Frame title={canCreate ? "Posts & Content Management" : "Template Library"} subtitle="Prepare announcements, public notices and reusable message content in English and Hindi." actions={canCreate ? <Button size="sm" onClick={() => setShowCreate((value) => !value)}>{current === "posts" ? "Create post" : "Create template"}</Button> : null} stats={[
    { label: "Posts", value: posts.length, hint: "Sample records" }, { label: "Templates", value: templates.length, hint: "Sample records" }, { label: "Languages", value: 2, hint: "English and Hindi" }, { label: "Pending review", value: 1, hint: "Sample status" },
  ]}>
    {canCreate && <div className="flex flex-wrap gap-2" role="tablist" aria-label="Content sections">{[["posts", "Posts & announcements"], ["templates", "Templates"], ["languages", "Language variants"]].map(([id, label]) => <Button key={id} size="sm" variant={current === id ? "primary" : "ghost"} role="tab" aria-selected={current === id} onClick={() => { setTab(id); setShowCreate(false); }}>{label}</Button>)}</div>}
    {showCreate && current !== "languages" && <DemoCreate title={current === "posts" ? "New announcement draft" : "New template draft"} label={current === "posts" ? "Post title" : "Template name"} onCancel={() => setShowCreate(false)} onSave={save} />}
    {current === "posts" && <Section title="Posts & announcements"><DataTable columns={[{ key: "title", header: "Post" }, { key: "type", header: "Type" }, { key: "language", header: "Language" }, { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> }]} data={posts} /></Section>}
    {current === "templates" && <Section title="Template library"><DataTable columns={[{ key: "name", header: "Template" }, { key: "channel", header: "Channel" }, { key: "languages", header: "Languages" }, { key: "version", header: "Version" }, { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> }]} data={templates} /></Section>}
    {current === "languages" && <Section title="Language variants" description="English and Hindi are the MVP baseline."><div className="grid gap-3 md:grid-cols-2">{[["English", "en"], ["Hindi", "hi"]].map(([name, code]) => <div key={code} className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">{name}</h3><p className="mt-1 text-xs text-base-content/60">Language code: {code}</p><StatusBadge status="approved" label="MVP language" /></div>)}</div></Section>}
  </Frame>;
}

export function ApprovalsWorkspace({ permissions = [] }) {
  const [rows, setRows] = useState(APPROVALS);
  const [selectedId, setSelectedId] = useState(APPROVALS[0]?.id);
  const selected = rows.find((row) => row.id === selectedId);
  const decide = (status) => setRows((items) => items.map((row) => row.id === selectedId ? { ...row, status } : row));
  return <Frame title="Approvals & Governance" subtitle="Review submissions against their version, audience, channel and content summary." stats={[
    { label: "Pending review", value: rows.filter((row) => row.status === "pending").length, hint: "Sample queue" }, { label: "Approved", value: 8, hint: "Sample period" }, { label: "Changes requested", value: 2, hint: "Sample period" }, { label: "Review SLA", value: "—", hint: "Not measured" },
  ]}>
    <div className="grid gap-5 lg:grid-cols-3">
      <section className="rounded-xl border border-base-300 bg-base-100 p-4"><h2 className="font-bold text-base">Review queue</h2><ul className="mt-3 divide-y divide-base-300">{rows.map((row) => <li key={row.id} className="py-3 first:pt-0"><button type="button" onClick={() => setSelectedId(row.id)} className="w-full text-left"><span className="font-semibold text-sm">{row.title}</span><span className="block text-xs text-base-content/60 mt-1">{row.submittedBy} · {row.submittedAt}</span><span className="mt-2 inline-block"><StatusBadge status={row.status} /></span></button></li>)}</ul></section>
      <section className="lg:col-span-2 rounded-xl border border-base-300 bg-base-100 p-5 space-y-3"><h2 className="font-bold text-base">Submission review</h2>{selected ? <><p className="font-semibold">{selected.title}</p><p className="text-xs text-base-content/60">Submitted by {selected.submittedBy}</p><div className="border-t border-base-300 pt-3 space-y-2 text-sm"><p>Channels: {selected.channels}</p><p>Version: Demo v1 (sample)</p><p>Audience: Synthetic audience preview</p><p>Content hash: Not generated</p></div><div className="flex flex-wrap gap-2">{permissions.includes("approvals:approve") && <Button size="sm" disabled={selected.status !== "pending"} onClick={() => decide("approved")}>Approve sample</Button>}{permissions.includes("approvals:reject") && <Button size="sm" variant="outline" disabled={selected.status !== "pending"} onClick={() => decide("rejected")}>Request changes</Button>}</div></> : <p className="text-sm text-base-content/60">Select a submission to review.</p>}</section>
    </div>
  </Frame>;
}

export function AudienceWorkspace({ permissions = [] }) {
  const [contacts, setContacts] = useState(CONTACTS);
  const [showAdd, setShowAdd] = useState(false);
  return <Frame title="Audience & Contacts" subtitle="Review tenant-scoped contact records and the validated CSV upload workflow." actions={permissions.includes("audiences:create") ? <Button size="sm" onClick={() => setShowAdd((value) => !value)}>Add contact</Button> : null} stats={[
    { label: "Contacts", value: 12450, hint: "Illustrative total" }, { label: "Active", value: 11980, hint: "Sample status" }, { label: "Languages", value: 2, hint: "English and Hindi" }, { label: "Import rows", value: 100000, hint: "Upload limit target" },
  ]}>
    {showAdd && <DemoCreate title="New contact preview" label="Contact name" onCancel={() => setShowAdd(false)} onSave={(name) => { setContacts((rows) => [{ id: "a" + Date.now(), name, email: "new.contact@example.test", phone: "+919876540099", district: "Meerut", language: "English" }, ...rows]); setShowAdd(false); }} />}
    <Section title="Contact directory"><DataTable columns={CONTACT_COLUMNS} data={contacts} /></Section>
    <Section title="CSV import"><div className="rounded-xl border border-base-300 bg-base-100 p-4"><p className="text-sm font-semibold">Secure upload API is available.</p><p className="mt-1 text-xs text-base-content/60">File submission is not wired to this demonstration page yet. The validated upload endpoint is already implemented in the backend.</p><StatusBadge status="mock_sandbox" label="UI integration pending" /></div></Section>
  </Frame>;
}

export function SegmentsWorkspace({ permissions = [] }) {
  const [created, setCreated] = useState([]);
  const canCreate = permissions.includes("segments:create");
  return <Frame title="Audience Segments" subtitle="Preview the allowlisted audience filter builder and segment workflow." actions={canCreate ? <Button size="sm" onClick={() => setCreated((items) => [...items, "New segment " + (items.length + 1)])}>Add sample segment</Button> : null}>
    <Section title="Saved segments"><div className="grid gap-3 md:grid-cols-3">{[["Meerut Hindi subscribers", "Meerut · Hindi · Active", "4,820"], ["Urban health centres", "Urban · English/Hindi", "2,180"], ["Emergency notices", "Active · SMS available", "8,400"], ...created.map((name) => [name, "Local demo segment", "0"])].map(([name, rule, count]) => <div key={name} className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">{name}</h3><p className="mt-1 text-xs text-base-content/60">{rule}</p><p className="mt-3 text-2xl font-bold tabular-nums">{count}</p><p className="text-xs text-base-content/50">Estimated members · sample</p></div>)}</div></Section>
    <Section title="Segment builder" description="Filters are illustrative. The server-side filter grammar and preview API are not implemented."><div className="rounded-xl border border-base-300 bg-base-100 p-4 grid gap-3 md:grid-cols-3"><label className="form-control"><span className="label-text text-xs">District</span><select className="select select-bordered select-sm bg-base-100"><option>Meerut</option><option>Ghaziabad</option><option>Any district</option></select></label><label className="form-control"><span className="label-text text-xs">Preferred language</span><select className="select select-bordered select-sm bg-base-100"><option>Hindi</option><option>English</option><option>Any</option></select></label><label className="form-control"><span className="label-text text-xs">Contact status</span><select className="select select-bordered select-sm bg-base-100"><option>Active</option><option>Inactive</option></select></label></div></Section>
  </Frame>;
}

export function ConsentWorkspace() {
  const rows = [
    { id: "1", contact: "Meera Singh", channel: "SMS", purpose: "Public health notices", state: "Recorded" },
    { id: "2", contact: "Arjun Verma", channel: "Email", purpose: "Department updates", state: "Withdrawn" },
    { id: "3", contact: "Farah Khan", channel: "WhatsApp", purpose: "Emergency alerts", state: "Unknown" },
  ];
  return <Frame title="Consent & Suppression" subtitle="Inspect channel- and purpose-specific consent history and suppression controls.">
    <div className="rounded-xl border border-warning/40 bg-warning/10 p-4 text-sm"><p className="font-semibold">Fail-closed rule</p><p className="mt-1 text-xs text-base-content/70">Unknown or missing consent is not treated as permission where consent is required. These are sample records; no consent decision is stored.</p></div>
    <Section title="Consent history"><DataTable columns={[{ key: "contact", header: "Contact" }, { key: "channel", header: "Channel" }, { key: "purpose", header: "Purpose" }, { key: "state", header: "State", render: (row) => <StatusBadge status={row.state === "Recorded" ? "approved" : row.state === "Withdrawn" ? "rejected" : "pending"} label={row.state} /> }]} data={rows} /></Section>
    <Section title="Suppression checks"><div className="grid gap-3 md:grid-cols-3">{[["Channel suppression", "Block delivery for a suppressed channel."], ["Purpose limitation", "Check the declared communication purpose."], ["Withdrawal history", "Preserve the withdrawal evidence."]].map(([title, body]) => <div key={title} className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm text-base-content/70">{body}</p></div>)}</div></Section>
  </Frame>;
}

export function DistributionWorkspace() {
  const [previewed, setPreviewed] = useState(false);
  return <Frame title="Mock Distribution" subtitle="Inspect the intended delivery workflow without contacting external providers." stats={[
    { label: "Mock campaigns", value: 18, hint: "Illustrative period" }, { label: "Recipients", value: 42800, hint: "Sample total" }, { label: "Mock accepted", value: 96.2, decimals: 1, suffix: "%", hint: "Sample metric" }, { label: "Unknown outcomes", value: 0, hint: "Sample metric" },
  ]}>
    <div className="rounded-xl border border-primary/40 bg-primary/10 p-4 text-sm"><p className="font-semibold">SANDBOX ONLY</p><p className="mt-1 text-xs text-base-content/70">No Email, SMS, WhatsApp or Push provider is connected. This workspace cannot send real messages.</p></div>
    <Section title="Execution preview" description="The future run requires an approved version, eligible recipient snapshot and idempotent mock adapter."><div className="rounded-xl border border-base-300 bg-base-100 p-5 space-y-3"><div className="grid gap-3 md:grid-cols-3">{[["1. Eligibility", "Consent, suppression and tenant re-check"], ["2. Snapshot", "Freeze approved recipients and content"], ["3. Execute", "Mock adapter, attempts and safe retries"]].map(([title, body]) => <div key={title} className="rounded-lg bg-base-200/60 p-4"><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm text-base-content/70">{body}</p></div>)}</div><Button size="sm" onClick={() => setPreviewed(true)}>Generate local preview</Button>{previewed && <p role="status" className="text-xs text-success">Local preview generated. No worker or outbound message was triggered.</p>}</div></Section>
    <Section title="Channel status"><div className="grid grid-cols-2 gap-3 md:grid-cols-4">{["Email", "SMS", "WhatsApp", "Push"].map((channel) => <div key={channel} className="rounded-xl border border-base-300 bg-base-100 p-4"><p className="font-bold">{channel}</p><p className="mt-1 text-xs text-base-content/60">Mock adapter target</p><StatusBadge status="mock_sandbox" label="Not connected" /></div>)}</div></Section>
  </Frame>;
}

export function AnalyticsWorkspace() {
  return <Frame title="Delivery Analytics" subtitle="Review channel and campaign summaries when backed by verified execution data." stats={[
    { label: "Campaigns", value: 18, hint: "Illustrative period" }, { label: "Recipients", value: 42800, hint: "Illustrative total" }, { label: "Accepted", value: 96.2, decimals: 1, suffix: "%", hint: "Sample metric" }, { label: "Unknown outcomes", value: 0, hint: "Sample metric" },
  ]}>
    <Section title="Channel performance" description="Sample values; analytics endpoints and metric definitions are not implemented."><div className="rounded-xl border border-base-300 bg-base-100 p-5 space-y-4">{[["SMS", 84], ["WhatsApp", 72], ["Email", 58], ["Push", 43]].map(([label, value]) => <div key={label}><div className="flex justify-between text-xs"><span>{label}</span><span className="tabular-nums">{value}%</span></div><div className="mt-1 h-2 rounded-full bg-base-300 overflow-hidden"><div className="h-full bg-primary" style={{ width: value + "%" }} /></div></div>)}</div></Section>
    <Section title="Metric definitions"><div className="grid gap-3 md:grid-cols-2">{[["Accepted", "Accepted by a mock adapter."], ["Delivered", "Confirmed delivery result where available."], ["Failed", "A terminal delivery failure."], ["Retrying / Unknown", "Separate retry state and unresolved outcome."]].map(([title, body]) => <div key={title} className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm text-base-content/70">{body}</p></div>)}</div></Section>
  </Frame>;
}

export function AuditWorkspace() {
  return <Frame title="Audit Log" subtitle="Inspect an organization-scoped view of important administrative and workflow events.">
    <Section title="Recent activity" description="Synthetic records. The append-oriented audit service is not yet implemented."><DataTable columns={[{ key: "event", header: "Event" }, { key: "actor", header: "Actor" }, { key: "resource", header: "Resource" }, { key: "time", header: "Timestamp" }]} data={[
      { id: "e1", event: "Member role assigned", actor: "Anita Rao", resource: "Imran Qureshi", time: "13 Nov 2026 · 09:45" },
      { id: "e2", event: "Campaign submitted", actor: "Imran Qureshi", resource: "Vaccination camp schedule", time: "13 Nov 2026 · 10:20" },
      { id: "e3", event: "Content updated", actor: "Kavya Sharma", resource: "Dengue prevention advisory", time: "12 Nov 2026 · 16:45" },
    ]} /></Section>
    <div className="rounded-xl border border-base-300 bg-base-100 p-5 text-sm text-base-content/70">Production audit records must be written server-side, append-oriented, tenant-scoped and protected from ordinary user modification.</div>
  </Frame>;
}

export function OrganizationSettingsWorkspace() {
  return <Frame title="Organization Settings" subtitle="Review the active institution's profile and tenant operating context.">
    <Section title="Organization profile"><div className="grid gap-3 md:grid-cols-2"><div className="rounded-xl border border-base-300 bg-base-100 p-4"><p className="text-xs text-base-content/60">Organization identity</p><p className="mt-1 font-semibold">Active tenant context</p><p className="mt-1 text-xs text-base-content/60">Values are supplied by the authenticated organization context.</p></div><div className="rounded-xl border border-base-300 bg-base-100 p-4"><p className="text-xs text-base-content/60">Communication mode</p><p className="mt-1 font-semibold">Sandbox / Mock only</p><p className="mt-1 text-xs text-base-content/60">External providers are not configured.</p></div></div></Section>
    <Section title="Governance controls"><p className="rounded-xl border border-base-300 bg-base-100 p-4 text-sm text-base-content/70">Member and role changes are managed separately. Organization settings shown here are read-only until the settings API is implemented.</p></Section>
  </Frame>;
}

export function PlatformAdministrationWorkspace() {
  const [tab, setTab] = useState("overview");
  const tabs = [["overview", "Platform overview"], ["organizations", "Organizations"], ["users", "Platform users"], ["operations", "System operations"]];
  const orgs = [
    { id: "o1", name: "Department of Public Health", region: "Meerut", status: "Active", members: 42 },
    { id: "o2", name: "Municipal Corporation", region: "Ghaziabad", status: "Active", members: 28 },
    { id: "o3", name: "District Education Office", region: "Noida", status: "Review", members: 16 },
  ];
  return <Frame title="Platform Administration" subtitle="Restricted global workspace for users with a server-verified Platform Operator assignment." stats={[
    { label: "Organizations", value: 14, hint: "Sample platform data" }, { label: "Active tenants", value: 12, hint: "Sample platform data" }, { label: "Users", value: 284, hint: "Sample platform data" }, { label: "System alerts", value: 0, hint: "Sample platform data" },
  ]}>
    <div className="rounded-xl border border-warning/40 bg-warning/10 p-4 text-sm"><p className="font-semibold">Restricted platform workspace</p><p className="mt-1 text-xs text-base-content/70">Access comes only from the authenticated user's platform-role assignment. Organization administrators cannot grant global access. Directory and operations records are samples.</p></div>
    <div className="flex flex-wrap gap-2" role="tablist" aria-label="Platform administration sections">{tabs.map(([id, label]) => <Button key={id} size="sm" variant={tab === id ? "primary" : "ghost"} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>{label}</Button>)}</div>
    {tab === "overview" && <Section title="Platform overview"><div className="grid gap-3 md:grid-cols-3">{[["Tenant lifecycle", "Organization onboarding and status review"], ["Platform identity", "Controlled operator assignments"], ["Operations", "System health, notices and incidents"]].map(([title, body]) => <div key={title} className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm text-base-content/70">{body}</p></div>)}</div></Section>}
    {tab === "organizations" && <Section title="Organizations" description="Synthetic cross-tenant directory; platform organization APIs are not implemented."><DataTable columns={[{ key: "name", header: "Organization" }, { key: "region", header: "Region" }, { key: "members", header: "Members" }, { key: "status", header: "Status" }]} data={orgs} /></Section>}
    {tab === "users" && <Section title="Platform users" description="Global user directory preview. Tenant membership administration remains in the organization workspace."><DataTable columns={[{ key: "name", header: "User" }, { key: "email", header: "Email" }, { key: "role", header: "Platform assignment" }, { key: "status", header: "Status" }]} data={[
      { id: "u1", name: "Platform Operator", email: "operator@example.test", role: "Platform Operator", status: "Active" },
      { id: "u2", name: "Operations Reviewer", email: "reviewer@example.test", role: "Read-only operator", status: "Active" },
    ]} /></Section>}
    {tab === "operations" && <Section title="System operations"><div className="grid gap-3 md:grid-cols-2">{[["API health", "Live health endpoint not connected"], ["Background processing", "Worker status not connected"], ["Security events", "Audit and incident stream pending"], ["Storage", "Upload monitoring pending"]].map(([title, body]) => <div key={title} className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm text-base-content/70">{body}</p><StatusBadge status="pending" label="Integration pending" /></div>)}</div></Section>}
  </Frame>;
}
