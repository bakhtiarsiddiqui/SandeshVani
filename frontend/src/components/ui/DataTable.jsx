import EmptyState from './EmptyState';
import LoadingSkeleton from './LoadingSkeleton';
import Button from './Button';

export default function DataTable({
  columns = [],
  data = [],
  isLoading = false,
  error = null,
  onRetry,
  emptyTitle = 'No records found',
  emptyDescription = 'There are no items matching this criteria.',
  className = '',
}) {
  const colSpan = Math.max(columns.length, 1);

  return (
    <div className={`overflow-x-auto rounded-xl border border-base-300 bg-base-100 shadow-xs ${className}`.trim()}>
      <table className="table table-zebra w-full text-left text-sm">
        <thead className="bg-base-200/70 text-xs uppercase tracking-wider text-base-content/70 border-b border-base-300">
          <tr>
            {columns.map((col, idx) => (
              <th key={col.key || idx} scope="col" className="py-3 px-4 font-semibold">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody className="divide-y divide-base-300 text-base-content/90">
          {isLoading && (
            <>
              <LoadingSkeleton variant="table-row" />
              <LoadingSkeleton variant="table-row" />
              <LoadingSkeleton variant="table-row" />
            </>
          )}

          {!isLoading && error && (
            <tr>
              <td colSpan={colSpan} className="p-8 text-center">
                <div className="space-y-3">
                  <p className="text-sm font-medium text-error">
                    {error}
                  </p>
                  {onRetry && (
                    <Button variant="secondary" size="sm" onClick={onRetry}>
                      Retry
                    </Button>
                  )}
                </div>
              </td>
            </tr>
          )}

          {!isLoading && !error && data.length === 0 && (
            <tr>
              <td colSpan={colSpan} className="p-6">
                <EmptyState
                  title={emptyTitle}
                  description={emptyDescription}
                />
              </td>
            </tr>
          )}

          {!isLoading &&
            !error &&
            data.map((row, rowIdx) => (
              <tr key={row.id || rowIdx} className="hover:bg-base-200/50 transition-colors">
                {columns.map((col, colIdx) => (
                  <td key={col.key || colIdx} className="py-3 px-4 text-xs sm:text-sm">
                    {col.render ? col.render(row, rowIdx) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

