const ICONS = {
  overview: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
  audience: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z",
  segments: "M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z",
  consent: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622z",
  campaigns: "M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7z",
  content: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a2 2 0 01.707.293l5.414 5.414a2 2 0 01.293.707V19a2 2 0 01-2 2z",
  approvals: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622",
  distribution: "M4 12h16M12 4l8 8-8 8M4 6v12",
  analytics: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6m6 0V9a2 2 0 012-2h2a2 2 0 012 2v10m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14",
  organization: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197",
  "org-settings": "M12 8a4 4 0 100 8 4 4 0 000-8zm8 4a8 8 0 01-.1 1.25l1.4 1.1-1.5 2.6-1.7-.7",
  audit: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  platform: "M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z",
};

export default function SidebarNavigation({ activeItem = "overview", onNavigate, items = [], className = "" }) {
  return (
    <aside className={"w-64 bg-secondary text-secondary-content border-r border-neutral/40 flex flex-col shrink-0 min-h-screen " + className} aria-label="Sidebar Navigation">
      <div className="p-4 border-b border-secondary-content/15">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-neutral text-primary flex items-center justify-center font-bold text-base shadow-xs">S</div>
          <div><h2 className="text-sm font-bold tracking-tight text-secondary-content leading-none">SandeshVani</h2><p className="text-[10px] text-secondary-content/70 font-medium tracking-wide uppercase mt-1">संदेशवाणी · MVP</p></div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto" aria-label="Main Navigation">
        <p className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-secondary-content/60">Your workspaces</p>
        {items.map((item) => {
          const isActive = activeItem === item.id;
          return <button key={item.id} type="button" onClick={() => onNavigate?.(item.id)} aria-current={isActive ? "page" : undefined} className={"w-full flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors text-left focus-visible:outline-2 focus-visible:outline-primary " + (isActive ? "bg-neutral text-primary font-semibold border-l-4 border-primary pl-2" : "text-secondary-content/85 hover:bg-secondary-content/10 hover:text-secondary-content")}>
            <span className={isActive ? "text-primary" : "text-secondary-content/55"}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d={ICONS[item.id] || "M5 12h14"} /></svg></span>
            <span className="truncate">{item.label}</span>
          </button>;
        })}
      </nav>
      <div className="p-3 border-t border-secondary-content/15 text-xs text-secondary-content/70"><div className="px-3 py-1.5 rounded-md bg-secondary-content/10 text-[11px] font-medium flex items-center justify-between"><span>Access:</span><span className="text-secondary-content font-semibold">Assigned roles</span></div></div>
    </aside>
  );
}
