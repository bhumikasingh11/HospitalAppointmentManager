import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DoctorsPage from './pages/DoctorsPage';
import DoctorDetailPage from './pages/DoctorDetailPage';
import MyAppointmentsPage from './pages/MyAppointmentsPage';
import PatientProfilePage from './pages/PatientProfilePage';
import DoctorDashboardPage from './pages/DoctorDashboardPage';
import DoctorConsultationPage from './pages/DoctorConsultationPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import AdminAddDoctorPage from './pages/AdminAddDoctorPage';
import AdminEditDoctorPage from './pages/AdminEditDoctorPage';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Navbar />
        <Routes>
          <Route path="/" element={<Navigate to="/doctors" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/doctors" element={<DoctorsPage />} />
          <Route path="/doctors/:id" element={<DoctorDetailPage />} />
          
          {/* Patient Routes */}
          <Route element={<ProtectedRoute allowedRoles={['PATIENT', 'ADMIN']} />}>
            <Route path="/my-appointments" element={<MyAppointmentsPage />} />
            <Route path="/my-profile" element={<PatientProfilePage />} />
          </Route>

          {/* Doctor Routes */}
          <Route element={<ProtectedRoute allowedRoles={['DOCTOR', 'ADMIN']} />}>
            <Route path="/doctor/dashboard" element={<DoctorDashboardPage />} />
            <Route path="/doctor/appointments/:id" element={<DoctorConsultationPage />} />
          </Route>

          {/* Admin Routes */}
          <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
            <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
            <Route path="/admin/doctors/new" element={<AdminAddDoctorPage />} />
            <Route path="/admin/doctors/:id" element={<AdminEditDoctorPage />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
