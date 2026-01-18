import { Clapperboard, Music, Play, Trash2 } from 'lucide-react';

export default function FileItem({ file, type, isPlaying, onPlay, onDelete, isDisabled }) {
  return (
    <div className={`media-card ${isPlaying ? 'playing-now' : ''}`}>
      <div className={`media-icon-box ${type}`}>
        {type === 'video' ? <Clapperboard size={20} /> : <Music size={20} />}
      </div>
      
      <div className="media-info">
        <div className="media-name" title={file.name}>{file.name}</div>
        <div className="media-meta">{file.size} • {file.modified}</div>
      </div>
      
      <div className="media-actions">
        <button 
            className="action-btn-icon play" 
            onClick={() => !isDisabled && onPlay(type, file.name)} 
            disabled={isDisabled}
            style={{ opacity: isDisabled ? 0.5 : 1, cursor: isDisabled ? 'not-allowed' : 'pointer' }}
            title="Prehrať"
        >
            <Play size={16} fill="currentColor" />
        </button>
        <button 
            className="action-btn-icon delete" 
            onClick={() => !isDisabled && onDelete(type, file.name)} 
            disabled={isDisabled}
            style={{ opacity: isDisabled ? 0.5 : 1, cursor: isDisabled ? 'not-allowed' : 'pointer' }}
            title="Vymazať"
        >
            <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}