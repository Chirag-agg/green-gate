/**
 * LoadingSpinner — Beautiful animated loading indicator.
 */

export default function LoadingSpinner({ message = 'Loading...', size = 'md' }) {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
  };

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-12">
      <div className="relative">
        <div className={`${sizeClasses[size]} rounded-full border-4 border-primary-100 border-t-primary-500 animate-spin`} />
        <div className={`absolute inset-0 ${sizeClasses[size]} rounded-full border-4 border-transparent border-b-accent-400 animate-spin`} style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
      </div>
      <p className="text-sm text-gray-500 font-medium animate-pulse">{message}</p>
    </div>
  );
}
