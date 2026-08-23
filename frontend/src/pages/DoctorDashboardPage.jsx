import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

export default function DoctorDashboardPage() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('ALL');
  const navigate = useNavigate();

  const fetchAppointments = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/api/doctor/appointments');
      setAppointments(res.data);
    } catch (err) {
      setError('Failed to fetch doctor appointments.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, []);

  const filteredAppointments = appointments.filter((appt) => {
    if (filter === 'ALL') return true;
    return appt.status === filter;
  });

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Doctor Dashboard</h2>
        <p>Manage your patient consultations and schedule</p>
      </div>

      <div className="filters-bar">
        <button 
          className={`btn ${filter === 'ALL' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setFilter('ALL')}
        >
          All ({appointments.length})
        </button>
        <button 
          className={`btn ${filter === 'BOOKED' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setFilter('BOOKED')}
        >
          Upcoming / Booked ({appointments.filter(a => a.status === 'BOOKED').length})
        </button>
        <button 
          className={`btn ${filter === 'COMPLETED' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setFilter('COMPLETED')}
        >
          Completed ({appointments.filter(a => a.status === 'COMPLETED').length})
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-spinner">Loading appointments...</div>
      ) : filteredAppointments.length === 0 ? (
        <div className="card empty-card">
          <p>No appointments found in this category.</p>
        </div>
      ) : (
        <div className="appointments-list">
          {filteredAppointments.map((appt) => (
            <div key={appt.id} className="card appointment-card">
              <div className="card-header">
                <div>
                  <h4>Patient: {appt.patient ? appt.patient.name : `Patient #${appt.patient_id}`}</h4>
                  <p className="appointment-date">
                    📅 {appt.appointment_date} | ⏰ {appt.start_time.slice(0, 5)} - {appt.end_time.slice(0, 5)}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  {appt.urgency && (
                    <span className={`badge ${appt.urgency === 'High' ? 'badge-danger' : appt.urgency === 'Medium' ? 'badge-warning' : 'badge-info'}`}>
                      Urgency: {appt.urgency}
                    </span>
                  )}
                  <span className={`badge ${appt.status === 'COMPLETED' ? 'badge-success' : 'badge-warning'}`}>
                    {appt.status}
                  </span>
                </div>
              </div>

              <div className="card-body">
                <p><strong>Reported Symptoms:</strong> {appt.symptoms || 'None provided'}</p>
                {appt.pre_visit_summary && (
                  <div className="summary-box">
                    <strong>AI Pre-visit Analysis:</strong>
                    <p style={{ whiteSpace: 'pre-line' }}>{appt.pre_visit_summary}</p>
                  </div>
                )}
              </div>

              <div className="card-footer">
                <button
                  className="btn btn-primary"
                  onClick={() => navigate(`/doctor/appointments/${appt.id}`)}
                >
                  {appt.status === 'COMPLETED' ? 'View Details' : 'Start Consultation'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
