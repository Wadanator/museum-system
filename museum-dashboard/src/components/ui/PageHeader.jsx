export default function PageHeader({ title, icon: Icon, children }) {
  return (
    <div className="header-row" style={{
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '24px',
        paddingBottom: '16px',
        borderBottom: '1px solid #e5e7eb',
        flexWrap: 'wrap',
        gap: '16px'
    }}>
      <h2 style={{ 
          margin: 0, 
          display: 'flex', 
          alignItems: 'center', 
          gap: '12px',
          color: '#111827',
          fontSize: '1.5rem'
      }}>
        {Icon && <Icon size={32} style={{ color: '#2563eb' }} />}
        {title}
      </h2>
      
      {/* Priestor pre tlačidlá vpravo */}
      <div className="header-actions" style={{ display: 'flex', gap: '10px' }}>
        {children}
      </div>
    </div>
  );
}