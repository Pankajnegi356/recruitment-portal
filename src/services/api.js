// API Service Layer - Database queries with constants fallback
import { USE_DATABASE } from '../config/database.js';

// Commented out database imports - uncomment when VM is ready
/*
import { executeQuery } from '../config/database.js';
*/

// =======================
// CONSTANT DATA (Fallback when VM is off)
// =======================

const MOCK_CANDIDATES = [
  {
    id: 1,
    name: "Shikha Kumari",
    email: "shikhakumari@gmail.com",
    phone: "9876543210",
    summary: "Results-driven Quality Assurance (QA) professional with 8+ years of experience ensuring seamless delivery of high-quality software products across diverse domains. Holds a Master's degree in Computer Applications (Uttar Pradesh Technical University), along with a Master's degree in Technology (Abdul Kalam Technical University), demonstrating strong technical and analytical expertise. Proficient in Automation Testing (Selenium WebDriver), API & Manual Testing, Cross-browser compatibility testing, and Webservice testing (Postman). Skilled in designing and implementing automation frameworks including Data-Driven and Page Object Model (POM) approaches.\n\nProven track record of leading and delivering successful QA projects such as Neosys, Ovanza, JSHealth Vitamins, and Zapoi. Experienced in executing regression, smoke, and sanity testing, preparing test plans, logging and re-testing JIRA tickets, and providing daily/weekly test reports to stakeholders.",
    skill_match_score: 85.5,
    status: 2, // Shortlisted
    created_at: "2025-08-19T10:30:00",
    appliedFor: "Machine Learning Intern",
    handler: "Hr name",
    appliedDate: "2025-08-19"
  },
  {
    id: 2,
    name: "Amish Singh", 
    email: "amish.singh@gmail.com",
    phone: "9876543211",
    summary: "Passionate software developer with expertise in full-stack development and machine learning.",
    skill_match_score: 78.2,
    status: 1, // Applied
    created_at: "2025-08-19T14:20:00",
    appliedFor: "Machine Learning Intern",
    handler: "Hr name",
    appliedDate: "2025-08-19"
  },
  {
    id: 3,
    name: "Devanshi",
    email: "devanshi@gmail.com", 
    phone: "9876543212",
    summary: "Recent computer science graduate with strong programming fundamentals and internship experience.",
    skill_match_score: 72.8,
    status: 1, // Applied
    created_at: "2025-08-19T16:45:00",
    appliedFor: "Machine Learning Intern",
    handler: "Hr name",
    appliedDate: "2025-08-19"
  },
  {
    id: 4,
    name: "Rahul Sharma",
    email: "rahul.sharma@gmail.com",
    phone: "9876543213",
    summary: "Experienced frontend developer with expertise in React and modern web technologies.",
    skill_match_score: 88.5,
    status: 3, // Pre Screening Test
    created_at: "2025-08-18T12:15:00",
    appliedFor: "Full Stack Developer",
    handler: "Hr name",
    appliedDate: "2025-08-18"
  },
  {
    id: 5,
    name: "Priya Patel",
    email: "priya.patel@gmail.com",
    phone: "9876543214",
    summary: "Data scientist with 3+ years experience in machine learning and data analysis.",
    skill_match_score: 91.2,
    status: 4, // Technical Interview
    created_at: "2025-08-17T09:30:00",
    appliedFor: "Machine Learning Intern",
    handler: "Hr name",
    appliedDate: "2025-08-17"
  },
  {
    id: 6,
    name: "Arjun Kumar",
    email: "arjun.kumar@gmail.com",
    phone: "9876543215",
    summary: "Backend developer specializing in Node.js and cloud technologies.",
    skill_match_score: 79.8,
    status: 2, // Shortlisted
    created_at: "2025-08-18T15:45:00",
    appliedFor: "Full Stack Developer",
    handler: "Hr name",
    appliedDate: "2025-08-18"
  },
  {
    id: 7,
    name: "Sneha Gupta",
    email: "sneha.gupta@gmail.com",
    phone: "9876543216",
    summary: "UI/UX designer with strong technical background and programming skills.",
    skill_match_score: 82.1,
    status: 3, // Pre Screening Test
    created_at: "2025-08-17T11:20:00",
    appliedFor: "Full Stack Developer",
    handler: "Hr name",
    appliedDate: "2025-08-17"
  }
];

const MOCK_DEPARTMENTS = [
  {
    id: 1,
    name: "Artificial Intelligence",
    owner: "Mantish Sir",
    team: "Hr name", 
    created_at: "2025-08-19T20:38:00"
  },
  {
    id: 2,
    name: "Software Development",
    owner: "Pankaj Negi",
    team: "Dev Team",
    created_at: "2025-08-18T15:20:00"
  }
];

const MOCK_JOBS = [
  {
    id: 1,
    title: "Machine Learning Intern",
    department: "Artificial Intelligence",
    team: "Hr name",
    status: "Active", 
    created_at: "2025-08-19T09:00:00"
  },
  {
    id: 2,
    title: "Full Stack Developer",
    department: "Software Development", 
    team: "Dev Team",
    status: "Active",
    created_at: "2025-08-18T10:00:00"
  },
  {
    id: 3,
    title: "Data Scientist",
    department: "Artificial Intelligence",
    team: "Data Team",
    status: "Completed",
    created_at: "2025-08-17T14:00:00"
  },
  {
    id: 4,
    title: "Frontend Developer",
    department: "Software Development",
    team: "UI Team",
    status: "On Hold",
    created_at: "2025-08-16T11:30:00"
  },
  {
    id: 5,
    title: "DevOps Engineer",
    department: "Software Development",
    team: "Infrastructure Team",
    status: "Canceled",
    created_at: "2025-08-15T09:15:00"
  }
];

const MOCK_INTERVIEWS = [
  {
    id: 1,
    candidate_id: 1,
    candidate_email: "shikhakumari@gmail.com",
    interview_link: "https://meet.google.com/abc-def-ghi",
    interviewer_name: "AI Interviewer",
    status: 5 // Interview Confirmed
  }
];

const MOCK_INTERVIEW_TESTS = [
  {
    id: 1,
    candidate_id: 1,
    candidate_name: "Shikha Kumari",
    email: "shikhakumari@gmail.com",
    test_score: 22.5,
    status: 4, // Passed Test
    created_at: "2025-08-19T12:00:00"
  }
];

// =======================
// API FUNCTIONS
// =======================

// Candidates API
export const getCandidates = async () => {
  if (USE_DATABASE) {
    // Uncomment when VM is ready
    /*
    try {
      const query = 'SELECT * FROM candidates ORDER BY created_at DESC';
      return await executeQuery(query);
    } catch (error) {
      console.error('Failed to fetch candidates:', error);
      return [];
    }
    */
    return []; // Return empty for now when DB is enabled but commented
  } else {
    // Return mock data
    return MOCK_CANDIDATES;
  }
};

export const getCandidateById = async (id) => {
  if (USE_DATABASE) {
    /*
    try {
      const query = 'SELECT * FROM candidates WHERE id = ?';
      const results = await executeQuery(query, [id]);
      return results[0] || null;
    } catch (error) {
      console.error('Failed to fetch candidate:', error);
      return null;
    }
    */
    return null;
  } else {
    return MOCK_CANDIDATES.find(c => c.id === parseInt(id)) || null;
  }
};

// Departments API
export const getDepartments = async () => {
  if (USE_DATABASE) {
    /*
    try {
      const query = 'SELECT * FROM departments ORDER BY created_at DESC';
      return await executeQuery(query);
    } catch (error) {
      console.error('Failed to fetch departments:', error);
      return [];
    }
    */
    return [];
  } else {
    return MOCK_DEPARTMENTS;
  }
};

// Jobs API  
export const getJobs = async () => {
  if (USE_DATABASE) {
    /*
    try {
      const query = 'SELECT * FROM jobs ORDER BY created_at DESC';
      return await executeQuery(query);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      return [];
    }
    */
    return [];
  } else {
    return MOCK_JOBS;
  }
};

// Interviews API
export const getInterviews = async () => {
  if (USE_DATABASE) {
    /*
    try {
      const query = 'SELECT * FROM interviews ORDER BY id DESC';
      return await executeQuery(query);
    } catch (error) {
      console.error('Failed to fetch interviews:', error);
      return [];
    }
    */
    return [];
  } else {
    return MOCK_INTERVIEWS;
  }
};

// Interview Tests API
export const getInterviewTests = async () => {
  if (USE_DATABASE) {
    /*
    try {
      const query = 'SELECT * FROM interview_tests ORDER BY created_at DESC';
      return await executeQuery(query);
    } catch (error) {
      console.error('Failed to fetch interview tests:', error);
      return [];
    }
    */
    return [];
  } else {
    return MOCK_INTERVIEW_TESTS;
  }
};

// Dashboard Stats
export const getDashboardStats = async () => {
  const candidates = await getCandidates();
  const jobs = await getJobs();
  const interviews = await getInterviews();
  
  return {
    totalCandidates: candidates.length,
    totalJobs: jobs.length,
    totalInterviews: interviews.length,
    candidatesByStatus: {
      applied: candidates.filter(c => c.status === 1).length,
      shortlisted: candidates.filter(c => c.status === 2).length,
      assessment: candidates.filter(c => c.status === 3 || c.status === 4).length,
      interview: candidates.filter(c => c.status === 5).length
    }
  };
};

// Search candidates
export const searchCandidates = async (searchTerm) => {
  const candidates = await getCandidates();
  if (!searchTerm) return candidates;
  
  return candidates.filter(candidate => 
    candidate.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    candidate.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    candidate.appliedFor?.toLowerCase().includes(searchTerm.toLowerCase())
  );
};
