import { Play, Settings2, Clock, Clapperboard, Star } from 'lucide-react';
import Card from '../ui/Card';

export default function SceneCard({ scene, onPlay, onEdit }) {
    const date = new Date(scene.modified * 1000).toLocaleDateString('sk-SK', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    });

    const isFeatured = scene.name.toLowerCase().includes('intro') || scene.name.toLowerCase().includes('main');

    return (
        <Card className={`scene-card ${isFeatured ? 'featured' : ''}`}>
            
            <div className="scene-cover">
                <button 
                    className="edit-btn-absolute" 
                    onClick={(e) => { e.stopPropagation(); onEdit(scene.name); }}
                    title="Upraviť scénu"
                >
                    <Settings2 size={18} />
                </button>
            </div>

            <div className="scene-icon-float">
                {isFeatured ? <Star size={24} fill="currentColor" /> : <Clapperboard size={24} />}
            </div>

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

            <button 
                className="play-fab" 
                onClick={(e) => { e.stopPropagation(); onPlay(scene.name); }}
                title="Spustiť scénu"
            >
                <Play size={20} fill="currentColor" />
            </button>

        </Card>
    );
}