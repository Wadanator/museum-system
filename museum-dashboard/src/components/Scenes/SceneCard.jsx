import { Play, Settings2, Clock, Clapperboard, Star } from 'lucide-react';
import Card from '../ui/Card';

export default function SceneCard({ scene, onPlay, onEdit }) {
    // Formát dátumu (pôvodná logika)
    const date = new Date(scene.modified * 1000).toLocaleDateString('sk-SK', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    });

    // Zvýraznenie hlavných scén
    const isFeatured = scene.name.toLowerCase().includes('intro') || scene.name.toLowerCase().includes('main');

    return (
        <Card className={`scene-card ${isFeatured ? 'featured' : ''}`}>
            
            {/* 1. Vrchný Cover */}
            <div className="scene-cover">
                {/* Tlačidlo Edit - Vpravo hore */}
                <button 
                    className="edit-btn-absolute" 
                    onClick={(e) => { e.stopPropagation(); onEdit(scene.name); }}
                    title="Upraviť scénu"
                >
                    <Settings2 size={18} />
                </button>
            </div>

            {/* 2. Plávajúca ikona (medzi vrchom a spodkom) */}
            <div className="scene-icon-float">
                {isFeatured ? <Star size={24} fill="currentColor" /> : <Clapperboard size={24} />}
            </div>

            {/* 3. Spodná časť (Body) */}
            <div className="scene-body">
                <div className="scene-info">
                    <h3 className="scene-name" title={scene.name}>
                        {scene.name.replace('.json', '')}
                    </h3>
                    <div className="scene-meta">
                        <Clock size={14} />
                        <span>{date}</span>
                    </div>
                </div>
            </div>

            {/* 4. Play Tlačidlo - Vpravo dole */}
            <button 
                className="play-fab" 
                onClick={(e) => { e.stopPropagation(); onPlay(scene.name); }}
                title="Spustiť scénu"
            >
                <Play size={20} fill="currentColor" style={{ marginLeft: 2 }} />
            </button>

        </Card>
    );
}