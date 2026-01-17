import { Loader2 } from 'lucide-react';

export default function Button({ 
    children, 
    onClick, 
    variant = 'primary', // Možnosti: primary, secondary, danger, success, ghost
    icon: Icon, 
    isLoading = false, 
    disabled = false,
    className = '',
    size = 'medium',     // Možnosti: small, medium, large
    type = 'button',
    ...props
}) {
  const baseClass = "btn"; 
  const variantClass = variant !== 'primary' ? `btn-${variant}` : 'btn-primary';
  const sizeClass = size === 'small' ? 'btn-small' : (size === 'large' ? 'btn-large' : '');
  
  return (
    <button 
        type={type}
        className={`${baseClass} ${variantClass} ${sizeClass} ${className}`}
        onClick={onClick}
        disabled={disabled || isLoading}
        style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            gap: size === 'small' ? '6px' : '8px',
            opacity: (disabled || isLoading) ? 0.7 : 1,
            cursor: (disabled || isLoading) ? 'not-allowed' : 'pointer',
            ...props.style
        }}
        {...props}
    >
        {isLoading ? (
            <Loader2 className="animate-spin" size={size === 'small' ? 14 : 18} />
        ) : (
            Icon && <Icon size={size === 'small' ? 16 : 20} />
        )}
        {children}
    </button>
  );
}