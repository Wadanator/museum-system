export default function ButtonGroup({ children, className = '', gap = '10px' }) {
  return (
    <div 
      className={`button-group ${className}`} 
      style={{ 
        display: 'flex', 
        gap: gap, 
        marginTop: '10px',
        width: '100%' 
      }}
    >
      {children}
    </div>
  );
}