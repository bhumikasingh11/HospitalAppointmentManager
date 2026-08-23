import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import DoctorCard from '../components/DoctorCard';

export default function DoctorsPage() {
  const [doctors, setDoctors] = useState([]);
  const [specialization, setSpecialization] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchDoctors = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (specialization) params.specialization = specialization;
      if (search) params.search = search;
      const res = await api.get('/api/doctors', { params });
      setDoctors(res.data);
    } catch (err) {
      setError('Failed to fetch doctors list.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoctors();
  }, [specialization]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchDoctors();
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Find a Doctor</h2>
        <p>Browse specialists and book your consultation slot</p>
      </div>

      <div className="filters-bar">
        <form onSubmit={handleSearchSubmit} className="search-form">
          <input
            type="text"
            placeholder="Search doctor name or specialty..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="btn btn-primary">Search</button>
        </form>

        <div className="filter-group">
          <label>Specialization:</label>
          <select 
            value={specialization} 
            onChange={(e) => setSpecialization(e.target.value)}
            className="filter-select"
          >
            <option value="">All Specialties</option>
            <option value="Cardiology">Cardiology</option>
            <option value="Dermatology">Dermatology</option>
            <option value="Pediatrics">Pediatrics</option>
            <option value="Orthopedics">Orthopedics</option>
            <option value="Neurology">Neurology</option>
            <option value="General Medicine">General Medicine</option>
          </select>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-spinner">Loading doctors...</div>
      ) : doctors.length === 0 ? (
        <p className="empty-state">No doctors found matching your criteria.</p>
      ) : (
        <div className="grid doctors-grid">
          {doctors.map((doctor) => (
            <DoctorCard key={doctor.id} doctor={doctor} />
          ))}
        </div>
      )}
    </div>
  );
}
