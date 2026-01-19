import { useState } from 'react';
import { Video, Upload, Square, FolderOpen, Volume2 } from 'lucide-react';
import { useMedia } from '../../hooks/useMedia';
import '../../styles/views/media-manager.css';

// Komponenty UI
import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';
import Card from '../ui/Card';
import Modal from '../ui/Modal';
// Nový import
import FileItem from '../Media/FileItem';

const MediaManager = () => {
  // Logika je správne v Hooku
  const { 
    videos, audios, isLoading, playingFile, 
    uploadMedia, deleteMedia, playMediaFile, stopAllMedia 
  } = useMedia();

  // UI State pre Modal (toto patrí sem, nie do hooku)
  const [deleteModal, setDeleteModal] = useState({
    isOpen: false, type: '', fileName: '', inputValue: ''
  });

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

  if (isLoading) return <div className="loading-state">Načítavam knižnicu médií...</div>;

  const areItemsDisabled = isLoading || playingFile !== null;

  return (
    <div className="media-manager-view">
        <PageHeader 
            title="Správca Médií" 
            subtitle="Audio a Video knižnica"
            icon={FolderOpen}
        >
            <Button 
                onClick={stopAllMedia} 
                className="bg-red-500 hover:bg-red-600 text-white border-red-600 gap-2"
                variant="danger"
                disabled={areItemsDisabled} // Tiež zablokujeme STOP ak systém pracuje
            >
                <Square size={16} fill="currentColor" />
                STOP VŠETKO
            </Button>
        </PageHeader>
      
      {/* Grid trieda namiesto inline štýlu */}
      <div className="media-grid-container">
          {/* VIDEO SECTION */}
          <Card 
            title={`Video & Obrázky (${videos.length})`} 
            icon={Video} 
            actions={
              <Button size="small" variant="secondary" onClick={() => handleUploadClick('video')} icon={Upload} disabled={isLoading}>
                  Nahrať
              </Button>
            }
          >
              <div className="files-list">
                 {videos.length > 0 ? (
                    videos.map(f => (
                        <FileItem 
                            key={f.name} 
                            file={f} 
                            type="video" 
                            isPlaying={playingFile === f.name}
                            onPlay={playMediaFile}
                            onDelete={openDeleteModal}
                            isDisabled={areItemsDisabled} // Aplikovaný spam fix
                        />
                    ))
                 ) : (
                    <div className="empty-state">Žiadne video súbory</div>
                 )}
              </div>
          </Card>

          {/* AUDIO SECTION */}
          <Card 
            title={`Zvukové efekty (${audios.length})`} 
            icon={Volume2} 
            actions={
              <Button size="small" variant="secondary" onClick={() => handleUploadClick('audio')} icon={Upload} disabled={isLoading}>
                  Nahrať
              </Button>
            }
          >
               <div className="files-list">
                 {audios.length > 0 ? (
                    audios.map(f => (
                        <FileItem 
                            key={f.name} 
                            file={f} 
                            type="audio" 
                            isPlaying={playingFile === f.name}
                            onPlay={playMediaFile}
                            onDelete={openDeleteModal}
                            isDisabled={areItemsDisabled}
                        />
                    ))
                 ) : (
                    <div className="empty-state">Žiadne audio súbory</div>
                 )}
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
        <p className="modal-text">
            Pre potvrdenie napíšte názov súboru: <strong className="highlight-text">{deleteModal.fileName}</strong>
        </p>
        <input 
            type="text" 
            className="modal-input"
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