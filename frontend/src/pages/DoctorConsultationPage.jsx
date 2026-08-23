import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/axios';

export default function DoctorConsultationPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [appointment, setAppointment] = useState(null);
  const [notes, setNotes] = useState('');
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form for adding a new prescription row
  const [newMed, setNewMed] = useState({
    medicine_name: '',
    dosage: '',
    frequency: 'Once daily',
    duration: '5 days',
    instructions: 'After meals'
  });

  const fetchAppointment = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/api/doctor/appointments/${id}`);
      setAppointment(res.data);
      if (res.data.post_visit_notes) {
        setNotes(res.data.post_visit_notes);
      }
      if (res.data.prescriptions && res.data.prescriptions.length > 0) {
        setPrescriptions(res.data.prescriptions);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load consultation details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointment();
  }, [id]);

  const handleAddPrescription = (e) => {
    e.preventDefault();
    if (!newMed.medicine_name || !newMed.dosage) {
      alert('Please fill Medicine Name and Dosage');
      return;
    }
    setPrescriptions([...prescriptions, { ...newMed }]);
    setNewMed({
      medicine_name: '',
      dosage: '',
      frequency: 'Once daily',
      duration: '5 days',
      instructions: 'After meals'
    });
  };

  const handleRemovePrescription = (index) => {
    setPrescriptions(prescriptions.filter((_, idx) => idx !== index));
  };

  const handleComplete = async (e) => {
    e.preventDefault();
    if (!notes.trim()) {
      setError('Please enter clinical notes before completing.');
      return;
    }

    setSubmitting(true);
    setError('');
    setSuccess('');

    try {
      const res = await api.post(`/api/doctor/appointments/${id}/complete`, {
        notes,
        prescriptions
      });
      setAppointment(res.data);
      setSuccess('Consultation completed and AI patient summary generated successfully!');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to complete consultation.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="loading-spinner">Loading consultation details...</div>;
  }

  if (!appointment) {
    return <div className="alert alert-error">{error || 'Appointment not found'}</div>;
  }

  const isCompleted = appointment.status === 'COMPLETED';

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Consultation: Appointment #{appointment.id}</h2>
          <p>Patient: <strong>{appointment.patient ? appointment.patient.name : 'Unknown'}</strong> | Date: <strong>{appointment.appointment_date} ({appointment.start_time.slice(0, 5)} - {appointment.end_time.slice(0, 5)})</strong></p>
        </div>
        <button className="btn btn-logout" onClick={() => navigate('/doctor/dashboard')}>
          ← Back to Dashboard
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="booking-grid">
        {/* Left column: Patient & AI Pre-visit summary */}
        <div className="card">
          <h3>Patient Information & AI Analysis</h3>
          <div style={{ marginTop: '1rem' }}>
            <p style={{ fontWeight: '600', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Reported Symptoms:</p>
            <p style={{ background: 'var(--bg)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', marginTop: '0.35rem', border: '1px solid var(--border)' }}>
              {appointment.symptoms || 'None reported'}
            </p>
          </div>

          <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontWeight: '600', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Urgency Level:</span>
            <span className={`badge ${appointment.urgency === 'High' ? 'badge-danger' : appointment.urgency === 'Medium' ? 'badge-warning' : 'badge-info'}`}>
              {appointment.urgency || 'Medium'}
            </span>
          </div>

          {appointment.pre_visit_summary && (
            <div className="summary-box" style={{ marginTop: '1.25rem' }}>
              <strong>AI Pre-Visit Assessment:</strong>
              <p style={{ whiteSpace: 'pre-line', marginTop: '0.5rem' }}>{appointment.pre_visit_summary}</p>
            </div>
          )}
        </div>

        {/* Right column: Clinical Notes & Prescriptions */}
        <div className="card">
          <h3>{isCompleted ? 'Completed Consultation Record' : 'Clinical Notes & Prescriptions'}</h3>

          <form onSubmit={handleComplete} style={{ marginTop: '1rem' }}>
            <div className="form-group">
              <label>Doctor's Clinical Notes / Diagnosis:</label>
              <textarea
                className="form-control"
                rows="5"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Enter diagnosis, examination findings, and clinical advice..."
                disabled={isCompleted}
                required
              />
            </div>

            <div className="form-group">
              <label>Prescribed Medications:</label>
              {prescriptions.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No prescriptions added yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
                  {prescriptions.map((p, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg)', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: '0.9rem' }}>
                      <div>
                        <strong style={{ color: 'var(--primary)' }}>{p.medicine_name}</strong> - {p.dosage} ({p.frequency}, {p.duration})
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{p.instructions}</div>
                      </div>
                      {!isCompleted && (
                        <button type="button" className="btn btn-danger" style={{ padding: '0.25rem 0.55rem', fontSize: '0.78rem' }} onClick={() => handleRemovePrescription(idx)}>
                          Remove
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {!isCompleted && (
                <div style={{ background: 'var(--bg)', padding: '1rem', borderRadius: 'var(--radius-sm)', marginTop: '0.75rem', border: '1px solid var(--border)' }}>
                  <h4 style={{ fontSize: '0.92rem', marginBottom: '0.65rem', color: 'var(--primary)' }}>+ Add Medication</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <input
                      type="text"
                      placeholder="Medicine Name (e.g. Amoxicillin)"
                      value={newMed.medicine_name}
                      onChange={(e) => setNewMed({ ...newMed, medicine_name: e.target.value })}
                    />
                    <input
                      type="text"
                      placeholder="Dosage (e.g. 500mg)"
                      value={newMed.dosage}
                      onChange={(e) => setNewMed({ ...newMed, dosage: e.target.value })}
                    />
                    <input
                      type="text"
                      placeholder="Frequency (e.g. Twice daily)"
                      value={newMed.frequency}
                      onChange={(e) => setNewMed({ ...newMed, frequency: e.target.value })}
                    />
                    <input
                      type="text"
                      placeholder="Duration (e.g. 7 days)"
                      value={newMed.duration}
                      onChange={(e) => setNewMed({ ...newMed, duration: e.target.value })}
                    />
                  </div>
                  <input
                    type="text"
                    placeholder="Instructions (e.g. Take after meals)"
                    value={newMed.instructions}
                    onChange={(e) => setNewMed({ ...newMed, instructions: e.target.value })}
                    style={{ marginBottom: '0.65rem' }}
                  />
                  <button type="button" className="btn btn-outline" style={{ fontSize: '0.85rem', padding: '0.45rem 0.9rem' }} onClick={handleAddPrescription}>
                    Add to Prescriptions
                  </button>
                </div>
              )}
            </div>

            {appointment.post_visit_summary && (
              <div className="summary-box" style={{ marginTop: '1.25rem', borderLeft: '4px solid var(--accent)' }}>
                <strong>✨ AI Patient-Friendly Summary:</strong>
                <p style={{ whiteSpace: 'pre-line', marginTop: '0.5rem' }}>{appointment.post_visit_summary}</p>
              </div>
            )}

            {!isCompleted && (
              <button
                type="submit"
                className="btn btn-primary btn-block"
                style={{ marginTop: '1.5rem' }}
                disabled={submitting}
              >
                {submitting ? 'Submitting & Generating AI Summary...' : 'Complete Consultation'}
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
