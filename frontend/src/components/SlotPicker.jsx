import React from 'react';

export default function SlotPicker({ slots, selectedSlot, onSelectSlot, loading }) {
  if (loading) {
    return <div className="loading-spinner">Loading available slots...</div>;
  }

  if (!slots || slots.length === 0) {
    return <p className="no-slots">No slots available for this date. Please select another date.</p>;
  }

  return (
    <div className="slots-grid">
      {slots.map((slot, idx) => {
        const isSelected = selectedSlot && selectedSlot.start_time === slot.start_time;
        return (
          <button
            key={idx}
            type="button"
            className={`slot-pill ${isSelected ? 'selected' : ''}`}
            onClick={() => onSelectSlot(slot)}
          >
            {slot.start_time.slice(0, 5)} - {slot.end_time.slice(0, 5)}
          </button>
        );
      })}
    </div>
  );
}
