import SidebarNavigation from './SidebarNavigation';

export default function AppShell({
  children,
  activeNav = 'overview',
  onNavigate,
  organizationName = 'National Health Awareness Initiative',
}) {
  return (
    <div className="min-h-screen bg-base-200 flex flex-col antialiased text-base-content">
      {/* Persistent Mock / Sandbox Environment Header Strip */}
      <div
        role="region"
        aria-label="Sandbox Environment Banner"
        className="bg-amber-100 text-amber-950 px-4 py-1.5 text-xs font-semibold border-b border-amber-300 flex items-center justify-between shadow-xs shrink-0"
      >
        <div className="flex items-center gap-2 mx-auto">
          <span className="w-2 h-2 rounded-full bg-amber-600 animate-pulse" aria-hidden="true" />
          <span>
            SANDBOX / MOCK MODE — Simulated messaging channels only. No real SMS, Email, WhatsApp, or Push dispatches.
          </span>
        </div>
      </div>

      {/* Main Container with Sidebar + Content */}
      <div className="flex-1 flex flex-row w-full">
        {/* Desktop Sidebar Navigation */}
        <SidebarNavigation
          activeItem={activeNav}
          onNavigate={onNavigate}
          className="hidden md:flex"
        />

        {/* Content Wrapper */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Top Organization Context Bar */}
          <header className="h-14 bg-base-100 border-b border-base-300 px-6 flex items-center justify-between shrink-0 shadow-2xs">
            <div className="flex items-center gap-2">
              <span className="text-xs text-base-content/60 font-medium">Organization:</span>
              <span className="text-xs font-bold text-base-content bg-base-200 px-2.5 py-1 rounded-md border border-base-300/80">
                {organizationName}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-secondary bg-secondary/10 px-2.5 py-1 rounded-full border border-secondary/20">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
                Tenant Isolated
              </span>
            </div>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto space-y-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

