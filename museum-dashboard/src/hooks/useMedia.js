import { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import { api } from '../services/api'; // Alebo authFetch, podľa toho čo používate

export const useMedia = () => {
    const [videos, setVideos] = useState([]);
    const [audios, setAudios] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [playingFile, setPlayingFile] = useState(null); // Pre vizuálny efekt

    // 1. Načítanie dát
    const fetchMedia = useCallback(async () => {
        try {
            setIsLoading(true);
            const [videoData, audioData] = await Promise.all([
                api.authFetch('/api/media/video').then(res => res.json()),
                api.authFetch('/api/media/audio').then(res => res.json())
            ]);
            setVideos(videoData || []);
            setAudios(audioData || []);
        } catch (error) {
            console.error(error);
            toast.error("Nepodarilo sa načítať médiá");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchMedia();
    }, [fetchMedia]);

    // 2. Upload
    const uploadMedia = async (type, file) => {
        const loadToast = toast.loading(`Nahrávam ${file.name}...`);
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const res = await api.authFetch(`/api/media/${type}`, {
                method: 'POST',
                body: formData
            });

            if (!res.ok) throw new Error("Upload failed");
            
            const data = await res.json();
            
            // Optimisticky update alebo refresh
            if (type === 'video') setVideos(prev => [...prev, data.file]);
            else setAudios(prev => [...prev, data.file]);
            
            toast.success("Súbor nahraný", { id: loadToast });
            return true;
        } catch (error) {
            toast.error("Chyba pri nahrávaní", { id: loadToast });
            return false;
        }
    };

    // 3. Delete
    const deleteMedia = async (type, filename) => {
        const loadToast = toast.loading(`Mažem ${filename}...`);
        try {
            const res = await api.authFetch(`/api/media/${type}/${filename}`, {
                method: 'DELETE'
            });

            if (!res.ok) throw new Error("Delete failed");

            // Update state
            if (type === 'video') setVideos(prev => prev.filter(v => v.name !== filename));
            else setAudios(prev => prev.filter(a => a.name !== filename));

            toast.success("Súbor vymazaný", { id: loadToast });
            return true;
        } catch (error) {
            toast.error("Chyba pri mazaní", { id: loadToast });
            return false;
        }
    };

    // 4. Play (Audio/Video)
    const playMediaFile = async (type, filename) => {
        try {
            setPlayingFile(filename); // UI efekt
            await api.playMedia(type, filename);
            toast.success(`Prehrávam: ${filename}`);
            
            // Reset vizuálneho stavu po 3 sekundách
            setTimeout(() => setPlayingFile(null), 3000);
        } catch (error) {
            toast.error("Chyba pri spustení prehrávania");
            setPlayingFile(null);
        }
    };

    // 5. Stop All
    const stopAllMedia = async () => {
        try {
            await api.stopAllMedia();
            toast.success("Prehrávanie zastavené");
            setPlayingFile(null);
        } catch (error) {
            toast.error("Chyba pri zastavovaní");
        }
    };

    return {
        videos,
        audios,
        isLoading,
        playingFile,
        fetchMedia,
        uploadMedia,
        deleteMedia,
        playMediaFile,
        stopAllMedia
    };
};