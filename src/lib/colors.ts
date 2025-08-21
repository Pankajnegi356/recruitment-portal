// Color utility functions for consistent blue theme usage
export const colorUtils = {
  // Status colors for recruitment stages
  status: {
    applied: 'bg-blue-100 text-blue-800 border-blue-200',
    shortlisted: 'bg-blue-500 text-white',
    screening: 'bg-blue-600 text-white',
    interview: 'bg-blue-700 text-white',
    hired: 'bg-green-500 text-white',
    rejected: 'bg-red-500 text-white',
    default: 'bg-gray-100 text-gray-800'
  },

  // Avatar colors using blue palette
  avatar: [
    'bg-blue-500',
    'bg-blue-600',
    'bg-blue-700',
    'bg-indigo-500',
    'bg-indigo-600',
    'bg-sky-500',
    'bg-sky-600'
  ],

  // Priority/importance levels
  priority: {
    high: 'bg-blue-700 text-white',
    medium: 'bg-blue-500 text-white',
    low: 'bg-blue-300 text-blue-900',
    info: 'bg-blue-100 text-blue-800'
  },

  // Interactive states
  interactive: {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-blue-100 hover:bg-blue-200 text-blue-800',
    ghost: 'hover:bg-blue-50 text-blue-600'
  }
};

// Helper function to get status color
export const getStatusColor = (status: string | number): string => {
  const statusMap: Record<string | number, string> = {
    1: colorUtils.status.applied,
    2: colorUtils.status.shortlisted,
    3: colorUtils.status.screening,
    4: colorUtils.status.interview,
    'applied': colorUtils.status.applied,
    'shortlisted': colorUtils.status.shortlisted,
    'screening': colorUtils.status.screening,
    'interview': colorUtils.status.interview,
    'hired': colorUtils.status.hired,
    'rejected': colorUtils.status.rejected
  };
  
  return statusMap[status] || colorUtils.status.default;
};

// Helper function to get avatar color based on name
export const getAvatarColor = (name: string): string => {
  const index = name.charCodeAt(0) % colorUtils.avatar.length;
  return colorUtils.avatar[index];
};

// Helper function to get priority color
export const getPriorityColor = (priority: 'high' | 'medium' | 'low' | 'info'): string => {
  return colorUtils.priority[priority] || colorUtils.priority.info;
};
