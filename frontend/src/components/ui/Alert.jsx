export default function Alert({
  variant = 'info',
  title,
  children,
  className = '',
  onClose,
}) {
  const configs = {
    info: {
      container: 'bg-blue-50 text-blue-900 border-blue-200',
      icon: (
        <svg className="w-5 h-5 text-primary shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    success: {
      container: 'bg-green-50 text-green-900 border-green-200',
      icon: (
        <svg className="w-5 h-5 text-success shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    warning: {
      container: 'bg-amber-50 text-amber-900 border-amber-200',
      icon: (
        <svg className="w-5 h-5 text-warning shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    },
    error: {
      container: 'bg-red-50 text-red-900 border-red-200',
      icon: (
        <svg className="w-5 h-5 text-error shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    sandbox_notice: {
      container: 'bg-amber-100 text-amber-950 border-amber-300 font-medium',
      icon: (
        <svg className="w-5 h-5 text-amber-800 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
    },
  };

  const config = configs[variant] || configs.info;
  const role = variant === 'error' ? 'alert' : 'status';

  return (
    <div
      role={role}
      className={`flex items-start gap-3 p-3.5 rounded-lg border text-sm shadow-sm ${config.container} ${className}`.trim()}
    >
      {config.icon}
      <div className="flex-1 space-y-0.5">
        {title && <h4 className="font-semibold text-sm">{title}</h4>}
        <div className="text-xs leading-relaxed">{children}</div>
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="text-base-content/50 hover:text-base-content focus-visible:outline-2 focus-visible:outline-primary p-0.5 rounded"
          aria-label="Dismiss notification"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}

