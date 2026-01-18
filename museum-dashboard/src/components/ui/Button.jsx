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

  // Bezpečné čistenie timeoutu ak by sa komponent odpojil
  useEffect(() => {
    return () => setInCooldown(false);
  }, []);

  const handleClick = useCallback((e) => {
    // Ak je loading, disabled alebo v cooldowne, stop
    if (disabled || isLoading || inCooldown) {
        e.preventDefault();
        return;
    }

    // Vykonaj akciu
    if (onClick) onClick(e);

    // Aktivuj cooldown ak je nastavený (teraz defaultne je)
    if (cooldown > 0) {
        setInCooldown(true);
        setTimeout(() => {
            setInCooldown(false);
        }, cooldown);
    }
  }, [onClick, disabled, isLoading, inCooldown, cooldown]);

  const isDisabled = disabled || isLoading || inCooldown;

  // Pridanie vizuálnej triedy pre cooldown
  const finalClassName = `btn ${variant !== 'primary' ? `btn-${variant}` : 'btn-primary'} ${size === 'small' ? 'btn-small' : (size === 'large' ? 'btn-large' : '')} ${className}`;

  return (
    <button 
        type={type}
        className={finalClassName}
        onClick={handleClick}
        disabled={isDisabled}
        style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            gap: size === 'small' ? '6px' : '8px',
            opacity: isDisabled ? 0.7 : 1,
            cursor: isDisabled ? 'not-allowed' : 'pointer',
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