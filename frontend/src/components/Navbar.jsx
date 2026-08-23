import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { formatDoctorName } from '../utils/formatName';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="navbar">
      <div className="nav-brand">
        <Link to="/">🏥 HospitalCare</Link>
      </div>
      <nav className="nav-links">
        {user?.role === 'ADMIN' ? (
          <>
            <Link to="/admin/dashboard">Admin Dashboard</Link>
            <Link to="/doctors">Patient View</Link>
            <span className="user-badge">Admin: {user.name}</span>
            <button onClick={handleLogout} className="btn-logout">Logout</button>
          </>
        ) : user?.role === 'DOCTOR' ? (
          <>
            <Link to="/doctor/dashboard">Doctor Dashboard</Link>
            <span className="user-badge">{formatDoctorName(user.name)}</span>
            <button onClick={handleLogout} className="btn-logout">Logout</button>
          </>
        ) : user ? (
          <>
            <Link to="/doctors">Find Doctors</Link>
            <Link to="/my-appointments">My Appointments</Link>
            <Link to="/my-profile">My Profile</Link>
            <span className="user-badge">{user.name}</span>
            <button onClick={handleLogout} className="btn-logout">Logout</button>
          </>
        ) : (
          <>
            <Link to="/doctors">Find Doctors</Link>
            <Link to="/login">Login</Link>
            <Link to="/register" className="btn-primary-link">Register</Link>
          </>
        )}
      </nav>
    </header>
  );
}
