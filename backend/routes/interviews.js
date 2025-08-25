const express = require('express');
const { pool } = require('../config/database');
const router = express.Router();

// GET /api/interviews - Get all interviews
router.get('/', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT i.*, c.name as candidate_name, c.email as candidate_email,
             j.title as job_title, d.name as department_name
      FROM interviews i
      JOIN candidates c ON i.candidate_id = c.id
      LEFT JOIN jobs j ON i.job_id = j.id
      LEFT JOIN departments d ON j.department_id = d.id
      ORDER BY i.interview_date DESC
    `);
    
    res.json(rows.map(interview => ({
      ...interview,
      interviewer_name: 'Not Assigned'
    })));
  } catch (error) {
    console.error('Error fetching interviews:', error);
    res.status(500).json({ error: 'Failed to fetch interviews' });
  }
});

// GET /api/interviews/:id - Get single interview
router.get('/:id', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT i.*, c.name as candidate_name, c.email as candidate_email,
             j.title as job_title, d.name as department_name
      FROM interviews i
      JOIN candidates c ON i.candidate_id = c.id
      LEFT JOIN jobs j ON i.job_id = j.id
      LEFT JOIN departments d ON j.department_id = d.id
      WHERE i.id = ?
    `, [req.params.id]);
    
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Interview not found' });
    }
    
    const interview = rows[0];
    res.json({
      ...interview,
      interviewer_name: interview.first_name ? 
        `${interview.first_name} ${interview.last_name}` : 'Unknown'
    });
  } catch (error) {
    console.error('Error fetching interview:', error);
    res.status(500).json({ error: 'Failed to fetch interview' });
  }
});

// POST /api/interviews - Create new interview
router.post('/', async (req, res) => {
  try {
    const {
      candidate_id, job_id, interviewer_id, interview_date, interview_type,
      duration_minutes, feedback, rating, status, interview_link
    } = req.body;
    
    if (!candidate_id || !interview_date) {
      return res.status(400).json({ error: 'Candidate ID and interview date are required' });
    }
    
    const [result] = await pool.execute(`
      INSERT INTO interviews (candidate_id, job_id, interview_date,
                             interview_type, duration_minutes, feedback, rating, status, interview_link)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [candidate_id, job_id, interview_date, interview_type || 'video',
        duration_minutes, feedback, rating, status || 'scheduled', interview_link]);
    
    // Fetch the created interview
    const [newInterview] = await pool.execute(`
      SELECT i.*, c.name as candidate_name, c.email as candidate_email,
             j.title as job_title
      FROM interviews i
      JOIN candidates c ON i.candidate_id = c.id
      LEFT JOIN jobs j ON i.job_id = j.id
      WHERE i.id = ?
    `, [result.insertId]);
    
    const interview = newInterview[0];
    res.status(201).json({
      ...interview,
      interviewer_name: 'Not Assigned'
    });
  } catch (error) {
    console.error('Error creating interview:', error);
    res.status(500).json({ error: 'Failed to create interview' });
  }
});

// PUT /api/interviews/:id - Update interview
router.put('/:id', async (req, res) => {
  try {
    const {
      candidate_id, job_id, interview_date, interview_type,
      duration_minutes, feedback, rating, status, interview_link
    } = req.body;
    const interviewId = req.params.id;
    
    if (!candidate_id || !interview_date) {
      return res.status(400).json({ error: 'Candidate ID and interview date are required' });
    }
    
    const [result] = await pool.execute(`
      UPDATE interviews 
      SET candidate_id = ?, job_id = ?, interview_date = ?,
          interview_type = ?, duration_minutes = ?, feedback = ?, rating = ?, 
          status = ?, interview_link = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [candidate_id, job_id, interview_date, interview_type,
        duration_minutes, feedback, rating, status, interview_link, interviewId]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Interview not found' });
    }
    
    // Fetch the updated interview
    const [updatedInterview] = await pool.execute(`
      SELECT i.*, c.name as candidate_name, c.email as candidate_email,
             j.title as job_title
      FROM interviews i
      JOIN candidates c ON i.candidate_id = c.id
      LEFT JOIN jobs j ON i.job_id = j.id
      WHERE i.id = ?
    `, [interviewId]);
    
    const interview = updatedInterview[0];
    res.json({
      ...interview,
      interviewer_name: 'Not Assigned'
    });
  } catch (error) {
    console.error('Error updating interview:', error);
    res.status(500).json({ error: 'Failed to update interview' });
  }
});

// DELETE /api/interviews/:id - Delete interview
router.delete('/:id', async (req, res) => {
  try {
    const [result] = await pool.execute('DELETE FROM interviews WHERE id = ?', [req.params.id]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Interview not found' });
    }
    
    res.json({ message: 'Interview deleted successfully' });
  } catch (error) {
    console.error('Error deleting interview:', error);
    res.status(500).json({ error: 'Failed to delete interview' });
  }
});

module.exports = router;
