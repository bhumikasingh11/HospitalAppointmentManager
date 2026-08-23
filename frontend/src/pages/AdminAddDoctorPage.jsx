import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

export default function AdminAddDoctorPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [specialization, setSpecialization] = useState('General Medicine');
  const [slotDuration, setSlotDuration] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Create doctor user account & profile via admin endpoint
      const docRes = await api.post('/api/admin/doctors', {
        name,
        email,
        password,
        specialization,
        slot_duration: parseInt(slotDuration)
      });

      // Redirect to configure doctor's working hours
      navigate(`/admin/doctors/${docRes.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create doctor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: '600px' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Add New Doctor</h2>
          <p>Register a doctor account and initialize their profile</p>
        </div>
        <button className="btn btn-logout" onClick={() => navigate('/admin/dashboard')}>
          ← Back
        </button>
      </div>

      <div className="card">
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Doctor Full Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Dr. Gregory House"
            />
          </div>

          <div className="form-group">
            <label>Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="doctor@hospital.com"
            />
          </div>

          <div className="form-group">
            <label>Temporary Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <div className="form-group">
            <label>Specialization</label>
            <select
              value={specialization}
              onChange={(e) => setSpecialization(e.target.value)}
              className="form-control"
            >
              <option value="General Medicine">General Medicine</option>
              <option value="Cardiology">Cardiology</option>
              <option value="Dermatology">Dermatology</option>
              <option value="Pediatrics">Pediatrics</option>
              <option value="Orthopedics">Orthopedics</option>
              <option value="Neurology">Neurology</option>
              <option value="Psychiatry">Psychiatry</option>
            </select>
          </div>

          <div className="form-group">
            <label>Slot Duration (minutes)</label>
            <input
              type="number"
              min="10"
              max="120"
              step="5"
              required
              value={slotDuration}
              onChange={(e) => setSlotDuration(e.target.value)}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Creating Doctor...' : 'Save & Configure Schedule'}
          </button>
        </form>
      </div>
    </div>
  );
}
