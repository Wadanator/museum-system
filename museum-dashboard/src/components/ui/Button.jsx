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

  useEffect(() => {
    return () => setInCooldown(false);
  }, []);

  const handleClick = useCallback((e) => {
    if (disabled || isLoading || inCooldown) {
        e.preventDefault();
        return;
    }
    if (onClick) onClick(e);

    if (cooldown > 0) {
        setTimeout(() => {
            setInCooldown(true);
            setTimeout(() => {
                setInCooldown(false);
            }, cooldown);
        }, 0);
    }
  }, [onClick, disabled, isLoading, inCooldown, cooldown]);

  const isDisabled = disabled || isLoading || inCooldown;

  // FIX: Pridané stavové triedy
  const finalClassName = [
    'btn',
    variant !== 'primary' ? `btn-${variant}` : 'btn-primary',
    size === 'small' ? 'btn-small' : (size === 'large' ? 'btn-large' : ''),
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