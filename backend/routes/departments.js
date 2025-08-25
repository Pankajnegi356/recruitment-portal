const express = require('express');
const { pool } = require('../config/database');
const router = express.Router();

// GET /api/departments - Get all departments
router.get('/', async (req, res) => {
  try {
    // Get departments with manager info
    const [departments] = await pool.execute(`
      SELECT d.*, 
             m.first_name as manager_first_name, 
             m.last_name as manager_last_name, 
             m.email as manager_email
      FROM departments d
      LEFT JOIN users m ON d.manager_id = m.id
      ORDER BY d.name
    `);
    
    // Get team members for each department
    const departmentsWithTeams = await Promise.all(departments.map(async (dept) => {
      const [teamMembers] = await pool.execute(`
        SELECT u.id, u.first_name, u.last_name, u.email, u.role, u.is_active
        FROM users u
        WHERE u.department_id = ? AND u.role IN ('recruiter', 'interviewer')
        ORDER BY u.first_name, u.last_name
      `, [dept.id]);
      
      return {
        ...dept,
        manager_name: dept.manager_first_name ? `${dept.manager_first_name} ${dept.manager_last_name}` : null,
        team_members: teamMembers,
        team_count: teamMembers.length
      };
    }));
    
    res.json(departmentsWithTeams);
  } catch (error) {
    console.error('Error fetching departments:', error);
    res.status(500).json({ error: 'Failed to fetch departments' });
  }
});

// GET /api/departments/:id - Get single department
router.get('/:id', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT d.*, u.first_name, u.last_name, u.email as manager_email
      FROM departments d
      LEFT JOIN users u ON d.manager_id = u.id
      WHERE d.id = ?
    `, [req.params.id]);
    
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Department not found' });
    }
    
    const dept = rows[0];
    
    // Get team members for this department
    const [teamMembers] = await pool.execute(`
      SELECT u.id, u.first_name, u.last_name, u.email, u.role, u.is_active
      FROM users u
      WHERE u.department_id = ? AND u.role IN ('recruiter', 'interviewer')
      ORDER BY u.first_name, u.last_name
    `, [req.params.id]);
    
    res.json({
      ...dept,
      manager_name: dept.first_name ? `${dept.first_name} ${dept.last_name}` : null,
      team_members: teamMembers
    });
  } catch (error) {
    console.error('Error fetching department:', error);
    res.status(500).json({ error: 'Failed to fetch department' });
  }
});

// POST /api/departments - Create new department
router.post('/', async (req, res) => {
  try {
    const { name, description, manager_id } = req.body;
    
    if (!name) {
      return res.status(400).json({ error: 'Department name is required' });
    }
    
    const [result] = await pool.execute(`
      INSERT INTO departments (name, description, manager_id)
      VALUES (?, ?, ?)
    `, [name, description, manager_id || null]);
    
    // Fetch the created department
    const [newDept] = await pool.execute(`
      SELECT d.*, u.first_name, u.last_name
      FROM departments d
      LEFT JOIN users u ON d.manager_id = u.id
      WHERE d.id = ?
    `, [result.insertId]);
    
    const dept = newDept[0];
    res.status(201).json({
      ...dept,
      manager_name: dept.first_name ? `${dept.first_name} ${dept.last_name}` : null
    });
  } catch (error) {
    console.error('Error creating department:', error);
    if (error.code === 'ER_DUP_ENTRY') {
      res.status(400).json({ error: 'Department name already exists' });
    } else {
      res.status(500).json({ error: 'Failed to create department' });
    }
  }
});

// PUT /api/departments/:id - Update department
router.put('/:id', async (req, res) => {
  try {
    const { name, description, manager_id } = req.body;
    const departmentId = req.params.id;
    
    if (!name) {
      return res.status(400).json({ error: 'Department name is required' });
    }
    
    const [result] = await pool.execute(`
      UPDATE departments 
      SET name = ?, description = ?, manager_id = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [name, description, manager_id || null, departmentId]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Department not found' });
    }
    
    // Fetch the updated department
    const [updatedDept] = await pool.execute(`
      SELECT d.*, u.first_name, u.last_name
      FROM departments d
      LEFT JOIN users u ON d.manager_id = u.id
      WHERE d.id = ?
    `, [departmentId]);
    
    const dept = updatedDept[0];
    res.json({
      ...dept,
      manager_name: dept.first_name ? `${dept.first_name} ${dept.last_name}` : null
    });
  } catch (error) {
    console.error('Error updating department:', error);
    if (error.code === 'ER_DUP_ENTRY') {
      res.status(400).json({ error: 'Department name already exists' });
    } else {
      res.status(500).json({ error: 'Failed to update department' });
    }
  }
});

// DELETE /api/departments/:id - Delete department
router.delete('/:id', async (req, res) => {
  try {
    // Check if department has associated jobs
    const [jobs] = await pool.execute('SELECT COUNT(*) as count FROM jobs WHERE department_id = ?', [req.params.id]);
    
    if (jobs[0].count > 0) {
      return res.status(400).json({ 
        error: `Cannot delete department: ${jobs[0].count} jobs still assigned. Please delete or reassign jobs first.` 
      });
    }
    
    // Automatically reassign users to null (no department) before deletion
    const [users] = await pool.execute('SELECT COUNT(*) as count FROM users WHERE department_id = ?', [req.params.id]);
    
    if (users[0].count > 0) {
      console.log(`Reassigning ${users[0].count} users from department ${req.params.id} to null`);
      await pool.execute('UPDATE users SET department_id = NULL WHERE department_id = ?', [req.params.id]);
    }
    
    const [result] = await pool.execute('DELETE FROM departments WHERE id = ?', [req.params.id]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Department not found' });
    }
    
    const message = users[0].count > 0 
      ? `Department deleted successfully. ${users[0].count} users were reassigned to no department.`
      : 'Department deleted successfully';
    
    res.json({ message });
  } catch (error) {
    console.error('Error deleting department:', error);
    res.status(500).json({ error: 'Failed to delete department' });
  }
});

// PUT /api/departments/:id/clear-members - Clear all team members from department
router.put('/:id/clear-members', async (req, res) => {
  try {
    // Set department_id to NULL for all users currently assigned to this department
    await pool.execute(`
      UPDATE users SET department_id = NULL WHERE department_id = ?
    `, [req.params.id]);
    
    res.json({ message: 'Department members cleared successfully' });
  } catch (error) {
    console.error('Error clearing department members:', error);
    res.status(500).json({ error: 'Failed to clear department members' });
  }
});

module.exports = router;
