export default function Input({
  id,
  type = 'text',
  placeholder = '',
  hasError = false,
  disabled = false,
  className = '',
  ...props
}) {
  const baseInput = 'input input-bordered w-full bg-base-100 text-base-content placeholder:text-base-content/40 transition-colors focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-1';
  const errorClass = hasError ? 'input-error focus-visible:outline-error border-error' : 'border-base-300 focus-visible:border-primary';

  return (
    <input
      id={id}
      type={type}
      placeholder={placeholder}
      disabled={disabled}
      aria-invalid={hasError ? 'true' : 'false'}
      className={`${baseInput} ${errorClass} ${className}`.trim()}
      {...props}
    />
  );
}

