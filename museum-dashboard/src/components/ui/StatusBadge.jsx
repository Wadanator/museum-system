export default function StatusBadge({ status, label, className = '' }) {
    // status mapping: 
    // 'online' -> zelená
    // 'offline' -> červená
    // 'warning' -> oranžová
    // 'info' -> modrá (default)

    const colors = {
        online: '#10b981',
        offline: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };

    const color = colors[status] || colors.offline;

    return (
        <div className={`status-badge ${status} ${className}`} style={{ 
            display: 'inline-flex', 
            alignItems: 'center', 
            gap: 8,
            padding: '6px 12px',
            borderRadius: '20px',
            backgroundColor: `${color}15`, // 15 = cca 10% opacity hex
            color: color,
            fontWeight: 600,
            fontSize: '0.9rem',
            border: `1px solid ${color}30`
        }}>
            <span style={{
                width: 8, 
                height: 8, 
                borderRadius: '50%',
                backgroundColor: color,
                boxShadow: `0 0 8px ${color}`
            }}></span>
            {label}
        </div>
    );
}