import { useState, useCallback, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

export default function Button({ 
    children, 
    onClick, 
    variant = 'primary', 
    icon: Icon, 
    isLoading = false, 
    disabled = false,
    className = '',
    size = 'medium',
    type = 'button',
    cooldown = 1000,
    ...props
}) {
  const [inCooldown, setInCooldown] = useState(false);
  const useCooldown = cooldown > 0 && type !== 'submit' && typeof onClick === 'function';

  useEffect(() => {
    return () => setInCooldown(false);
  }, []);

  const handleClick = useCallback((e) => {
    if (disabled || isLoading || (useCooldown && inCooldown)) {
        e.preventDefault();
        return;
    }
    if (onClick) onClick(e);

    if (useCooldown) {
    setInCooldown(true);
    setTimeout(() => setInCooldown(false), cooldown);
    }
  }, [onClick, disabled, isLoading, inCooldown, cooldown, useCooldown]);

  const isDisabled = disabled || isLoading || (useCooldown && inCooldown);

  // FIX: Pridané stavové triedy
  const finalClassName = [
    variant === 'unstyled' ? 'btn-unstyled' : 'btn',
    variant === 'unstyled' ? '' : (variant !== 'primary' ? `btn-${variant}` : 'btn-primary'),
    variant === 'unstyled' ? '' : (size === 'small' ? 'btn-small' : (size === 'large' ? 'btn-large' : '')),
    isDisabled ? 'is-disabled' : '',
    isLoading ? 'is-loading' : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <button 
        type={type}
        className={finalClassName}
        onClick={handleClick}
        disabled={isDisabled}
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