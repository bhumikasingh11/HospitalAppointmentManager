import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/axios';
import SlotPicker from '../components/SlotPicker';
import { useAuth } from '../context/AuthContext';
import { formatDoctorName } from '../utils/formatName';

export default function DoctorDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [doctor, setDoctor] = useState(null);
  const [selectedDate, setSelectedDate] = useState(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
  });
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [symptoms, setSymptoms] = useState('');
  const [loadingDoc, setLoadingDoc] = useState(true);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [booking, setBooking] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Fetch doctor profile
  useEffect(() => {
    const fetchDoc = async () => {
      setLoadingDoc(true);
      try {
        const res = await api.get(`/api/doctors/${id}`);
        setDoctor(res.data);
      } catch (err) {
        setError('Doctor not found.');
      } finally {
        setLoadingDoc(false);
      }
    };
    fetchDoc();
  }, [id]);

  // Fetch slots whenever selectedDate or id changes
  const fetchSlots = async () => {
    if (!selectedDate) return;
    setLoadingSlots(true);
    setSelectedSlot(null);
    try {
      const res = await api.get(`/api/doctors/${id}/slots`, {
        params: { date: selectedDate }
      });
      const uniqueSlots = [];
      const seen = new Set();
      for (const slot of res.data || []) {
        if (!seen.has(slot.start_time)) {
          seen.add(slot.start_time);
          uniqueSlots.push(slot);
        }
      }
      setSlots(uniqueSlots);
    } catch (err) {
      setSlots([]);
    } finally {
      setLoadingSlots(false);
    }
  };

  useEffect(() => {
    fetchSlots();
  }, [id, selectedDate]);

  const handleBooking = async (e) => {
    e.preventDefault();
    if (!user) {
      navigate('/login');
      return;
    }
    if (!selectedSlot) {
      setError('Please select a time slot.');
      return;
    }

    setBooking(true);
    setError('');
    setSuccess('');

    try {
      await api.post('/api/appointments', {
        doctor_id: parseInt(id),
        appointment_date: selectedDate,
        start_time: selectedSlot.start_time,
        symptoms: symptoms
      });
      setSuccess('Appointment booked successfully!');
      setTimeout(() => {
        navigate('/my-appointments');
      }, 1200);
    } catch (err) {
      if (err.response && err.response.status === 409) {
        setError('Slot was just booked. Please select another.');
        // Refresh available slots
        fetchSlots();
      } else {
        setError(err.response?.data?.detail || 'Booking failed. Please try again.');
      }
    } finally {
      setBooking(false);
    }
  };

  if (loadingDoc) {
    return <div className="loading-spinner">Loading doctor profile...</div>;
  }

  if (!doctor) {
    return <div className="alert alert-error">Doctor could not be found.</div>;
  }

  return (
    <div className="page-container">
      <div className="card doctor-header-card">
        <div className="doctor-avatar-lg">🩺</div>
        <div>
          <h2>{doctor.user ? formatDoctorName(doctor.user.name) : `Doctor #${doctor.id}`}</h2>
          <p className="specialization-tag">{doctor.specialization}</p>
          <p>Consultation slot duration: <strong>{doctor.slot_duration} minutes</strong></p>
        </div>
      </div>

      <div className="booking-grid">
        <div className="card">
          <h3>1. Choose Appointment Date</h3>
          <input
            type="date"
            className="form-control"
            value={selectedDate}
            min={new Date().toISOString().split('T')[0]}
            onChange={(e) => setSelectedDate(e.target.value)}
          />

          <h3 style={{ marginTop: '1.5rem' }}>2. Select Time Slot</h3>
          <SlotPicker
            slots={slots}
            selectedSlot={selectedSlot}
            onSelectSlot={setSelectedSlot}
            loading={loadingSlots}
          />
        </div>

        <div className="card">
          <h3>3. Appointment Details</h3>
          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}

          <form onSubmit={handleBooking}>
            <div className="form-group">
              <label>Selected Time:</label>
              <div className="selected-slot-preview">
                {selectedSlot 
                  ? `📅 ${selectedDate} at ${selectedSlot.start_time.slice(0, 5)} - ${selectedSlot.end_time.slice(0, 5)}`
                  : 'No slot selected'}
              </div>
            </div>

            <div className="form-group">
              <label>Describe your symptoms or reason for visit:</label>
              <textarea
                className="form-control"
                rows="4"
                value={symptoms}
                onChange={(e) => setSymptoms(e.target.value)}
                placeholder="e.g. Mild headache and fatigue for 3 days..."
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={booking || !selectedSlot}
            >
              {booking ? 'Confirming Booking...' : 'Book Appointment'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
