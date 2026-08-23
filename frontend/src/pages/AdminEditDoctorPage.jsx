import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { formatDoctorName } from '../utils/formatName';

const DAYS = [
  { val: 0, label: 'Monday' },
  { val: 1, label: 'Tuesday' },
  { val: 2, label: 'Wednesday' },
  { val: 3, label: 'Thursday' },
  { val: 4, label: 'Friday' },
  { val: 5, label: 'Saturday' },
  { val: 6, label: 'Sunday' }
];

export default function AdminEditDoctorPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [doctor, setDoctor] = useState(null);
  const [specialization, setSpecialization] = useState('');
  const [slotDuration, setSlotDuration] = useState(30);

  // Working hour form
  const [dayOfWeek, setDayOfWeek] = useState(0);
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('17:00');

  // Leave form
  const [leaveDate, setLeaveDate] = useState('');
  const [leaveReason, setLeaveReason] = useState('');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchDoctor = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/api/doctors/${id}`);
      setDoctor(res.data);
      setSpecialization(res.data.specialization);
      setSlotDuration(res.data.slot_duration);
    } catch (err) {
      setError('Failed to load doctor profile.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoctor();
  }, [id]);

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const res = await api.put(`/api/admin/doctors/${id}`, {
        specialization,
        slot_duration: parseInt(slotDuration)
      });
      setDoctor(res.data);
      setSuccess('Doctor profile updated successfully.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update profile.');
    }
  };

  const handleAddWorkingHour = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await api.post(`/api/admin/doctors/${id}/working-hours`, {
        day_of_week: parseInt(dayOfWeek),
        start_time: startTime + ':00',
        end_time: endTime + ':00'
      });
      setSuccess('Working hours added successfully.');
      fetchDoctor();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add working hours.');
    }
  };

  const handleAddLeave = async (e) => {
    e.preventDefault();
    if (!leaveDate) return;
    if (!window.confirm('Adding this leave will automatically cancel all conflicting appointments and notify affected patients. Continue?')) {
      return;
    }

    setError('');
    setSuccess('');
    try {
      await api.post(`/api/admin/doctors/${id}/leaves`, {
        leave_date: leaveDate,
        reason: leaveReason || 'Doctor unavailable'
      });
      setSuccess('Doctor leave recorded! Conflicting appointments were cancelled and patients notified.');
      setLeaveDate('');
      setLeaveReason('');
      fetchDoctor();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to record leave.');
    }
  };

  if (loading) {
    return <div className="loading-spinner">Loading doctor details...</div>;
  }

  if (!doctor) {
    return <div className="alert alert-error">Doctor not found.</div>;
  }

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Configure Doctor: {doctor.user ? formatDoctorName(doctor.user.name) : `Doctor #${doctor.id}`}</h2>
          <p>Email: {doctor.user?.email} | Specialization: {doctor.specialization}</p>
        </div>
        <button className="btn btn-logout" onClick={() => navigate('/admin/dashboard')}>
          ← Back to Doctors
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="booking-grid">
        {/* Left Column: Profile & Working Hours */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="card">
            <h3>Doctor Profile</h3>
            <form onSubmit={handleUpdateProfile} style={{ marginTop: '1rem' }}>
              <div className="form-group">
                <label>Specialization</label>
                <input
                  type="text"
                  required
                  value={specialization}
                  onChange={(e) => setSpecialization(e.target.value)}
                />
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

              <button type="submit" className="btn btn-primary">Save Profile Changes</button>
            </form>
          </div>

          <div className="card">
            <h3>Working Hours Schedule</h3>
            {doctor.working_hours?.length > 0 ? (
              <div style={{ marginTop: '0.75rem', marginBottom: '1rem' }}>
                {doctor.working_hours.map((wh) => (
                  <div key={wh.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid #e2e8f0' }}>
                    <strong>{DAYS.find(d => d.val === wh.day_of_week)?.label}:</strong>
                    <span>{wh.start_time.slice(0, 5)} - {wh.end_time.slice(0, 5)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: '#64748b', margin: '0.75rem 0' }}>No working hours set yet.</p>
            )}

            <form onSubmit={handleAddWorkingHour} style={{ background: '#f8fafc', padding: '1rem', borderRadius: '6px' }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>+ Add Shift / Working Hours</h4>
              <div className="form-group">
                <label>Day of Week</label>
                <select value={dayOfWeek} onChange={(e) => setDayOfWeek(e.target.value)} className="form-control">
                  {DAYS.map(d => (
                    <option key={d.val} value={d.val}>{d.label}</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.85rem' }}>Start Time</label>
                  <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
                </div>
                <div>
                  <label style={{ fontSize: '0.85rem' }}>End Time</label>
                  <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} required />
                </div>
              </div>

              <button type="submit" className="btn btn-primary" style={{ fontSize: '0.85rem' }}>Add Working Hours</button>
            </form>
          </div>
        </div>

        {/* Right Column: Doctor Leaves & Conflict Handler */}
        <div className="card">
          <h3>Doctor Leaves & Conflict Protection</h3>
          <p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            Setting a leave automatically cancels any existing booked appointments on that date and sends notifications to patients.
          </p>

          <form onSubmit={handleAddLeave} style={{ marginTop: '1.25rem', background: '#fef2f2', padding: '1rem', borderRadius: '6px', border: '1px solid #fecaca' }}>
            <h4 style={{ fontSize: '0.9rem', marginBottom: '0.75rem', color: '#991b1b' }}>Record Doctor Leave</h4>
            
            <div className="form-group">
              <label>Leave Date</label>
              <input
                type="date"
                required
                min={new Date().toISOString().split('T')[0]}
                value={leaveDate}
                onChange={(e) => setLeaveDate(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Reason / Note</label>
              <input
                type="text"
                placeholder="e.g. Medical Conference / Personal Leave"
                value={leaveReason}
                onChange={(e) => setLeaveReason(e.target.value)}
              />
            </div>

            <button type="submit" className="btn btn-danger btn-block">
              Apply Leave & Resolve Conflicts
            </button>
          </form>

          <div style={{ marginTop: '1.5rem' }}>
            <h4>Recorded Leaves ({doctor.leaves?.length || 0})</h4>
            {doctor.leaves?.length > 0 ? (
              <div style={{ marginTop: '0.75rem' }}>
                {doctor.leaves.map((l) => (
                  <div key={l.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0.75rem', background: '#f8fafc', borderRadius: '4px', marginBottom: '0.5rem', border: '1px solid #e2e8f0' }}>
                    <span>📅 <strong>{l.leave_date}</strong></span>
                    <span style={{ color: '#64748b' }}>{l.reason || 'Leave'}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: '#64748b', marginTop: '0.5rem', fontSize: '0.9rem' }}>No leaves recorded.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
