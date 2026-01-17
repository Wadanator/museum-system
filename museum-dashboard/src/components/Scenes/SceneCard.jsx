import { Play, Edit, Clock, FileJson } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';

export default function SceneCard({ scene, onPlay, onEdit }) {
    // Formát dátumu
    const date = new Date(scene.modified * 1000).toLocaleDateString('sk-SK', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
    });

    return (
        <Card className="scene-card">
            <div className="scene-header">
                <div className="scene-icon">
                    <FileJson size={28} className="text-primary" />
                </div>
                <div className="scene-info">
                    <h3 className="scene-title">{scene.name}</h3>
                    <span className="scene-meta">
                        <Clock size={12} style={{ marginRight: 4 }} /> 
                        {date}
                    </span>
                </div>
            </div>

            <div className="scene-actions">
                <ButtonGroup>
                    <Button 
                        onClick={() => onPlay(scene.name)} 
                        variant="success" 
                        icon={Play}
                        style={{ flex: 1 }}
                    >
                        Spustiť
                    </Button>
                    <Button 
                        onClick={() => onEdit(scene.name)} 
                        variant="secondary" 
                        icon={Edit}
                    >
                        Upraviť
                    </Button>
                </ButtonGroup>
            </div>
        </Card>
    );
}