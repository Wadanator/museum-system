import { createContext, useContext, useState, useRef } from 'react';

const ConfirmContext = createContext();

export function ConfirmProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const [options, setOptions] = useState({ title: '', message: '', confirmText: 'Áno', cancelText: 'Zrušiť', type: 'warning' });
  const resolveRef = useRef(null);

  const confirm = (params) => {
    setOptions({
        title: params.title || 'Potvrdenie',
        message: params.message || 'Ste si istí?',
        confirmText: params.confirmText || 'Potvrdiť',
        cancelText: params.cancelText || 'Zrušiť',
        type: params.type || 'warning'
    });
    setIsOpen(true);

    return new Promise((resolve) => {
      resolveRef.current = resolve;
    });
  };

  const handleConfirm = () => {
    setIsOpen(false);
    if (resolveRef.current) resolveRef.current(true);
  };

  const handleCancel = () => {
    setIsOpen(false);
    if (resolveRef.current) resolveRef.current(false);
  };

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {isOpen && (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 9999,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            backdropFilter: 'blur(2px)'
        }}>
            <div style={{
                backgroundColor: 'white', padding: '24px', borderRadius: '16px',
                maxWidth: '400px', width: '90%', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)',
                animation: 'pulse 0.2s ease-out'
            }}>
                <h3 style={{marginTop: 0, fontSize: '1.25rem', color: options.type === 'danger' ? '#dc2626' : '#1f2937'}}>
                    {options.title}
                </h3>
                <p style={{color: '#4b5563', marginBottom: '24px', lineHeight: '1.5'}}>
                    {options.message}
                </p>
                <div style={{display: 'flex', justifyContent: 'flex-end', gap: '12px'}}>
                    <button onClick={handleCancel} className="btn btn-secondary" style={{padding: '8px 16px'}}>
                        {options.cancelText}
                    </button>
                    <button onClick={handleConfirm} className={`btn ${options.type === 'danger' ? 'btn-danger' : 'btn-primary'}`} style={{padding: '8px 16px'}}>
                        {options.confirmText}
                    </button>
                </div>
            </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

export const useConfirm = () => useContext(ConfirmContext);