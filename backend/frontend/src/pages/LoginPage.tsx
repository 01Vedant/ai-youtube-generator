import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/state/auth';

type LoginPageProps = {
  onSuccess?: () => void;
};

const LoginPage: React.FC<LoginPageProps> = ({ onSuccess }) => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      if (typeof navigate === 'function') {
        navigate('/');
      } else if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    setEmail(e.target.value);
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    setPassword(e.target.value);
  };

  return (
    <div style={{ maxWidth: 420, margin: '2rem auto', padding: '0 1rem' }}>
      <h1 style={{ marginBottom: '1rem' }}>Login</h1>
      <form onSubmit={handleSubmit} noValidate>
        <div style={{ marginBottom: '0.75rem' }}>
          <label htmlFor="email" style={{ display: 'block', marginBottom: 4 }}>Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={handleEmailChange}
            required
            aria-invalid={error ? 'true' : 'false'}
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>

        <div style={{ marginBottom: '0.75rem' }}>
          <label htmlFor="password" style={{ display: 'block', marginBottom: 4 }}>Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={handlePasswordChange}
            required
            aria-invalid={error ? 'true' : 'false'}
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>

        {error && (
          <div role="alert" style={{ color: '#b00020', marginBottom: '0.75rem' }}>
            {error}
          </div>
        )}

        <button type="submit" disabled={loading} style={{ padding: '0.5rem 0.75rem' }}>
          {loading ? 'Logging in…' : 'Login'}
        </button>
      </form>
    </div>
  );
};

export default LoginPage;
