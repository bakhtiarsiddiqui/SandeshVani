import SidebarNavigation from "./SidebarNavigation";

export default function AppShell({
  children,
  activeNav = "overview",
  onNavigate,
  navItems = [],
  headerActions,
  organizationName = "National Health Awareness Initiative",
  roles = [],
}) {
  const roleNames = roles.map((role) => typeof role === "string" ? role : role?.name).filter(Boolean);
  return (
    <div className="min-h-screen bg-base-200 flex flex-col antialiased text-base-content">
      <div role="region" aria-label="Sandbox Environment Banner" className="bg-primary/15 text-primary px-4 py-1.5 text-xs font-semibold border-b border-primary/40 flex items-center justify-between shadow-xs shrink-0">
        <div className="flex items-center gap-2 mx-auto">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse" aria-hidden="true" />
          <span>SANDBOX / MOCK MODE — Simulated messaging channels only. No real SMS, Email, WhatsApp, or Push dispatches.</span>
        </div>
      </div>
      {navItems.length > 1 && (
        <nav className="md:hidden flex gap-1 overflow-x-auto bg-secondary px-3 py-2 border-b border-neutral/40" aria-label="Mobile workspace navigation">
          {navItems.map((item) => (
            <button key={item.id} type="button" onClick={() => onNavigate?.(item.id)} aria-current={activeNav === item.id ? "page" : undefined} className={"shrink-0 rounded-md px-3 py-2 text-xs font-medium transition-colors " + (activeNav === item.id ? "bg-neutral text-primary border-b-2 border-primary" : "text-secondary-content/85 hover:bg-secondary-content/10")}>
              {item.label}
            </button>
          ))}
        </nav>
      )}
      <div className="flex-1 flex flex-row w-full">
        <SidebarNavigation activeItem={activeNav} onNavigate={onNavigate} items={navItems} className="hidden md:flex" />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="min-h-14 bg-base-100 border-b border-base-300 px-6 py-2 flex flex-wrap items-center justify-between gap-2 shrink-0 shadow-2xs">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-xs text-base-content/60 font-medium">Organization:</span>
                <span className="text-xs font-bold text-base-content bg-base-200 px-2.5 py-1 rounded-md border border-base-300/80">{organizationName}</span>
              </div>
              {roleNames.length > 0 && <p className="text-[10px] text-base-content/50">Active roles: {roleNames.join(" · ")}</p>}
            </div>
            <div className="flex items-center gap-2">
              {headerActions}
              <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-secondary bg-secondary/10 px-2.5 py-1 rounded-full border border-secondary/20"><span className="w-1.5 h-1.5 rounded-full bg-secondary" />Tenant Isolated</span>
            </div>
          </header>
          <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto space-y-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
