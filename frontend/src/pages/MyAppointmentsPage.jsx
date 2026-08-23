import React, { useState } from 'react';
import api from '../api/axios';
import AppointmentCard from '../components/AppointmentCard';
import { useEffect } from 'react';

const EMERGENCY_MESSAGE = `⚠️ EMERGENCY NOTICE

If you or someone near you is experiencing a life-threatening situation — such as chest pain, difficulty breathing, loss of consciousness, severe bleeding, stroke symptoms, or any other serious emergency — DO NOT wait.

Call your local emergency number immediately (e.g. 112 or 911).

This app is NOT an emergency service. Always seek immediate in-person medical care for emergencies.`;

export default function MyAppointmentsPage() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showEmergency, setShowEmergency] = useState(false);

  const fetchAppointments = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/api/appointments/my');
      setAppointments(res.data);
    } catch (err) {
      setError('Failed to load appointments.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, []);

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2>My Appointments</h2>
          <p>View your scheduled and past appointments</p>
        </div>
        <button
          className="btn"
          style={{
            background: '#c0392b',
            color: '#fff',
            border: 'none',
            fontWeight: 700,
            fontSize: '0.95rem',
            padding: '0.6rem 1.25rem',
            borderRadius: 8,
            cursor: 'pointer',
          }}
          onClick={() => setShowEmergency(true)}
        >
          🚨 Emergency Assistance
        </button>
      </div>

      {/* Emergency modal */}
      {showEmergency && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
          onClick={() => setShowEmergency(false)}
        >
          <div
            style={{
              background: '#fff', borderRadius: 12, padding: '2rem', maxWidth: 480, width: '90%',
              boxShadow: '0 8px 32px rgba(0,0,0,0.25)', border: '2px solid #c0392b',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ color: '#c0392b', marginBottom: '1rem' }}>🚨 Emergency Assistance</h3>
            <div
              style={{
                background: '#fff5f5', border: '1px solid #f5c6c6', borderRadius: 8,
                padding: '1rem', whiteSpace: 'pre-line', fontSize: '0.95rem',
                color: '#333', lineHeight: 1.65,
              }}
            >
              {EMERGENCY_MESSAGE}
            </div>
            <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-outline"
                onClick={() => setShowEmergency(false)}
                style={{ borderColor: '#c0392b', color: '#c0392b' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-spinner">Loading appointments...</div>
      ) : appointments.length === 0 ? (
        <div className="card empty-card">
          <p>You have no appointments yet.</p>
        </div>
      ) : (
        <div className="appointments-list">
          {appointments.map((appt) => (
            <AppointmentCard
              key={appt.id}
              appointment={appt}
              onUpdate={fetchAppointments}
            />
          ))}
        </div>
      )}
    </div>
  );
}
