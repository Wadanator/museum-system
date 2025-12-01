import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { authFetch } from '../../services/api';
import '../../styles/views/media-manager.css';

const MediaManager = () => {
  const [videos, setVideos] = useState([]);
  const [audios, setAudios] = useState([]);
  const [loading, setLoading] = useState(true);

  // Stav pre modálne okno mazania
  const [deleteModal, setDeleteModal] = useState({
    isOpen: false,
    type: '',
    fileName: '',
    inputValue: ''
  });

  useEffect(() => {
    fetchMedia();
  }, []);

  const fetchMedia = async () => {
    try {
      const [videoRes, audioRes] = await Promise.all([
        authFetch('/api/media/video'),
        authFetch('/api/media/audio')
      ]);

      if (videoRes.ok) setVideos(await videoRes.json());
      if (audioRes.ok) setAudios(await audioRes.json());
    } catch (error) {
      console.error("Chyba pri načítaní médií:", error);
      toast.error("Nepodarilo sa načítať zoznam súborov");
    } finally {
      setLoading(false);
    }
  };

  // --- LOGIKA MAZANIA ---

  const openDeleteModal = (type, fileName) => {
    setDeleteModal({
      isOpen: true,
      type,
      fileName,
      inputValue: '' 
    });
  };

  const closeDeleteModal = () => {
    setDeleteModal(prev => ({ ...prev, isOpen: false }));
  };

  const confirmDelete = async () => {
    const { type, fileName, inputValue } = deleteModal;

    if (inputValue !== fileName) {
      toast.error("Názov súboru sa nezhoduje!");
      return;
    }

    const loadingToast = toast.loading(`Mažem ${fileName}...`);
    closeDeleteModal(); 

    try {
      const res = await authFetch(`/api/media/${type}/${fileName}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        if (type === 'video') {
          setVideos(prev => prev.filter(v => v.name !== fileName));
        } else {
          setAudios(prev => prev.filter(a => a.name !== fileName));
        }
        toast.success(`${fileName} bol vymazaný`, { id: loadingToast });
      } else {
        const err = await res.json();
        toast.error(`Chyba: ${err.error || 'Nepodarilo sa vymazať súbor'}`, { id: loadingToast });
      }
    } catch (error) {
      console.error("Delete error:", error);
      toast.error("Chyba pripojenia pri mazaní", { id: loadingToast });
    }
  };

  // --- LOGIKA NAHRÁVANIA ---

  const handleUpload = (type) => {
    const input = document.createElement('input');
    input.type = 'file';
    
    if (type === 'video') {
      input.accept = "video/*,image/*,.mkv"; 
    } else {
      input.accept = "audio/*";
    }

    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const loadingToast = toast.loading(`Nahrávam ${file.name}...`);
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await authFetch(`/api/media/${type}`, {
          method: 'POST',
          body: formData
        });

        if (res.ok) {
          const data = await res.json();
          if (type === 'video') {
            setVideos(prev => [...prev, data.file]);
          } else {
            setAudios(prev => [...prev, data.file]);
          }
          toast.success("Súbor úspešne nahraný", { id: loadingToast });
        } else {
          const err = await res.json();
          toast.error(`Chyba: ${err.error || 'Upload zlyhal'}`, { id: loadingToast });
        }
      } catch (error) {
        console.error("Upload error:", error);
        toast.error("Chyba pripojenia pri nahrávaní", { id: loadingToast });
      }
    };

    input.click();
  };

  // Komponent Karty
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
            onClick={() => openDeleteModal(type, file.name)} 
            title="Vymazať súbor"
        >
            🗑️
        </button>
      </div>
    </div>
  );

  if (loading) return <div className="media-manager-container">Načítavam médiá...</div>;

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
            <div className="empty-media-state">Žiadne videá.</div>
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
            <div className="empty-media-state">Žiadne zvuky.</div>
          )}
        </div>
      </div>

      {/* --- MODÁLNE OKNO PRE MAZANIE --- */}
      {deleteModal.isOpen && (
        <div className="modal-overlay">
          <div className="modal-content delete-modal">
            <h3>⚠️ Vymazať súbor?</h3>
            <p>
              Táto akcia je nevratná. Ak chcete vymazať súbor 
              <strong> {deleteModal.fileName}</strong>, 
              napíšte jeho celý názov nižšie:
            </p>
            
            <div className="modal-input-wrapper">
              <input 
                type="text" 
                className="modal-input"
                placeholder="Sem napíšte názov súboru"
                value={deleteModal.inputValue}
                onChange={(e) => setDeleteModal(prev => ({...prev, inputValue: e.target.value}))}
                autoFocus
              />
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={closeDeleteModal}>
                Zrušiť
              </button>
              <button 
                className="btn btn-danger" 
                disabled={deleteModal.inputValue !== deleteModal.fileName}
                onClick={confirmDelete}
              >
                Vymazať súbor
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MediaManager;