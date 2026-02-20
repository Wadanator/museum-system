import { X } from 'lucide-react';

export default function Modal({ isOpen, title, onClose, children, footer, type = 'default' }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
            <h3 className={`modal-title ${type === 'danger' ? 'danger' : ''}`}>
                {title}
            </h3>
            <button onClick={onClose} className="modal-close-btn" aria-label="Zatvoriť">
                <X size={20} />
            </button>
        </div>
        
        {/* FIX: Použitie CSS triedy namiesto inline style */}
        <div className="modal-body-text">
            {children}
        </div>

        {footer && (
            <div className="modal-actions">
                {footer}
            </div>
        )}
      </div>
    </div>
  );
}