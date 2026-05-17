import { Play, Settings2, Clock, Clapperboard, Star, Wand2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Card from '../ui/Card';
import Button from '../ui/Button';

export default function SceneCard({ scene, onPlay, onEdit }) {
  const navigate = useNavigate();
    const date = new Date(scene.modified * 1000).toLocaleDateString('sk-SK', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    });

    const isFeatured = scene.name.toLowerCase().includes('intro') || scene.name.toLowerCase().includes('main');

    return (
        <Card className={`scene-card ${isFeatured ? 'featured' : ''}`}>
            
            <div className="scene-cover">
                <Button
                    variant="unstyled"
                    size="small"
                    className="edit-btn-absolute"
                    onClick={(e) => { e.stopPropagation(); onEdit(scene.name); }}
                    title="Upraviť scénu (JSON)"
                    aria-label="Upraviť scénu"
                    icon={Settings2}
                    cooldown={0}
                />
                <Button
                    variant="unstyled"
                    size="small"
                    className="edit-btn-absolute edit-btn-absolute--v2"
                    onClick={(e) => { e.stopPropagation(); navigate(`/scene-editor/${scene.name}`); }}
                    title="Otvoriť v SceneEditor V2"
                    aria-label="Otvoriť v SceneEditor V2"
                    icon={Wand2}
                    cooldown={0}
                />
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

            <Button
                variant="unstyled"
                size="small"
                className="play-fab" 
                onClick={(e) => { e.stopPropagation(); onPlay(scene.name); }}
                title="Spustiť scénu"
                aria-label="Spustiť scénu"
                icon={Play}
                cooldown={0}
            />

        </Card>
    );
}