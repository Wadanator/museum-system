import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Landmark, Lock, User } from 'lucide-react';
import Button from '../ui/Button'; // Import Buttonu

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
    <div style={{
        height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'linear-gradient(135deg, #eef2f6, #cfd9df)'
    }}>
      <div style={{
          background: 'white', padding: '50px 40px', borderRadius: '24px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.08)', width: '100%', maxWidth: '420px',
          textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '10px'
      }}>
        <div style={{
            background: '#eff6ff', width: '80px', height: '80px', borderRadius: '50%', 
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 10px auto',
            color: '#2563eb'
        }}>
             <Landmark size={40} />
        </div>
        
        <h1 style={{fontSize: '2rem', fontWeight: 'bold', color: '#1f2937', margin: 0}}>Museum Control</h1>
        <p style={{color: '#6b7280', marginBottom: '20px'}}>Prihláste sa pre prístup k ovládaniu</p>

        <form onSubmit={handleSubmit} style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
            <div style={{position: 'relative'}}>
                <User size={18} style={{position: 'absolute', left: 15, top: 14, color: '#9ca3af'}} />
                <input type="text" placeholder="Používateľské meno" value={username} onChange={e => setUsername(e.target.value)}
                    style={{padding: '12px 12px 12px 40px', borderRadius: '12px', border: '1px solid #e5e7eb', width: '100%', outline: 'none'}} />
            </div>

            <div style={{position: 'relative'}}>
                <Lock size={18} style={{position: 'absolute', left: 15, top: 14, color: '#9ca3af'}} />
                <input type="password" placeholder="Heslo" value={password} onChange={e => setPassword(e.target.value)}
                    style={{padding: '12px 12px 12px 40px', borderRadius: '12px', border: '1px solid #e5e7eb', width: '100%', outline: 'none'}} />
            </div>
            
            <Button type="submit" isLoading={isSubmitting} size="large" style={{marginTop: 10, borderRadius: 12}}>
                Prihlásiť sa
            </Button>
        </form>
        
        <div style={{marginTop: '30px', fontSize: '0.8rem', color: '#9ca3af'}}>v1.0.0 &bull; Museum System</div>
      </div>
    </div>
  );
}