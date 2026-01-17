import Button from './Button';
import { X } from 'lucide-react';

export default function Modal({ isOpen, title, onClose, children, footer, type = 'default' }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 1000, backdropFilter: 'blur(4px)'
    }}>
      <div className="modal-content" style={{
          background: 'white',
          padding: '24px',
          borderRadius: '16px',
          width: '90%', maxWidth: '500px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
          animation: 'fadeIn 0.2s ease-out'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ margin: 0, fontSize: '1.25rem', color: type === 'danger' ? '#ef4444' : '#111827' }}>
                {title}
            </h3>
            <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280' }}>
                <X size={20} />
            </button>
        </div>
        
        <div style={{ marginBottom: '24px', color: '#4b5563' }}>
            {children}
        </div>

        <div className="modal-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            {footer}
        </div>
      </div>
    </div>
  );
}