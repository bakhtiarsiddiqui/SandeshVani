import { cloneElement, isValidElement, useId } from 'react';

export default function FormField({
  label,
  id,
  error,
  helperText,
  required = false,
  children,
  className = '',
}) {
  const generatedId = useId();
  const fieldId = id || generatedId;
  const errorId = error ? `${fieldId}-error` : undefined;
  const helperId = helperText ? `${fieldId}-helper` : undefined;
  const describedBy = [errorId, helperId].filter(Boolean).join(' ') || undefined;
  const controlProps = {
    id: fieldId,
    'aria-describedby': describedBy,
    hasError: Boolean(error),
  };

  const control = typeof children === 'function'
    ? children(controlProps)
    : isValidElement(children)
      ? cloneElement(children, {
          id: children.props.id || fieldId,
          'aria-describedby': children.props['aria-describedby'] || describedBy,
          hasError: children.props.hasError ?? Boolean(error),
        })
      : children;

  return (
    <div className={`form-control w-full space-y-1.5 ${className}`.trim()}>
      {label && (
        <label htmlFor={fieldId} className="label-text block text-sm font-medium text-base-content">
          {label}
          {required && <span className="text-error ml-1" aria-hidden="true">*</span>}
          {required && <span className="sr-only">(required)</span>}
        </label>
      )}

      <div>{control}</div>

      {helperText && !error && (
        <p id={helperId} className="text-xs text-base-content/60">
          {helperText}
        </p>
      )}

      {error && (
        <p id={errorId} role="alert" className="text-xs font-medium text-error flex items-center gap-1">
          <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}
