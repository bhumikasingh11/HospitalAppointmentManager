import React from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDoctorName } from '../utils/formatName';

export default function DoctorCard({ doctor }) {
  const navigate = useNavigate();

  return (
    <div className="card doctor-card">
      <div className="doctor-avatar">🩺</div>
      <div className="doctor-info">
        <h3>{doctor.user ? formatDoctorName(doctor.user.name) : `Doctor #${doctor.id}`}</h3>
        <p className="specialization">{doctor.specialization}</p>
        <p className="slot-duration">Slot duration: {doctor.slot_duration} mins</p>
      </div>
      <button 
        className="btn btn-primary"
        onClick={() => navigate(`/doctors/${doctor.id}`)}
      >
        View Slots & Book
      </button>
    </div>
  );
}
