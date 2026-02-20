export default function StatusBadge({ status, label, className = '' }) {
    // statusy: 'online', 'offline', 'warning', 'info', 'success', 'error'
    // fallback na 'info' ak status nie je rozpoznaný
    const statusClass = status || 'info';

    return (
        <div className={`status-badge ${statusClass} ${className}`}>
            <span className="status-dot"></span>
            {label}
        </div>
    );
}