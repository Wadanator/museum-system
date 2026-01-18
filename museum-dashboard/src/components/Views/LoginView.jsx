import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Landmark, Lock, User } from 'lucide-react';
import Button from '../ui/Button'; 
import '../../styles/views/login-view.css'; // Import nového CSS

export default function LoginView() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    await login(username, password);
    setIsSubmitting(false);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-logo">
             <Landmark size={40} />
        </div>
        
        <h1 className="login-title">Museum Control</h1>
        <p className="login-subtitle">Prihláste sa pre prístup k ovládaniu</p>

        <form onSubmit={handleSubmit} className="login-form">
            <div className="input-group">
                <User size={18} className="input-icon" />
                <input 
                    type="text" 
                    placeholder="Používateľské meno" 
                    className="login-input"
                    value={username} 
                    onChange={e => setUsername(e.target.value)}
                />
            </div>

            <div className="input-group">
                <Lock size={18} className="input-icon" />
                <input 
                    type="password" 
                    placeholder="Heslo" 
                    className="login-input"
                    value={password} 
                    onChange={e => setPassword(e.target.value)}
                />
            </div>
            
            <Button 
                type="submit" 
                isLoading={isSubmitting} 
                size="large" 
                style={{ marginTop: 10, borderRadius: 12 }} // Inline style povolený pre špecifický override layoutu
            >
                Prihlásiť sa
            </Button>
        </form>
        
        <div className="login-footer">v1.0.0 &bull; Museum System</div>
      </div>
    </div>
  );
}