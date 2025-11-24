import { useState } from 'react';
import toast from 'react-hot-toast';
import '../../styles/views/media-manager.css'; // Import nového CSS

const MediaManager = ({ sceneName }) => {
  // Dummy dáta (neskôr nahradíš API volaním)
  const [videos, setVideos] = useState([
    { name: 'intro_sequence.mp4', size: '24.5 MB', modified: '15.11.2023' },
    { name: 'loop_background.mp4', size: '128.2 MB', modified: '10.11.2023' },
    { name: 'black_screen.png', size: '0.5 MB', modified: '01.10.2023' }
  ]);

  const [audios, setAudios] = useState([
    { name: 'voiceover_main.mp3', size: '4.2 MB', modified: '16.11.2023' },
    { name: 'click_effect.wav', size: '0.1 MB', modified: '20.10.2023' }
  ]);

  const handleDelete = (type, fileName) => {
    if (!window.confirm(`Naozaj chcete vymazať súbor ${fileName}?`)) return;

    if (type === 'video') {
      setVideos(prev => prev.filter(v => v.name !== fileName));
    } else {
      setAudios(prev => prev.filter(a => a.name !== fileName));
    }
    toast.success(`${fileName} bol vymazaný`);
  };

  const handleUpload = (type) => {
    // Tu bude logika pre otvorenie file pickera a upload
    toast('Otváram dialóg pre nahrávanie... (Demo)', {
      icon: '📂',
      style: { borderRadius: '10px', background: '#333', color: '#fff' },
    });
  };

  // Pomocný komponent pre jednu kartu (definovaný vnútri alebo importovaný)
  const FileCard = ({ file, type }) => (
    <div className="media-card">
      <div className={`media-icon-box ${type}`}>
        {type === 'video' ? '🎬' : '🎵'}
      </div>
      <div className="media-info">
        <div className="media-name" title={file.name}>{file.name}</div>
        <div className="media-meta">
          <span>{file.size}</span>
          <span>•</span>
          <span>{file.modified}</span>
        </div>
      </div>
      <div className="media-actions">
        <button 
            className="btn-delete" 
            onClick={() => handleDelete(type, file.name)} 
            title="Vymazať súbor"
        >
            🗑️
        </button>
      </div>
    </div>
  );

  return (
    <div className="media-manager-container">
      {/* Sekcia Videá */}
      <div className="media-section">
        <div className="section-header">
          <div className="section-title">
            🎥 Video & Obrázky
            <span className="count-badge">{videos.length}</span>
          </div>
          <button className="btn btn-secondary btn-small" onClick={() => handleUpload('video')}>
            ⬆️ Nahrať Video
          </button>
        </div>
        
        <div className="media-grid">
          {videos.length > 0 ? (
            videos.map(file => <FileCard key={file.name} file={file} type="video" />)
          ) : (
            <div className="empty-media-state">
              Pre túto scénu nie sú nahrané žiadne videá.
            </div>
          )}
        </div>
      </div>

      {/* Sekcia Audio */}
      <div className="media-section">
        <div className="section-header">
          <div className="section-title">
            🔊 Zvukové efekty
            <span className="count-badge">{audios.length}</span>
          </div>
          <button className="btn btn-secondary btn-small" onClick={() => handleUpload('audio')}>
            ⬆️ Nahrať Audio
          </button>
        </div>

        <div className="media-grid">
          {audios.length > 0 ? (
            audios.map(file => <FileCard key={file.name} file={file} type="audio" />)
          ) : (
            <div className="empty-media-state">
              Pre túto scénu nie sú nahrané žiadne zvuky.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MediaManager;