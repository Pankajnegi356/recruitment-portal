// API Service Layer - Real backend connection

// Backend API base URL - using Vite proxy
const API_BASE_URL = '/api';

// HTTP request helper
const apiRequest = async (endpoint, options = {}) => {
  try {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log('Making API request to:', url);
    
    // Get token from localStorage
    const token = localStorage.getItem('auth_token');
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers
      },
      ...options
    };

    const response = await fetch(url, config);
    console.log('API response status:', response.status);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Request failed' }));
      console.error('API Error:', errorData);
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    console.log('API response data:', data);
    return data;
  } catch (error) {
    console.error(`API request failed for ${endpoint}:`, error);
    
    // If it's a connection error, provide fallback
    if (error.message.includes('fetch') || error.message.includes('NetworkError')) {
      console.warn('Backend connection failed, check if server is running on port 5000');
    }
    
    throw error;
  }
};

// =======================
// API FUNCTIONS
// =======================

// =============================
// CANDIDATES API
// =============================
export const getCandidates = async () => {
  return await apiRequest('/candidates');
};

export const getCandidateById = async (id) => {
  return await apiRequest(`/candidates/${id}`);
};

export const createCandidate = async (candidateData) => {
  return await apiRequest('/candidates', {
    method: 'POST',
    body: JSON.stringify(candidateData)
  });
};

export const updateCandidate = async (id, candidateData) => {
  return await apiRequest(`/candidates/${id}`, {
    method: 'PUT',
    body: JSON.stringify(candidateData)
  });
};

export const deleteCandidate = async (id) => {
  return await apiRequest(`/candidates/${id}`, {
    method: 'DELETE'
  });
};

// Submit resume for AI processing
export const submitCandidateResume = async (candidateData, resumeFile) => {
  const formData = new FormData();
  
  // Add candidate data
  Object.keys(candidateData).forEach(key => {
    if (candidateData[key] !== null && candidateData[key] !== undefined && candidateData[key] !== '') {
      formData.append(key, candidateData[key]);
    }
  });
  
  // Add resume file
  if (resumeFile) {
    formData.append('resume', resumeFile);
  }
  
  return await apiRequest('/submit-candidate-resume', {
    method: 'POST',
    headers: {}, // Don't set Content-Type, let browser handle it for FormData
    body: formData
  });
};

// =============================
// DEPARTMENTS API
// =============================
export const getDepartments = async () => {
  return await apiRequest('/departments');
};

export const getDepartmentById = async (id) => {
  return await apiRequest(`/departments/${id}`);
};

export const createDepartment = async (departmentData) => {
  return await apiRequest('/departments', {
    method: 'POST',
    body: JSON.stringify(departmentData)
  });
};

export const updateDepartment = async (id, departmentData) => {
  return await apiRequest(`/departments/${id}`, {
    method: 'PUT',
    body: JSON.stringify(departmentData)
  });
};

export const deleteDepartment = async (id) => {
  return await apiRequest(`/departments/${id}`, {
    method: 'DELETE'
  });
};

// =============================
// JOBS API
// =============================
export const getJobs = async () => {
  return await apiRequest('/jobs');
};

export const getJobById = async (id) => {
  return await apiRequest(`/jobs/${id}`);
};

export const createJob = async (jobData) => {
  return await apiRequest('/jobs', {
    method: 'POST',
    body: JSON.stringify(jobData)
  });
};

export const updateJob = async (id, jobData) => {
  return await apiRequest(`/jobs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(jobData)
  });
};

export const deleteJob = async (id) => {
  return await apiRequest(`/jobs/${id}`, {
    method: 'DELETE'
  });
};

export const getJobApplications = async (jobId) => {
  return await apiRequest(`/jobs/${jobId}/applications`);
};

// =============================
// APPLICATIONS API
// =============================
export const getApplications = async () => {
  return await apiRequest('/applications');
};

export const createApplication = async (applicationData) => {
  return await apiRequest('/applications', {
    method: 'POST',
    body: JSON.stringify(applicationData)
  });
};

export const updateApplication = async (id, applicationData) => {
  return await apiRequest(`/applications/${id}`, {
    method: 'PUT',
    body: JSON.stringify(applicationData)
  });
};

export const deleteApplication = async (id) => {
  return await apiRequest(`/applications/${id}`, {
    method: 'DELETE'
  });
};

// =============================
// INTERVIEWS API
// =============================
export const getInterviews = async () => {
  return await apiRequest('/interviews');
};

export const getInterviewById = async (id) => {
  return await apiRequest(`/interviews/${id}`);
};

export const createInterview = async (interviewData) => {
  return await apiRequest('/interviews', {
    method: 'POST',
    body: JSON.stringify(interviewData)
  });
};

export const updateInterview = async (id, interviewData) => {
  return await apiRequest(`/interviews/${id}`, {
    method: 'PUT',
    body: JSON.stringify(interviewData)
  });
};

export const deleteInterview = async (id) => {
  return await apiRequest(`/interviews/${id}`, {
    method: 'DELETE'
  });
};

// =============================
// INTERVIEW TESTS API
// =============================
export const getInterviewTests = async () => {
  return await apiRequest('/interview-tests');
};

// =============================
// DASHBOARD & STATS API
// =============================
export const getDashboardStats = async () => {
  return await apiRequest('/dashboard/stats');
};

export const getRecentActivity = async () => {
  return await apiRequest('/dashboard/recent-activity');
};

// =============================
// AUTH API
// =============================
export const login = async (credentials) => {
  return await apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials)
  });
};

export const register = async (userData) => {
  return await apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify(userData)
  });
};

export const getUsers = async () => {
  return await apiRequest('/auth/users');
};

// =============================
// SEARCH API
// =============================
export const searchCandidates = async (searchTerm) => {
  try {
    const candidates = await getCandidates();
    if (!searchTerm) return candidates;
    
    return candidates.filter(candidate => 
      candidate.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      candidate.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      candidate.position_applied?.toLowerCase().includes(searchTerm.toLowerCase())
    );
  } catch (error) {
    console.error('Search failed:', error);
    return [];
  }
};

// =============================
// ACTIVITY LOGS API
// =============================
export const getActivityLogs = async () => {
  return await apiRequest('/activity-logs');
};

export const getActivityLogById = async (id) => {
  return await apiRequest(`/activity-logs/${id}`);
};

export const createActivityLog = async (activityData) => {
  return await apiRequest('/activity-logs', {
    method: 'POST',
    body: JSON.stringify(activityData)
  });
};

export const updateActivityLog = async (id, activityData) => {
  return await apiRequest(`/activity-logs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(activityData)
  });
};

export const deleteActivityLog = async (id) => {
  return await apiRequest(`/activity-logs/${id}`, {
    method: 'DELETE'
  });
};

export const getUserActivityLogs = async (userId) => {
  return await apiRequest(`/activity-logs/user/${userId}`);
};

export const getEntityActivityLogs = async (entityType, entityId) => {
  return await apiRequest(`/activity-logs/entity/${entityType}/${entityId}`);
};

// Backward compatibility aliases for existing code
export const getTasks = getActivityLogs;
export const getTaskById = getActivityLogById;
export const createTask = createActivityLog;
export const updateTask = updateActivityLog;
export const deleteTask = deleteActivityLog;
export const getUserTasks = getUserActivityLogs;
