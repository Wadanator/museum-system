import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';

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
        height: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #f3f4f6, #e5e7eb)'
    }}>
      <div style={{
          background: 'white',
          padding: '40px',
          borderRadius: '16px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
          width: '100%',
          maxWidth: '400px',
          textAlign: 'center'
      }}>
        <h1 style={{marginBottom: '20px', fontSize: '2rem'}}>🏛️ Login</h1>
        <form onSubmit={handleSubmit} style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
            <input 
                type="text" 
                placeholder="Meno (admin)" 
                value={username}
                onChange={e => setUsername(e.target.value)}
                style={{padding: '12px', borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '1rem'}}
            />
            <input 
                type="password" 
                placeholder="Heslo" 
                value={password}
                onChange={e => setPassword(e.target.value)}
                style={{padding: '12px', borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '1rem'}}
            />
            <button 
                type="submit" 
                disabled={isSubmitting}
                className="btn btn-primary"
                style={{padding: '12px', justifyContent: 'center', fontSize: '1rem'}}
            >
                {isSubmitting ? 'Overujem...' : 'Prihlásiť sa'}
            </button>
        </form>
      </div>
    </div>
  );
}