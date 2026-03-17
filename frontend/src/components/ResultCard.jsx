/**
 * ResultCard — Displays a single metric with icon, value, and label.
 */

export default function ResultCard({ icon: Icon, label, value, subtext, color = 'primary', className = '' }) {
  const colorClasses = {
    primary: 'text-primary-700 bg-primary-100',
    accent: 'text-surface-700 bg-surface-200',
    red: 'text-red-700 bg-red-100',
    green: 'text-green-700 bg-green-100',
    blue: 'text-blue-700 bg-blue-100',
  };

  const colors = colorClasses[color] || colorClasses.primary;

  return (
    <div className={`card-glass p-8 group hover:-translate-y-1 transition-transform duration-300 ${className}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-bold text-surface-500 uppercase tracking-widest mb-3">{label}</p>
          <p className="text-4xl font-extrabold text-surface-900 tracking-tight">{value}</p>
          {subtext && <p className="text-sm font-semibold text-surface-500 mt-2">{subtext}</p>}
        </div>
        {Icon && (
          <div className={`w-14 h-14 rounded-2xl ${colors} flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform duration-300`}>
            <Icon className="w-7 h-7" />
          </div>
        )}
      </div>
    </div>
  );
}
