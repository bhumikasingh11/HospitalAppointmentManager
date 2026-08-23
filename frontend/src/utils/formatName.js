export function formatDoctorName(name) {
  if (!name) return 'Doctor';
  const trimmed = name.trim();
  if (/^dr\.?/i.test(trimmed)) {
    return trimmed;
  }
  return `Dr. ${trimmed}`;
}
