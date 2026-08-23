import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { formatDoctorName } from '../utils/formatName';

export default function AdminDashboardPage() {
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const fetchDoctors = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/api/admin/doctors');
      setDoctors(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load doctors.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoctors();
  }, []);

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Admin Dashboard</h2>
          <p>Manage hospital doctors, schedules, slot durations, and leaves</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/admin/doctors/new')}>
          + Add New Doctor
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-spinner">Loading doctor records...</div>
      ) : (
        <div className="card">
          <h3>Doctor Management ({doctors.length})</h3>
          {doctors.length === 0 ? (
            <p style={{ marginTop: '1rem', color: '#64748b' }}>No doctors configured yet.</p>
          ) : (
            <div style={{ marginTop: '1rem', overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #e2e8f0', background: '#f8fafc' }}>
                    <th style={{ padding: '0.75rem' }}>ID</th>
                    <th style={{ padding: '0.75rem' }}>Doctor Name</th>
                    <th style={{ padding: '0.75rem' }}>Email</th>
                    <th style={{ padding: '0.75rem' }}>Specialization</th>
                    <th style={{ padding: '0.75rem' }}>Slot Duration</th>
                    <th style={{ padding: '0.75rem' }}>Working Days</th>
                    <th style={{ padding: '0.75rem' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {doctors.map((doc) => (
                    <tr key={doc.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={{ padding: '0.75rem' }}>#{doc.id}</td>
                      <td style={{ padding: '0.75rem', fontWeight: '500' }}>{doc.user ? formatDoctorName(doc.user.name) : `Doctor #${doc.id}`}</td>
                      <td style={{ padding: '0.75rem', color: '#64748b' }}>{doc.user ? doc.user.email : 'N/A'}</td>
                      <td style={{ padding: '0.75rem' }}><span className="badge badge-info">{doc.specialization}</span></td>
                      <td style={{ padding: '0.75rem' }}>{doc.slot_duration} mins</td>
                      <td style={{ padding: '0.75rem' }}>{doc.working_hours?.length || 0} configured</td>
                      <td style={{ padding: '0.75rem' }}>
                        <button
                          className="btn btn-outline"
                          style={{ padding: '0.3rem 0.75rem', fontSize: '0.85rem' }}
                          onClick={() => navigate(`/admin/doctors/${doc.id}`)}
                        >
                          Configure / Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
