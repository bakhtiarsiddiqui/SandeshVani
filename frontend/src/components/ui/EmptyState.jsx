export default function EmptyState({
  title = 'No records found',
  description = 'There is currently no data available to display in this workspace.',
  action,
  icon,
  className = '',
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center p-8 sm:p-12 rounded-xl border border-dashed border-base-300 bg-base-100 ${className}`.trim()}
    >
      <div className="w-12 h-12 rounded-full bg-base-200 flex items-center justify-center text-base-content/50 mb-4">
        {icon || (
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
        )}
      </div>

      <h3 className="text-base font-semibold text-base-content mb-1">
        {title}
      </h3>

      <p className="text-xs sm:text-sm text-base-content/70 max-w-sm mb-6 leading-relaxed">
        {description}
      </p>

      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}

