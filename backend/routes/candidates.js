const express = require('express');
const { pool } = require('../config/database');
const router = express.Router();

// GET /api/candidates - Get all candidates
router.get('/', async (req, res) => {
  try {
    // Check if candidates table has any data
    const [candidateCount] = await pool.execute('SELECT COUNT(*) as count FROM candidates');
    
    if (candidateCount[0].count === 0) {
      return res.json([]);
    }

    const [rows] = await pool.execute(`
      SELECT c.*, 
             COALESCE(d.name, 'No Department') as department_name, 
             COALESCE(j.title, 'No Job') as job_title,
             COUNT(DISTINCT ja.id) as applications_count,
             COUNT(DISTINCT i.id) as interviews_count,
             COUNT(DISTINCT it.id) as test_count,
             AVG(it.test_score) as avg_prescreening_score,
             MAX(it.test_score) as max_prescreening_score
      FROM candidates c
      LEFT JOIN departments d ON c.department_id = d.id
      LEFT JOIN jobs j ON c.job_id = j.id
      LEFT JOIN job_applications ja ON c.id = ja.candidate_id
      LEFT JOIN interviews i ON c.id = i.candidate_id
      LEFT JOIN interview_tests it ON c.id = it.candidate_id
      GROUP BY c.id
      ORDER BY c.created_at DESC
    `);
    
    res.json(rows);
  } catch (error) {
    console.error('Error fetching candidates:', error);
    res.status(500).json({ error: 'Failed to fetch candidates' });
  }
});

// GET /api/candidates/:id - Get single candidate
router.get('/:id', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT c.*, d.name as department_name, j.title as job_title,
             COUNT(DISTINCT ja.id) as applications_count,
             COUNT(DISTINCT i.id) as interviews_count,
             COUNT(DISTINCT it.id) as test_count,
             AVG(it.test_score) as avg_prescreening_score,
             MAX(it.test_score) as max_prescreening_score,
             AVG(i.rating) as avg_interview_rating,
             MAX(i.rating) as max_interview_rating
      FROM candidates c
      LEFT JOIN departments d ON c.department_id = d.id
      LEFT JOIN jobs j ON c.job_id = j.id
      LEFT JOIN job_applications ja ON c.id = ja.candidate_id
      LEFT JOIN interviews i ON c.id = i.candidate_id
      LEFT JOIN interview_tests it ON c.id = it.candidate_id
      WHERE c.id = ?
      GROUP BY c.id
    `, [req.params.id]);
    
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Candidate not found' });
    }
    
    res.json(rows[0]);
  } catch (error) {
    console.error('Error fetching candidate:', error);
    res.status(500).json({ error: 'Failed to fetch candidate' });
  }
});

// POST /api/candidates - Create new candidate
router.post('/', async (req, res) => {
  try {
    const {
      name, email, phone, summary, skill_match_score, status, position_applied,
      department_id, job_id, resume_path, experience_years, current_salary,
      expected_salary, source
    } = req.body;
    
    if (!name || !email) {
      return res.status(400).json({ error: 'Name and email are required' });
    }
    
    const [result] = await pool.execute(`
      INSERT INTO candidates (name, email, phone, summary, skill_match_score, status,
                             position_applied, department_id, job_id, resume_path,
                             experience_years, current_salary, expected_salary, source)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [name, email, phone, summary, skill_match_score || null, status || 2,
        position_applied, department_id, job_id, resume_path, experience_years,
        current_salary, expected_salary, source || 'direct']);
    
    // Fetch the created candidate
    const [newCandidate] = await pool.execute(`
      SELECT c.*, d.name as department_name, j.title as job_title
      FROM candidates c
      LEFT JOIN departments d ON c.department_id = d.id
      LEFT JOIN jobs j ON c.job_id = j.id
      WHERE c.id = ?
    `, [result.insertId]);
    
    const candidate = newCandidate[0];
    res.status(201).json({
      ...candidate,
      applications_count: 0,
      interviews_count: 0
    });
  } catch (error) {
    console.error('Error creating candidate:', error);
    if (error.code === 'ER_DUP_ENTRY') {
      res.status(400).json({ error: 'Email already exists' });
    } else {
      res.status(500).json({ error: 'Failed to create candidate' });
    }
  }
});

// PUT /api/candidates/:id - Update candidate
router.put('/:id', async (req, res) => {
  try {
    const {
      name, email, phone, summary, skill_match_score, status, position_applied,
      department_id, job_id, resume_path, experience_years, current_salary,
      expected_salary, source
    } = req.body;
    const candidateId = req.params.id;
    
    if (!name || !email) {
      return res.status(400).json({ error: 'Name and email are required' });
    }
    
    const [result] = await pool.execute(`
      UPDATE candidates 
      SET name = ?, email = ?, phone = ?, summary = ?, skill_match_score = ?, 
          status = ?, position_applied = ?, department_id = ?, job_id = ?, 
          resume_path = ?, experience_years = ?, current_salary = ?, 
          expected_salary = ?, source = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [name, email, phone, summary, skill_match_score, status, position_applied,
        department_id, job_id, resume_path, experience_years, current_salary,
        expected_salary, source, candidateId]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Candidate not found' });
    }
    
    // Fetch the updated candidate
    const [updatedCandidate] = await pool.execute(`
      SELECT c.*, d.name as department_name, j.title as job_title,
             COUNT(DISTINCT ja.id) as applications_count,
             COUNT(DISTINCT i.id) as interviews_count
      FROM candidates c
      LEFT JOIN departments d ON c.department_id = d.id
      LEFT JOIN jobs j ON c.job_id = j.id
      LEFT JOIN job_applications ja ON c.id = ja.candidate_id
      LEFT JOIN interviews i ON c.id = i.candidate_id
      WHERE c.id = ?
      GROUP BY c.id
    `, [candidateId]);
    
    res.json(updatedCandidate[0]);
  } catch (error) {
    console.error('Error updating candidate:', error);
    if (error.code === 'ER_DUP_ENTRY') {
      res.status(400).json({ error: 'Email already exists' });
    } else {
      res.status(500).json({ error: 'Failed to update candidate' });
    }
  }
});

// DELETE /api/candidates/:id - Delete candidate
router.delete('/:id', async (req, res) => {
  try {
    // Check if candidate has applications or interviews
    const [applications] = await pool.execute(
      'SELECT COUNT(*) as count FROM job_applications WHERE candidate_id = ?', 
      [req.params.id]
    );
    const [interviews] = await pool.execute(
      'SELECT COUNT(*) as count FROM interviews WHERE candidate_id = ?', 
      [req.params.id]
    );
    
    if (applications[0].count > 0 || interviews[0].count > 0) {
      return res.status(400).json({ 
        error: 'Cannot delete candidate with applications or interviews' 
      });
    }
    
    const [result] = await pool.execute('DELETE FROM candidates WHERE id = ?', [req.params.id]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Candidate not found' });
    }
    
    res.json({ message: 'Candidate deleted successfully' });
  } catch (error) {
    console.error('Error deleting candidate:', error);
    res.status(500).json({ error: 'Failed to delete candidate' });
  }
});

// GET /api/candidates/:id/applications - Get applications for a candidate
router.get('/:id/applications', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT ja.*, j.title, j.department_id, d.name as department_name
      FROM job_applications ja
      JOIN jobs j ON ja.job_id = j.id
      LEFT JOIN departments d ON j.department_id = d.id
      WHERE ja.candidate_id = ?
      ORDER BY ja.application_date DESC
    `, [req.params.id]);
    
    res.json(rows);
  } catch (error) {
    console.error('Error fetching candidate applications:', error);
    res.status(500).json({ error: 'Failed to fetch candidate applications' });
  }
});

// GET /api/candidates/:id/interviews - Get interviews for a candidate
router.get('/:id/interviews', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT i.*, j.title as job_title
      FROM interviews i
      LEFT JOIN jobs j ON i.job_id = j.id
      WHERE i.candidate_id = ?
      ORDER BY i.interview_date DESC
    `, [req.params.id]);
    
    res.json(rows.map(interview => ({
      ...interview,
      interviewer_name: 'Not Assigned'
    })));
  } catch (error) {
    console.error('Error fetching candidate interviews:', error);
    res.status(500).json({ error: 'Failed to fetch candidate interviews' });
  }
});

module.exports = router;
