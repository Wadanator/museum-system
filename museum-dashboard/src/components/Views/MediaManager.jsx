import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { authFetch } from '../../services/api';
import { Video, Upload, Trash2, Music, Volume2, Clapperboard, AlertTriangle } from 'lucide-react';
import '../../styles/views/media-manager.css';

// Import UI
import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';
import Card from '../ui/Card';
import Modal from '../ui/Modal';

const MediaManager = () => {
  const [videos, setVideos] = useState([]);
  const [audios, setAudios] = useState([]);
  const [loading, setLoading] = useState(true);

  // Stav pre modal
  const [deleteModal, setDeleteModal] = useState({
    isOpen: false,
    type: '',
    fileName: '',
    inputValue: ''
  });

  useEffect(() => { fetchMedia(); }, []);

  const fetchMedia = async () => {
    try {
      const [videoRes, audioRes] = await Promise.all([
        authFetch('/api/media/video'),
        authFetch('/api/media/audio')
      ]);
      if (videoRes.ok) setVideos(await videoRes.json());
      if (audioRes.ok) setAudios(await audioRes.json());
    } catch (error) {
      toast.error("Nepodarilo sa načítať médiá");
    } finally {
      setLoading(false);
    }
  };

  const openDeleteModal = (type, fileName) => setDeleteModal({ isOpen: true, type, fileName, inputValue: '' });
  const closeDeleteModal = () => setDeleteModal(prev => ({ ...prev, isOpen: false }));

  const confirmDelete = async () => {
    const { type, fileName, inputValue } = deleteModal;
    if (inputValue !== fileName) return toast.error("Názov sa nezhoduje!");

    closeDeleteModal();
    const loadToast = toast.loading(`Mažem ${fileName}...`);

    try {
      const res = await authFetch(`/api/media/${type}/${fileName}`, { method: 'DELETE' });
      if (res.ok) {
        if (type === 'video') setVideos(p => p.filter(v => v.name !== fileName));
        else setAudios(p => p.filter(a => a.name !== fileName));
        toast.success("Vymazané", { id: loadToast });
      } else {
        toast.error("Chyba pri mazaní", { id: loadToast });
      }
    } catch (e) { toast.error("Chyba pripojenia", { id: loadToast }); }
  };

  const handleUpload = (type) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = type === 'video' ? "video/*,image/*,.mkv" : "audio/*";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const loadToast = toast.loading(`Nahrávam ${file.name}...`);
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await authFetch(`/api/media/${type}`, { method: 'POST', body: formData });
        if (res.ok) {
          const data = await res.json();
          type === 'video' ? setVideos(p => [...p, data.file]) : setAudios(p => [...p, data.file]);
          toast.success("Nahrané", { id: loadToast });
        } else toast.error("Upload zlyhal", { id: loadToast });
      } catch (e) { toast.error("Chyba uploadu", { id: loadToast }); }
    };
    input.click();
  };

  // Sub-komponent pre súbor (lokálne definovaný, alebo ho môžeš dať do samostatného súboru)
  const FileItem = ({ file, type }) => (
    <div className="media-card" style={{display: 'flex', alignItems: 'center', padding: 12, border: '1px solid #e5e7eb', borderRadius: 8, gap: 12, background: 'white'}}>
      <div className={`media-icon-box ${type}`} style={{padding: 10, borderRadius: 8, background: type === 'video' ? '#eff6ff' : '#f0fdf4', color: type === 'video' ? '#2563eb' : '#16a34a'}}>
        {type === 'video' ? <Clapperboard size={20} /> : <Music size={20} />}
      </div>
      <div style={{flex: 1, overflow: 'hidden'}}>
        <div style={{fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}} title={file.name}>{file.name}</div>
        <div style={{fontSize: '0.8em', color: '#6b7280'}}>{file.size} • {file.modified}</div>
      </div>
      <Button variant="ghost" size="small" onClick={() => openDeleteModal(type, file.name)} icon={Trash2} style={{color: '#ef4444'}} />
    </div>
  );

  if (loading) return <div style={{padding: 40, textAlign: 'center'}}>Načítavam médiá...</div>;

  return (
    <div className="tab-content active">
      <PageHeader title="Správca Médií" icon={Video} />
      
      <div className="media-grid-container" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px' }}>
          {/* VIDEO SECTION */}
          <Card title={`Video & Obrázky (${videos.length})`} icon={Video} actions={
              <Button size="small" variant="secondary" onClick={() => handleUpload('video')} icon={Upload}>Nahrať</Button>
          }>
              <div style={{display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 500, overflowY: 'auto'}}>
                 {videos.length > 0 ? videos.map(f => <FileItem key={f.name} file={f} type="video" />) : <div style={{padding: 20, textAlign: 'center', color: '#9ca3af'}}>Prázdne</div>}
              </div>
          </Card>

          {/* AUDIO SECTION */}
          <Card title={`Zvukové efekty (${audios.length})`} icon={Volume2} actions={
              <Button size="small" variant="secondary" onClick={() => handleUpload('audio')} icon={Upload}>Nahrať</Button>
          }>
               <div style={{display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 500, overflowY: 'auto'}}>
                 {audios.length > 0 ? audios.map(f => <FileItem key={f.name} file={f} type="audio" />) : <div style={{padding: 20, textAlign: 'center', color: '#9ca3af'}}>Prázdne</div>}
              </div>
          </Card>
      </div>

      <Modal 
        isOpen={deleteModal.isOpen} 
        title="Vymazať súbor?" 
        type="danger"
        onClose={closeDeleteModal}
        footer={
            <>
                <Button variant="secondary" onClick={closeDeleteModal}>Zrušiť</Button>
                <Button variant="danger" disabled={deleteModal.inputValue !== deleteModal.fileName} onClick={confirmDelete}>Vymazať súbor</Button>
            </>
        }
      >
        <p>Pre potvrdenie napíšte názov súboru: <strong>{deleteModal.fileName}</strong></p>
        <input 
            type="text" 
            className="form-control" 
            value={deleteModal.inputValue}
            onChange={(e) => setDeleteModal(prev => ({...prev, inputValue: e.target.value}))}
            style={{width: '100%', padding: '10px', marginTop: '10px', borderRadius: '6px', border: '1px solid #d1d5db'}}
            autoFocus
        />
      </Modal>
    </div>
  );
};

export default MediaManager;