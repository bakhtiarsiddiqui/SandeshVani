export default function PageHeader({
  title,
  subtitle,
  breadcrumbs = [],
  actions,
  badge,
  className = '',
}) {
  return (
    <header className={`space-y-3 pb-6 border-b border-base-300 ${className}`.trim()}>
      {breadcrumbs.length > 0 && (
        <nav className="text-xs text-base-content/60" aria-label="Breadcrumb">
          <ul className="flex items-center gap-1.5 flex-wrap">
            {breadcrumbs.map((crumb, idx) => (
              <li key={idx} className="flex items-center gap-1.5">
                {idx > 0 && <span className="text-base-content/40">/</span>}
                <span className={idx === breadcrumbs.length - 1 ? 'font-medium text-base-content' : ''}>
                  {crumb}
                </span>
              </li>
            ))}
          </ul>
        </nav>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-base-content">
              {title}
            </h1>
            {badge && <div>{badge}</div>}
          </div>
          {subtitle && (
            <p className="text-xs sm:text-sm text-base-content/70 max-w-2xl leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>

        {actions && (
          <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
            {actions}
          </div>
        )}
      </div>
    </header>
  );
}


