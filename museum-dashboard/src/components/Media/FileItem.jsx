import { Clapperboard, Music, Play, Trash2 } from 'lucide-react';
import Button from '../ui/Button';

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
        <Button
          variant="unstyled"
            size="small"
            className="action-btn-icon play"
            onClick={() => !isDisabled && onPlay(type, file.name)}
            disabled={isDisabled}
            icon={Play}
            title="Prehrať"
            aria-label="Prehrať"
            cooldown={0}
        />
        <Button
          variant="unstyled"
            size="small"
            className="action-btn-icon delete"
            onClick={() => !isDisabled && onDelete(type, file.name)}
            disabled={isDisabled}
            icon={Trash2}
            title="Vymazať"
            aria-label="Vymazať"
            cooldown={0}
        />
      </div>
    </div>
  );
}