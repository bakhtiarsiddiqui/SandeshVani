export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  type = 'button',
  className = '',
  onClick,
  ...props
}) {
  const sizeClasses = {
    sm: 'btn-sm text-xs',
    md: 'btn-md text-sm',
    lg: 'btn-lg text-base',
  };

  const variantClasses = {
    primary: 'btn-primary text-white shadow-sm hover:brightness-95',
    secondary: 'bg-base-300 hover:bg-base-200 text-neutral border-base-300',
    accent: 'btn-secondary text-white shadow-sm',
    danger: 'btn-error text-white shadow-sm',
    outline: 'btn-outline btn-primary',
    ghost: 'btn-ghost text-base-content hover:bg-base-300',
  };

  const baseClasses = 'btn font-medium transition-colors focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2';
  const resolvedClass = `${baseClasses} ${variantClasses[variant] || variantClasses.primary} ${sizeClasses[size] || sizeClasses.md} ${className}`.trim();

  return (
    <button
      type={type}
      className={resolvedClass}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      onClick={onClick}
      {...props}
    >
      {isLoading && (
        <span
          className="loading loading-spinner loading-xs mr-2"
          aria-hidden="true"
        />
      )}
      {children}
    </button>
  );
}

