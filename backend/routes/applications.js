const express = require('express');
const { pool } = require('../config/database');
const router = express.Router();

// GET /api/applications - Get all job applications
router.get('/', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT ja.*, c.name as candidate_name, c.email, c.phone,
             j.title as job_title, d.name as department_name
      FROM job_applications ja
      JOIN candidates c ON ja.candidate_id = c.id
      JOIN jobs j ON ja.job_id = j.id
      LEFT JOIN departments d ON j.department_id = d.id
      ORDER BY ja.application_date DESC
    `);
    
    res.json(rows);
  } catch (error) {
    console.error('Error fetching applications:', error);
    res.status(500).json({ error: 'Failed to fetch applications' });
  }
});

// POST /api/applications - Create new job application
router.post('/', async (req, res) => {
  try {
    const { job_id, candidate_id, status, cover_letter } = req.body;
    
    if (!job_id || !candidate_id) {
      return res.status(400).json({ error: 'Job ID and Candidate ID are required' });
    }
    
    const [result] = await pool.execute(`
      INSERT INTO job_applications (job_id, candidate_id, status, cover_letter)
      VALUES (?, ?, ?, ?)
    `, [job_id, candidate_id, status || 'applied', cover_letter]);
    
    // Fetch the created application
    const [newApp] = await pool.execute(`
      SELECT ja.*, c.name as candidate_name, c.email, c.phone,
             j.title as job_title, d.name as department_name
      FROM job_applications ja
      JOIN candidates c ON ja.candidate_id = c.id
      JOIN jobs j ON ja.job_id = j.id
      LEFT JOIN departments d ON j.department_id = d.id
      WHERE ja.id = ?
    `, [result.insertId]);
    
    res.status(201).json(newApp[0]);
  } catch (error) {
    console.error('Error creating application:', error);
    if (error.code === 'ER_DUP_ENTRY') {
      res.status(400).json({ error: 'Application already exists for this job and candidate' });
    } else {
      res.status(500).json({ error: 'Failed to create application' });
    }
  }
});

// PUT /api/applications/:id - Update application status
router.put('/:id', async (req, res) => {
  try {
    const { status, cover_letter } = req.body;
    const applicationId = req.params.id;
    
    if (!status) {
      return res.status(400).json({ error: 'Status is required' });
    }
    
    const [result] = await pool.execute(`
      UPDATE job_applications 
      SET status = ?, cover_letter = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [status, cover_letter, applicationId]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Application not found' });
    }
    
    // Fetch the updated application
    const [updatedApp] = await pool.execute(`
      SELECT ja.*, c.name as candidate_name, c.email, c.phone,
             j.title as job_title, d.name as department_name
      FROM job_applications ja
      JOIN candidates c ON ja.candidate_id = c.id
      JOIN jobs j ON ja.job_id = j.id
      LEFT JOIN departments d ON j.department_id = d.id
      WHERE ja.id = ?
    `, [applicationId]);
    
    res.json(updatedApp[0]);
  } catch (error) {
    console.error('Error updating application:', error);
    res.status(500).json({ error: 'Failed to update application' });
  }
});

// DELETE /api/applications/:id - Delete application
router.delete('/:id', async (req, res) => {
  try {
    const [result] = await pool.execute('DELETE FROM job_applications WHERE id = ?', [req.params.id]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Application not found' });
    }
    
    res.json({ message: 'Application deleted successfully' });
  } catch (error) {
    console.error('Error deleting application:', error);
    res.status(500).json({ error: 'Failed to delete application' });
  }
});

module.exports = router;
