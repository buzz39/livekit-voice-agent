import React, { useState, useEffect } from 'react';
import ReactCalendar from 'react-calendar';
import 'react-calendar/dist/Calendar.css';
import { Phone, Clock, CheckCircle, AlertCircle, Calendar as CalendarIcon } from 'lucide-react';
import { getAppointments } from '../../api';

const statusConfig = {
  pending: { label: 'Pending', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', icon: <Clock className="w-3 h-3" /> },
  confirmed: { label: 'Confirmed', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', icon: <CheckCircle className="w-3 h-3" /> },
  done: { label: 'Done', color: 'text-slate-400', bg: 'bg-slate-700/50 border-slate-600/20', icon: <CheckCircle className="w-3 h-3" /> },
};

const Calendar = () => {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAppointments = async () => {
      setLoading(true);
      try {
        const data = await getAppointments();
        setAppointments(data || []);
      } catch (err) {
        console.error('Failed to fetch appointments:', err);
        setAppointments([]);
      } finally {
        setLoading(false);
      }
    };
    fetchAppointments();
  }, []);

  // Get appointments for selected date
  const selectedDateStr = selectedDate.toISOString().split('T')[0];
  const dayAppointments = appointments.filter(a => a.date === selectedDateStr);

  // Dates that have appointments (for tile highlighting)
  const appointmentDates = new Set(appointments.map(a => a.date));

  const tileContent = ({ date, view }) => {
    if (view !== 'month') return null;
    const dateStr = date.toISOString().split('T')[0];
    if (appointmentDates.has(dateStr)) {
      return (
        <div className="flex justify-center mt-1">
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
        </div>
      );
    }
    return null;
  };

  return (
    <div className="h-full grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Calendar Widget */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-5">
          <CalendarIcon className="w-5 h-5 text-indigo-400" />
          <h2 className="text-lg font-semibold text-white">Appointment Calendar</h2>
        </div>
        <div className="react-calendar-dark">
          <ReactCalendar
            onChange={setSelectedDate}
            value={selectedDate}
            tileContent={tileContent}
            className="w-full !bg-transparent !border-none"
          />
        </div>
        <div className="mt-4 pt-4 border-t border-slate-800 text-sm text-slate-400">
          {appointments.length} total appointments · {appointmentDates.size} days with bookings
        </div>
      </div>

      {/* Appointments for selected date */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-white">
            {selectedDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
          </h2>
          <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded-full">
            {dayAppointments.length} appointment{dayAppointments.length !== 1 ? 's' : ''}
          </span>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
            Loading appointments...
          </div>
        ) : dayAppointments.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-3">
            <CalendarIcon className="w-10 h-10 text-slate-700" />
            <p className="text-sm">No appointments on this day</p>
          </div>
        ) : (
          <div className="space-y-3 overflow-y-auto flex-1">
            {dayAppointments.map((appt) => {
              const status = statusConfig[appt.status] || statusConfig.pending;
              return (
                <div key={appt.id} className="p-4 bg-slate-800 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div className="font-medium text-white">{appt.lead_name}</div>
                    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${status.bg} ${status.color}`}>
                      {status.icon}
                      {status.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-slate-400">
                    <div className="flex items-center gap-1.5">
                      <Phone className="w-3.5 h-3.5" />
                      {appt.phone}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      {appt.time}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* All upcoming appointments summary */}
      <div className="md:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">All Appointments</h2>
        {loading ? (
          <div className="text-slate-500 text-sm">Loading...</div>
        ) : appointments.length === 0 ? (
          <div className="text-slate-500 text-sm">No appointments found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-800">
                  <th className="text-left py-2 pr-4 font-medium">Lead Name</th>
                  <th className="text-left py-2 pr-4 font-medium">Phone</th>
                  <th className="text-left py-2 pr-4 font-medium">Date</th>
                  <th className="text-left py-2 pr-4 font-medium">Time</th>
                  <th className="text-left py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((appt) => {
                  const status = statusConfig[appt.status] || statusConfig.pending;
                  return (
                    <tr key={appt.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 pr-4 text-white font-medium">{appt.lead_name}</td>
                      <td className="py-3 pr-4 text-slate-400">{appt.phone}</td>
                      <td className="py-3 pr-4 text-slate-400">{appt.date}</td>
                      <td className="py-3 pr-4 text-slate-400">{appt.time}</td>
                      <td className="py-3">
                        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${status.bg} ${status.color}`}>
                          {status.icon}
                          {status.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Calendar;
