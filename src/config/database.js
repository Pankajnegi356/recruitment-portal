// Database Configuration - VM MySQL Connection
// Toggle USE_DATABASE to switch between DB and constants

// Read from environment or fallback to default
export const USE_DATABASE = import.meta.env.VITE_USE_DATABASE === 'true' || false;

export const DB_CONFIG = {
  host: import.meta.env.VITE_DB_HOST || '48.216.217.84',
  port: parseInt(import.meta.env.VITE_DB_PORT) || 3306,
  user: import.meta.env.VITE_DB_USER || 'appuser',
  password: import.meta.env.VITE_DB_PASSWORD || 'strongpassword',
  database: import.meta.env.VITE_DB_NAME || 'recruitment_portal',
  charset: 'utf8mb4',
  collation: 'utf8mb4_unicode_ci',
  // Connection pool settings
  connectionLimit: 10,
  acquireTimeout: 60000,
  timeout: 60000,
  reconnect: true
};

// MySQL connection setup (commented out until needed)
/*
import mysql from 'mysql2/promise';

let pool = null;

export const getConnection = async () => {
  if (!pool) {
    pool = mysql.createPool(DB_CONFIG);
  }
  return pool;
};

export const executeQuery = async (query, params = []) => {
  try {
    const connection = await getConnection();
    const [rows] = await connection.execute(query, params);
    return rows;
  } catch (error) {
    console.error('Database query error:', error);
    throw error;
  }
};

// Test connection
export const testConnection = async () => {
  try {
    const connection = await getConnection();
    const [rows] = await connection.execute('SELECT 1 as test');
    console.log('Database connection successful:', rows);
    return true;
  } catch (error) {
    console.error('Database connection failed:', error);
    return false;
  }
};
*/

// Status code mappings based on your backend system
export const STATUS_CODES = {
  REJECTED: 0,           // Failed or rejected candidates
  APPLIED: 1,            // Initial application  
  SHORTLISTED: 2,        // Passed initial screening
  PRE_SCREENING: 3,      // Pre-screening test stage
  TECHNICAL_INTERVIEW: 4, // Technical interview stage
  HIRED: 5               // Successfully hired
};

export const STATUS_LABELS = {
  0: 'Rejected',
  1: 'Applied',
  2: 'Shortlisted',
  3: 'Pre Screening Test',
  4: 'Technical Interview', 
  5: 'Hired'
};

export const getStatusLabel = (statusCode) => {
  return STATUS_LABELS[statusCode] || 'Unknown';
};

export const getStatusColor = (statusCode) => {
  switch (statusCode) {
    case 0: return 'bg-red-500 text-white';        // Rejected
    case 1: return 'bg-blue-500 text-white';       // Applied
    case 2: return 'bg-yellow-500 text-white';     // Shortlisted
    case 3: return 'bg-orange-500 text-white';     // Pre Screening Test
    case 4: return 'bg-purple-500 text-white';     // Technical Interview
    case 5: return 'bg-green-500 text-white';      // Hired
    default: return 'bg-gray-500 text-white';
  }
};
