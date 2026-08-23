import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';

export default function PatientProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [saveErr, setSaveErr] = useState('');
  const [deactivating, setDeactivating] = useState(false);
  const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveMsg('');
    setSaveErr('');
    try {
      await api.patch('/api/auth/profile', { name, email });
      setSaveMsg('Profile updated successfully.');
    } catch (err) {
      setSaveErr(err.response?.data?.detail || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async () => {
    setDeactivating(true);
    try {
      await api.post('/api/auth/deactivate');
      logout();
      navigate('/login');
    } catch (err) {
      setSaveErr(err.response?.data?.detail || 'Failed to deactivate account.');
      setDeactivating(false);
      setShowDeactivateConfirm(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: 560, margin: '2rem auto' }}>
      <div className="page-header">
        <h2>My Profile</h2>
        <p>Update your personal information</p>
      </div>

      <div className="card" style={{ padding: '2rem' }}>
        <form onSubmit={handleSave}>
          <div className="form-group" style={{ marginBottom: '1.25rem' }}>
            <label className="form-label">Full Name</label>
            <input
              className="form-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={2}
            />
          </div>
          <div className="form-group" style={{ marginBottom: '1.5rem' }}>
            <label className="form-label">Email Address</label>
            <input
              className="form-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          {saveMsg && <div className="alert alert-success" style={{ marginBottom: '1rem' }}>{saveMsg}</div>}
          {saveErr && <div className="alert alert-error" style={{ marginBottom: '1rem' }}>{saveErr}</div>}
          <button className="btn btn-primary" type="submit" disabled={saving} style={{ width: '100%' }}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>

      <div className="card" style={{ padding: '1.5rem', marginTop: '1.5rem', border: '1px solid #ffc0cb' }}>
        <h4 style={{ color: '#c0392b', marginBottom: '0.5rem' }}>Deactivate Account</h4>
        <p style={{ color: '#555', fontSize: '0.9rem', marginBottom: '1rem' }}>
          Your appointment history and medical records will be <strong>preserved</strong>. You will not be able to log in until an administrator reactivates your account.
        </p>
        {!showDeactivateConfirm ? (
          <button
            className="btn btn-danger"
            onClick={() => setShowDeactivateConfirm(true)}
          >
            Deactivate My Account
          </button>
        ) : (
          <div style={{ background: '#fff5f5', borderRadius: 8, padding: '1rem' }}>
            <p style={{ color: '#c0392b', fontWeight: 600, marginBottom: '0.75rem' }}>
              Are you sure? This will log you out immediately.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                className="btn btn-danger"
                onClick={handleDeactivate}
                disabled={deactivating}
              >
                {deactivating ? 'Deactivating...' : 'Yes, Deactivate'}
              </button>
              <button
                className="btn btn-outline"
                onClick={() => setShowDeactivateConfirm(false)}
                disabled={deactivating}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
