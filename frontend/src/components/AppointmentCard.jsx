import React, { useState } from 'react';
import api from '../api/axios';

const APPT_RESPONSE_LABELS = {
  ATTEND: "✅ I'll attend",
  LATE: '⏳ I may be late',
  RESCHEDULE: '🔄 I need to reschedule',
};

const FOLLOWUP_LABELS = {
  BETTER: '😊 Better',
  SAME: '😐 About the same',
  NOT_IMPROVING: '😟 Not improving',
};

const ATTENDANCE_LABELS = {
  CLINIC: '🏥 I\'ll visit the clinic',
  RESCHEDULE: '🔄 I need to reschedule',
};

export default function AppointmentCard({ appointment, onUpdate }) {
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState('');
  const [updatingResponse, setUpdatingResponse] = useState(false);
  const [updatingFollowup, setUpdatingFollowup] = useState(false);
  const [updatingAttendance, setUpdatingAttendance] = useState(false);

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel this appointment?')) return;
    setCancelling(true);
    setError('');
    try {
      await api.post(`/api/appointments/${appointment.id}/cancel`);
      if (onUpdate) onUpdate();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to cancel appointment');
    } finally {
      setCancelling(false);
    }
  };

  const handleAppointmentResponse = async (response) => {
    setUpdatingResponse(true);
    setError('');
    try {
      await api.patch(`/api/appointments/${appointment.id}/response`, { response });
      if (onUpdate) onUpdate();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update response');
    } finally {
      setUpdatingResponse(false);
    }
  };

  const handleFollowUp = async (response) => {
    setUpdatingFollowup(true);
    setError('');
    try {
      await api.patch(`/api/appointments/${appointment.id}/followup`, { response });
      if (onUpdate) onUpdate();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update follow-up response');
    } finally {
      setUpdatingFollowup(false);
    }
  };

  const handleAttendance = async (method) => {
    setUpdatingAttendance(true);
    setError('');
    try {
      await api.patch(`/api/appointments/${appointment.id}/attendance`, { method });
      if (onUpdate) onUpdate();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update attendance method');
    } finally {
      setUpdatingAttendance(false);
    }
  };

  const statusColors = {
    BOOKED: 'badge-success',
    HELD: 'badge-warning',
    CANCELLED: 'badge-danger',
    COMPLETED: 'badge-info',
  };

  const isBooked = appointment.status === 'BOOKED';
  const isCompleted = appointment.status === 'COMPLETED';

  return (
    <div className="card appointment-card">
      <div className="card-header">
        <div>
          <h4>Appointment #{appointment.id}</h4>
          <p className="appointment-date">
            📅 {appointment.appointment_date} | ⏰ {appointment.start_time.slice(0, 5)} - {appointment.end_time.slice(0, 5)}
          </p>
        </div>
        <span className={`badge ${statusColors[appointment.status] || ''}`}>
          {appointment.status}
        </span>
      </div>

      <div className="card-body">
        {appointment.symptoms && (
          <p><strong>Symptoms:</strong> {appointment.symptoms}</p>
        )}
        {appointment.urgency && (
          <p><strong>Urgency:</strong> {appointment.urgency}</p>
        )}
        {appointment.pre_visit_summary && (
          <div className="summary-box">
            <strong>Pre-visit AI Summary:</strong>
            <p>{appointment.pre_visit_summary}</p>
          </div>
        )}
        {appointment.post_visit_notes && (
          <div className="notes-box">
            <strong>Doctor's Notes:</strong>
            <p>{appointment.post_visit_notes}</p>
          </div>
        )}
        {appointment.post_visit_summary && (
          <div className="summary-box">
            <strong>Patient Summary:</strong>
            <p>{appointment.post_visit_summary}</p>
          </div>
        )}

        {/* Appointment Response - BOOKED */}
        {isBooked && (
          <div className="response-section" style={{ marginTop: '1rem', padding: '0.85rem', background: '#f0fbf6', borderRadius: 8, border: '1px solid #b2dfdb' }}>
            <p style={{ fontWeight: 600, marginBottom: '0.5rem', color: '#087F5B' }}>Will you attend this appointment?</p>
            {appointment.appointment_response && (
              <p style={{ fontSize: '0.85rem', color: '#555', marginBottom: '0.5rem' }}>
                Current: <strong>{APPT_RESPONSE_LABELS[appointment.appointment_response] || appointment.appointment_response}</strong>
              </p>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {Object.entries(APPT_RESPONSE_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  className={`btn ${appointment.appointment_response === key ? 'btn-primary' : 'btn-outline'}`}
                  style={{ fontSize: '0.82rem', padding: '0.3rem 0.75rem' }}
                  onClick={() => handleAppointmentResponse(key)}
                  disabled={updatingResponse}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Attendance Method - BOOKED */}
        {isBooked && (
          <div className="response-section" style={{ marginTop: '0.75rem', padding: '0.85rem', background: '#f7fbff', borderRadius: 8, border: '1px solid #b3d1f7' }}>
            <p style={{ fontWeight: 600, marginBottom: '0.5rem', color: '#1565c0' }}>How will you attend?</p>
            {appointment.attendance_method && (
              <p style={{ fontSize: '0.85rem', color: '#555', marginBottom: '0.5rem' }}>
                Current: <strong>{ATTENDANCE_LABELS[appointment.attendance_method] || appointment.attendance_method}</strong>
              </p>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {Object.entries(ATTENDANCE_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  className={`btn ${appointment.attendance_method === key ? 'btn-primary' : 'btn-outline'}`}
                  style={{ fontSize: '0.82rem', padding: '0.3rem 0.75rem' }}
                  onClick={() => handleAttendance(key)}
                  disabled={updatingAttendance}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Follow-up Response - COMPLETED */}
        {isCompleted && (
          <div className="response-section" style={{ marginTop: '1rem', padding: '0.85rem', background: '#fafafa', borderRadius: 8, border: '1px solid #ddd' }}>
            <p style={{ fontWeight: 600, marginBottom: '0.5rem', color: '#333' }}>How are you doing after your visit?</p>
            {appointment.follow_up_response && (
              <p style={{ fontSize: '0.85rem', color: '#555', marginBottom: '0.5rem' }}>
                Current: <strong>{FOLLOWUP_LABELS[appointment.follow_up_response] || appointment.follow_up_response}</strong>
              </p>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {Object.entries(FOLLOWUP_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  className={`btn ${appointment.follow_up_response === key ? 'btn-primary' : 'btn-outline'}`}
                  style={{ fontSize: '0.82rem', padding: '0.3rem 0.75rem' }}
                  onClick={() => handleFollowUp(key)}
                  disabled={updatingFollowup}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && <div className="alert alert-error" style={{ marginTop: '0.75rem' }}>{error}</div>}
      </div>

      <div className="card-footer">
        {isBooked && (
          <button
            className="btn btn-danger"
            onClick={handleCancel}
            disabled={cancelling}
          >
            {cancelling ? 'Cancelling...' : 'Cancel Appointment'}
          </button>
        )}
      </div>
    </div>
  );
}
