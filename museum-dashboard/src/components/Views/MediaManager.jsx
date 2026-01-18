import { useState } from 'react';
import { 
    Video, Upload, Trash2, Music, Volume2, 
    Clapperboard, Play, Square, FolderOpen
} from 'lucide-react';
import { useMedia } from '../../hooks/useMedia';
import '../../styles/views/media-manager.css';

import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';
import Card from '../ui/Card';
import Modal from '../ui/Modal';

const MediaManager = () => {
  const { 
    videos, audios, isLoading, playingFile, 
    uploadMedia, deleteMedia, playMediaFile, stopAllMedia 
  } = useMedia();

  const [deleteModal, setDeleteModal] = useState({
    isOpen: false, type: '', fileName: '', inputValue: ''
  });

  // Handlery
  const handleUploadClick = (type) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = type === 'video' ? "video/*,image/*,.mkv" : "audio/*";
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (file) uploadMedia(type, file);
    };
    input.click();
  };

  const openDeleteModal = (type, fileName) => setDeleteModal({ isOpen: true, type, fileName, inputValue: '' });
  const closeDeleteModal = () => setDeleteModal(prev => ({ ...prev, isOpen: false }));
  
  const confirmDelete = async () => {
    if (deleteModal.inputValue !== deleteModal.fileName) return;
    const success = await deleteMedia(deleteModal.type, deleteModal.fileName);
    if (success) closeDeleteModal();
  };

  // Komponent pre položku súboru
  const FileItem = ({ file, type }) => (
    <div className={`media-card ${playingFile === file.name ? 'playing-now' : ''}`}>
      <div className={`media-icon-box ${type}`}>
        {type === 'video' ? <Clapperboard size={20} /> : <Music size={20} />}
      </div>
      <div className="media-info">
        <div className="media-name" title={file.name}>{file.name}</div>
        <div className="media-meta">{file.size} • {file.modified}</div>
      </div>
      <div className="media-actions">
        <button className="action-btn-icon play" onClick={() => playMediaFile(type, file.name)} title="Prehrať">
            <Play size={16} fill="currentColor" />
        </button>
        <button className="action-btn-icon delete" onClick={() => openDeleteModal(type, file.name)} title="Vymazať">
            <Trash2 size={16} />
        </button>
      </div>
    </div>
  );

  if (isLoading) return <div className="p-8 text-center text-slate-500">Načítavam knižnicu médií...</div>;

  return (
    <div className="tab-content active">
        {/* Nový Header */}
        <PageHeader 
            title="Správca Médií" 
            subtitle="Audio a Video knižnica"
            icon={FolderOpen}
        >
            <Button 
                onClick={stopAllMedia} 
                className="bg-red-500 hover:bg-red-600 text-white border-red-600 gap-2"
                variant="danger"
            >
                <Square size={16} fill="currentColor" />
                STOP VŠETKO
            </Button>
        </PageHeader>
      
      <div className="media-grid-container" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '24px' }}>
          {/* VIDEO SECTION */}
          <Card 
            title={`Video & Obrázky (${videos.length})`} 
            icon={Video} 
            actions={
              <Button size="small" variant="secondary" onClick={() => handleUploadClick('video')} icon={Upload}>
                  Nahrať
              </Button>
            }
          >
              <div className="files-list">
                 {videos.length > 0 ? videos.map(f => <FileItem key={f.name} file={f} type="video" />) : <div className="empty-state">Žiadne video súbory</div>}
              </div>
          </Card>

          {/* AUDIO SECTION */}
          <Card 
            title={`Zvukové efekty (${audios.length})`} 
            icon={Volume2} 
            actions={
              <Button size="small" variant="secondary" onClick={() => handleUploadClick('audio')} icon={Upload}>
                  Nahrať
              </Button>
            }
          >
               <div className="files-list">
                 {audios.length > 0 ? audios.map(f => <FileItem key={f.name} file={f} type="audio" />) : <div className="empty-state">Žiadne audio súbory</div>}
              </div>
          </Card>
      </div>

      {/* DELETE MODAL */}
      <Modal 
        isOpen={deleteModal.isOpen} 
        title="Vymazať súbor?" 
        type="danger"
        onClose={closeDeleteModal}
        footer={
            <>
                <Button variant="secondary" onClick={closeDeleteModal}>Zrušiť</Button>
                <Button variant="danger" disabled={deleteModal.inputValue !== deleteModal.fileName} onClick={confirmDelete}>
                    Vymazať súbor
                </Button>
            </>
        }
      >
        <p className="text-slate-300 mb-4">
            Pre potvrdenie napíšte názov súboru: <strong className="text-white bg-slate-700 px-1 rounded">{deleteModal.fileName}</strong>
        </p>
        <input 
            type="text" 
            className="w-full p-2 bg-slate-900 border border-slate-700 rounded text-white font-mono focus:border-red-500 outline-none" 
            value={deleteModal.inputValue}
            onChange={(e) => setDeleteModal(prev => ({...prev, inputValue: e.target.value}))}
            autoFocus
            placeholder="Opíšte názov súboru..."
        />
      </Modal>
    </div>
  );
};

export default MediaManager;