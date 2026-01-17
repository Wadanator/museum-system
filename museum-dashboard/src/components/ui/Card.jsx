export default function Card({ children, title, icon: Icon, className = '', actions }) {
  return (
    <div className={`card-component ${className}`} style={{
        background: 'white',
        borderRadius: '12px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        padding: '24px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column'
    }}>
      {(title || Icon || actions) && (
        <div className="card-header" style={{
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '16px'
        }}>
            <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.1rem', color: '#374151' }}>
                {Icon && <Icon size={20} />}
                {title}
            </h3>
            {actions && <div className="card-actions">{actions}</div>}
        </div>
      )}
      
      <div className="card-content" style={{ flex: 1 }}>
        {children}
      </div>
    </div>
  );
}