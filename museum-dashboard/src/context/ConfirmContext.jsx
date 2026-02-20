import { createContext, useContext, useState, useRef } from 'react';

const ConfirmContext = createContext();

export function ConfirmProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const [options, setOptions] = useState({ 
    title: '', 
    message: '', 
    confirmText: 'Áno', 
    cancelText: 'Zrušiť', 
    type: 'warning' 
  });
  
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
        <div className="confirm-overlay">
            <div className="confirm-box">
                <h3 className={`confirm-title ${options.type === 'danger' ? 'danger' : ''}`}>
                    {options.title}
                </h3>
                <p className="confirm-message">
                    {options.message}
                </p>
                <div className="confirm-actions">
                    <button onClick={handleCancel} className="btn btn-secondary">
                        {options.cancelText}
                    </button>
                    <button 
                        onClick={handleConfirm} 
                        className={`btn ${options.type === 'danger' ? 'btn-danger' : 'btn-primary'}`}
                    >
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