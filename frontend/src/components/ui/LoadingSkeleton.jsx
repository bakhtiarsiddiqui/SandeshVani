export default function LoadingSkeleton({
  variant = 'text',
  lines = 3,
  className = '',
}) {
  if (variant === 'card') {
    return (
      <div
        className={`rounded-xl border border-base-300 bg-base-100 p-6 space-y-4 animate-pulse shadow-sm ${className}`.trim()}
        role="status"
        aria-label="Loading content"
      >
        <div className="h-4 bg-base-300 rounded w-1/3" />
        <div className="space-y-2">
          <div className="h-3 bg-base-300 rounded w-full" />
          <div className="h-3 bg-base-300 rounded w-5/6" />
        </div>
        <div className="h-8 bg-base-300 rounded w-1/4 mt-4" />
      </div>
    );
  }

  if (variant === 'table-row') {
    return (
      <tr className="animate-pulse" role="status" aria-label="Loading row">
        <td colSpan={100} className="py-3 px-4">
          <div className="flex items-center space-x-4">
            <div className="h-3.5 bg-base-300 rounded w-1/4" />
            <div className="h-3.5 bg-base-300 rounded w-1/3" />
            <div className="h-3.5 bg-base-300 rounded w-1/6" />
            <div className="h-3.5 bg-base-300 rounded w-1/5" />
          </div>
        </td>
      </tr>
    );
  }

  return (
    <div
      className={`space-y-2 animate-pulse ${className}`.trim()}
      role="status"
      aria-label="Loading content"
    >
      {Array.from({ length: lines }).map((_, idx) => (
        <div
          key={idx}
          className={`h-3 bg-base-300 rounded ${
            idx === lines - 1 && lines > 1 ? 'w-3/5' : 'w-full'
          }`}
        />
      ))}
    </div>
  );
}

