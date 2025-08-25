const express = require('express');
const { pool } = require('../config/database');
const router = express.Router();

// GET /api/dashboard/stats - Get dashboard statistics
router.get('/stats', async (req, res) => {
  try {
    // Get basic counts - these will return 0 for empty tables
    const [candidates] = await pool.execute('SELECT COUNT(*) as count FROM candidates');
    const [jobs] = await pool.execute('SELECT COUNT(*) as count FROM jobs');
    const [interviews] = await pool.execute('SELECT COUNT(*) as count FROM interviews');
    const [departments] = await pool.execute('SELECT COUNT(*) as count FROM departments');
    
    // Get pending interviews count (status 4 and 5)
    const [pendingInterviews] = await pool.execute('SELECT COUNT(*) as count FROM candidates WHERE status IN (4, 5)');

    // Initialize default values for empty database
    let candidatesByStatus = [{
      rejected: 0,
      applied: 0,
      shortlisted: 0,
      assessment: 0,
      interview: 0,
      hired: 0
    }];

    let jobsByStatus = [];

    // Only query if there are candidates
    if (candidates[0].count > 0) {
      const [candidatesStatus] = await pool.execute(`
        SELECT 
          SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) as rejected,
          SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as applied,
          SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) as shortlisted,
          SUM(CASE WHEN status = 3 THEN 1 ELSE 0 END) as assessment,
          SUM(CASE WHEN status >= 4 THEN 1 ELSE 0 END) as interview,
          SUM(CASE WHEN status = 6 THEN 1 ELSE 0 END) as hired
        FROM candidates
      `);
      candidatesByStatus = candidatesStatus;
    }

    // Only query if there are jobs
    if (jobs[0].count > 0) {
      const [jobsStatus] = await pool.execute(`
        SELECT status, COUNT(*) as count
        FROM jobs
        GROUP BY status
      `);
      jobsByStatus = jobsStatus;
    }

    // Get recent activity (last 30 days)
    const [recentCandidates] = await pool.execute(`
      SELECT COUNT(*) as count
      FROM candidates
      WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    `);

    const [recentJobs] = await pool.execute(`
      SELECT COUNT(*) as count
      FROM jobs
      WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    `);

    // Get application trends (last 14 days)
    const [applicationTrends] = await pool.execute(`
      SELECT DATE(created_at) as date, COUNT(*) as applications
      FROM candidates
      WHERE created_at >= DATE_SUB(NOW(), INTERVAL 14 DAY)
      GROUP BY DATE(created_at)
      ORDER BY date ASC
    `);

    // Get department-wise hiring
    const [departmentHiring] = await pool.execute(`
      SELECT d.name as department, COUNT(c.id) as hires
      FROM departments d
      LEFT JOIN candidates c ON d.id = c.department_id AND c.status = 6
      GROUP BY d.id, d.name
      ORDER BY hires DESC
    `);

    const stats = {
      totalCandidates: candidates[0].count,
      totalJobs: jobs[0].count,
      totalInterviews: interviews[0].count,
      pendingInterviews: pendingInterviews[0].count,
      totalDepartments: departments[0].count,
      candidatesByStatus: candidatesByStatus[0],
      jobsByStatus: jobsByStatus.reduce((acc, job) => {
        acc[job.status] = job.count;
        return acc;
      }, {}),
      recentCandidates: recentCandidates[0].count,
      recentJobs: recentJobs[0].count,
      applicationTrends,
      departmentHiring
    };

    res.json(stats);
  } catch (error) {
    console.error('Error fetching dashboard stats:', error);
    res.status(500).json({ error: 'Failed to fetch dashboard statistics' });
  }
});

// GET /api/dashboard/recent-activity - Get recent activities
router.get('/recent-activity', async (req, res) => {
  try {
    const [activities] = await pool.execute(`
      (SELECT 'candidate' as type, id, name as title, created_at as timestamp, 'New candidate added' as description
       FROM candidates 
       ORDER BY created_at DESC LIMIT 5)
      UNION ALL
      (SELECT 'job' as type, id, title, created_at as timestamp, 'New job posted' as description
       FROM jobs 
       ORDER BY created_at DESC LIMIT 5)
      UNION ALL
      (SELECT 'interview' as type, id, CONCAT('Interview for candidate ', candidate_id) as title, 
       created_at as timestamp, 'Interview scheduled' as description
       FROM interviews 
       ORDER BY created_at DESC LIMIT 5)
      ORDER BY timestamp DESC
      LIMIT 10
    `);

    res.json(activities);
  } catch (error) {
    console.error('Error fetching recent activity:', error);
    res.status(500).json({ error: 'Failed to fetch recent activity' });
  }
});

module.exports = router;
