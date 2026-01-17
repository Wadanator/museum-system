export default function SceneProgressBar({ data }) {
    if (!data.visible) return null;

    return (
        <div className="scene-progress">
            <div className="progress-header">Prebieha scéna</div>
            <div className="progress-bar">
                <div 
                    className="progress-fill" 
                    style={{ width: `${data.progress}%` }}
                ></div>
            </div>
            <div className="progress-info">
                <span>{data.text}</span>
                <span>{data.info}</span>
            </div>
        </div>
    );
}