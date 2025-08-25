const express = require('express');
const { pool } = require('../config/database');
const { authenticateToken } = require('../middleware/auth');
const router = express.Router();

// Helper function to generate unique application code
function generateApplicationCode(title) {
  // Create a clean code from job title
  const cleanTitle = title
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, '') // Remove special characters
    .replace(/\s+/g, '-') // Replace spaces with hyphens
    .substring(0, 20); // Limit length
  
  // Add timestamp for uniqueness
  const timestamp = Date.now().toString().slice(-4);
  return `${cleanTitle}-${timestamp}`;
}

// GET /api/jobs - Get all jobs
router.get('/', async (req, res) => {
  try {
    // Check if jobs table has any data
    const [jobCount] = await pool.execute('SELECT COUNT(*) as count FROM jobs');
    
    if (jobCount[0].count === 0) {
      return res.json([]);
    }

    const [rows] = await pool.execute(`
      SELECT j.*, 
             COALESCE(d.name, 'No Department') as department_name, 
             COALESCE(u.first_name, 'Unknown') as first_name, 
             COALESCE(u.last_name, 'User') as last_name,
             COUNT(ja.id) as applications_count
      FROM jobs j
      LEFT JOIN departments d ON j.department_id = d.id
      LEFT JOIN users u ON j.posted_by = u.id
      LEFT JOIN job_applications ja ON j.id = ja.job_id
      GROUP BY j.id
      ORDER BY j.created_at DESC
    `);
    
    // Add application links to all jobs
    const jobsWithLinks = rows.map(job => {
      const applicationCode = generateApplicationCode(job.title);
      const applicationUrl = `/apply/${applicationCode}`;
      return {
        ...job,
        posted_by_name: job.first_name ? `${job.first_name} ${job.last_name}` : 'Unknown',
        application_url: applicationUrl,
        application_code: applicationCode,
        public_link: `http://localhost:8080${applicationUrl}`
      };
    });
    
    res.json(jobsWithLinks);
  } catch (error) {
    console.error('Error fetching jobs:', error);
    res.status(500).json({ error: 'Failed to fetch jobs' });
  }
});

// GET /api/jobs/:id - Get single job
router.get('/:id', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT j.*, d.name as department_name, u.first_name, u.last_name,
             COUNT(ja.id) as applications_count
      FROM jobs j
      LEFT JOIN departments d ON j.department_id = d.id
      LEFT JOIN users u ON j.posted_by = u.id
      LEFT JOIN job_applications ja ON j.id = ja.job_id
      WHERE j.id = ?
      GROUP BY j.id
    `, [req.params.id]);
    
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Job not found' });
    }
    
    const job = rows[0];
    res.json({
      ...job,
      posted_by_name: job.first_name ? `${job.first_name} ${job.last_name}` : 'Unknown'
    });
  } catch (error) {
    console.error('Error fetching job:', error);
    res.status(500).json({ error: 'Failed to fetch job' });
  }
});

// POST /api/jobs - Create new job (requires authentication)
router.post('/', authenticateToken, async (req, res) => {
  try {
    const {
      title, description, department_id, requirements, salary_min, salary_max,
      location, employment_type, experience_level, skills_required, status
    } = req.body;
    
    if (!title) {
      return res.status(400).json({ error: 'Job title is required' });
    }
    
    // Generate unique application code and URL
    const applicationCode = generateApplicationCode(title);
    const applicationUrl = `/apply/${applicationCode}`;
    const linkCreatedAt = new Date();
    
    // Insert job with application link fields (when DB is updated)
    // Use the authenticated user's ID as posted_by
    const [result] = await pool.execute(`
      INSERT INTO jobs (title, description, department_id, requirements, salary_min, 
                       salary_max, location, employment_type, experience_level, status, posted_by)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [title, description, department_id, requirements, salary_min, salary_max,
        location, employment_type || 'full-time', experience_level || 'mid', 
        status || 'draft', req.user.id]); // Using authenticated user's ID
    
    console.log(`Generated application link: ${applicationUrl} (Code: ${applicationCode})`);
    
    // Fetch the created job
    const [newJob] = await pool.execute(`
      SELECT j.*, d.name as department_name, u.first_name, u.last_name
      FROM jobs j
      LEFT JOIN departments d ON j.department_id = d.id
      LEFT JOIN users u ON j.posted_by = u.id
      WHERE j.id = ?
    `, [result.insertId]);
    
    const job = newJob[0];
    res.status(201).json({
      ...job,
      posted_by_name: job.first_name ? `${job.first_name} ${job.last_name}` : 'Unknown',
      applications_count: 0,
      application_url: applicationUrl,
      application_code: applicationCode,
      public_link: `${req.protocol}://${req.get('host')}${applicationUrl}`
    });
  } catch (error) {
    console.error('Error creating job:', error);
    res.status(500).json({ error: 'Failed to create job' });
  }
});

// PUT /api/jobs/:id - Update job
router.put('/:id', async (req, res) => {
  try {
    const {
      title, description, department_id, requirements, salary_min, salary_max,
      location, employment_type, experience_level, status
    } = req.body;
    const jobId = req.params.id;
    
    if (!title || !description || !department_id) {
      return res.status(400).json({ 
        error: 'Title, description, and department are required' 
      });
    }
    
    const [result] = await pool.execute(`
      UPDATE jobs 
      SET title = ?, description = ?, department_id = ?, requirements = ?, 
          salary_min = ?, salary_max = ?, location = ?, employment_type = ?, 
          experience_level = ?, status = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [title, description, department_id, requirements, salary_min, salary_max,
        location, employment_type, experience_level, status, jobId]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Job not found' });
    }
    
    // Fetch the updated job
    const [updatedJob] = await pool.execute(`
      SELECT j.*, d.name as department_name, u.first_name, u.last_name,
             COUNT(ja.id) as applications_count
      FROM jobs j
      LEFT JOIN departments d ON j.department_id = d.id
      LEFT JOIN users u ON j.posted_by = u.id
      LEFT JOIN job_applications ja ON j.id = ja.job_id
      WHERE j.id = ?
      GROUP BY j.id
    `, [jobId]);
    
    const job = updatedJob[0];
    res.json({
      ...job,
      posted_by_name: job.first_name ? `${job.first_name} ${job.last_name}` : 'Unknown'
    });
  } catch (error) {
    console.error('Error updating job:', error);
    res.status(500).json({ error: 'Failed to update job' });
  }
});

// DELETE /api/jobs/:id - Delete job
router.delete('/:id', async (req, res) => {
  try {
    // Check if job has applications
    const [applications] = await pool.execute(
      'SELECT COUNT(*) as count FROM job_applications WHERE job_id = ?', 
      [req.params.id]
    );
    
    if (applications[0].count > 0) {
      return res.status(400).json({ 
        error: 'Cannot delete job with applications. Set status to closed instead.' 
      });
    }
    
    const [result] = await pool.execute('DELETE FROM jobs WHERE id = ?', [req.params.id]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Job not found' });
    }
    
    res.json({ message: 'Job deleted successfully' });
  } catch (error) {
    console.error('Error deleting job:', error);
    res.status(500).json({ error: 'Failed to delete job' });
  }
});

// GET /api/jobs/:id/applications - Get applications for a specific job
router.get('/:id/applications', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT ja.*, c.name, c.email, c.phone, c.experience_years
      FROM job_applications ja
      JOIN candidates c ON ja.candidate_id = c.id
      WHERE ja.job_id = ?
      ORDER BY ja.application_date DESC
    `, [req.params.id]);
    
    res.json(rows);
  } catch (error) {
    console.error('Error fetching job applications:', error);
    res.status(500).json({ error: 'Failed to fetch job applications' });
  }
});

module.exports = router;
