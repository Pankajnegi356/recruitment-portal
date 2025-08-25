const express = require('express');
const { pool } = require('../config/database');
const router = express.Router();

// GET /api/activity-logs - Get all activity logs
router.get('/', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT al.*, u.first_name, u.last_name, u.email
      FROM activity_logs al
      LEFT JOIN users u ON al.user_id = u.id
      ORDER BY al.created_at DESC
    `);
    
    res.json(rows.map(log => ({
      ...log,
      user_name: log.first_name ? `${log.first_name} ${log.last_name}` : 'Unknown'
    })));
  } catch (error) {
    console.error('Error fetching activity logs:', error);
    res.status(500).json({ error: 'Failed to fetch activity logs' });
  }
});

// GET /api/activity-logs/:id - Get single activity log
router.get('/:id', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT al.*, u.first_name, u.last_name, u.email
      FROM activity_logs al
      LEFT JOIN users u ON al.user_id = u.id
      WHERE al.id = ?
    `, [req.params.id]);
    
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Activity log not found' });
    }
    
    const log = rows[0];
    res.json({
      ...log,
      user_name: log.first_name ? `${log.first_name} ${log.last_name}` : 'Unknown'
    });
  } catch (error) {
    console.error('Error fetching activity log:', error);
    res.status(500).json({ error: 'Failed to fetch activity log' });
  }
});

// POST /api/activity-logs - Create new activity log
router.post('/', async (req, res) => {
  try {
    const {
      user_id, action, entity_type, entity_id, details
    } = req.body;
    
    if (!user_id || !action || !entity_type || !entity_id) {
      return res.status(400).json({ 
        error: 'User ID, action, entity type, and entity ID are required' 
      });
    }
    
    const [result] = await pool.execute(`
      INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details)
      VALUES (?, ?, ?, ?, ?)
    `, [user_id, action, entity_type, entity_id, details || null]);
    
    // Fetch the created activity log
    const [newLog] = await pool.execute(`
      SELECT al.*, u.first_name, u.last_name, u.email
      FROM activity_logs al
      LEFT JOIN users u ON al.user_id = u.id
      WHERE al.id = ?
    `, [result.insertId]);
    
    const log = newLog[0];
    res.status(201).json({
      ...log,
      user_name: log.first_name ? `${log.first_name} ${log.last_name}` : 'Unknown'
    });
  } catch (error) {
    console.error('Error creating activity log:', error);
    res.status(500).json({ error: 'Failed to create activity log' });
  }
});

// PUT /api/activity-logs/:id - Update activity log
router.put('/:id', async (req, res) => {
  try {
    const {
      user_id, action, entity_type, entity_id, details
    } = req.body;
    const logId = req.params.id;
    
    if (!user_id || !action || !entity_type || !entity_id) {
      return res.status(400).json({ 
        error: 'User ID, action, entity type, and entity ID are required' 
      });
    }
    
    const [result] = await pool.execute(`
      UPDATE activity_logs 
      SET user_id = ?, action = ?, entity_type = ?, entity_id = ?, details = ?
      WHERE id = ?
    `, [user_id, action, entity_type, entity_id, details || null, logId]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Activity log not found' });
    }
    
    // Fetch the updated activity log
    const [updatedLog] = await pool.execute(`
      SELECT al.*, u.first_name, u.last_name, u.email
      FROM activity_logs al
      LEFT JOIN users u ON al.user_id = u.id
      WHERE al.id = ?
    `, [logId]);
    
    const log = updatedLog[0];
    res.json({
      ...log,
      user_name: log.first_name ? `${log.first_name} ${log.last_name}` : 'Unknown'
    });
  } catch (error) {
    console.error('Error updating activity log:', error);
    res.status(500).json({ error: 'Failed to update activity log' });
  }
});

// DELETE /api/activity-logs/:id - Delete activity log
router.delete('/:id', async (req, res) => {
  try {
    const [result] = await pool.execute('DELETE FROM activity_logs WHERE id = ?', [req.params.id]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Activity log not found' });
    }
    
    res.json({ message: 'Activity log deleted successfully' });
  } catch (error) {
    console.error('Error deleting activity log:', error);
    res.status(500).json({ error: 'Failed to delete activity log' });
  }
});

// GET /api/activity-logs/user/:userId - Get activity logs for a specific user
router.get('/user/:userId', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT al.*, u.first_name, u.last_name, u.email
      FROM activity_logs al
      LEFT JOIN users u ON al.user_id = u.id
      WHERE al.user_id = ?
      ORDER BY al.created_at DESC
    `, [req.params.userId]);
    
    res.json(rows.map(log => ({
      ...log,
      user_name: log.first_name ? `${log.first_name} ${log.last_name}` : 'Unknown'
    })));
  } catch (error) {
    console.error('Error fetching user activity logs:', error);
    res.status(500).json({ error: 'Failed to fetch user activity logs' });
  }
});

// GET /api/activity-logs/entity/:entityType/:entityId - Get activity logs for a specific entity
router.get('/entity/:entityType/:entityId', async (req, res) => {
  try {
    const [rows] = await pool.execute(`
      SELECT al.*, u.first_name, u.last_name, u.email
      FROM activity_logs al
      LEFT JOIN users u ON al.user_id = u.id
      WHERE al.entity_type = ? AND al.entity_id = ?
      ORDER BY al.created_at DESC
    `, [req.params.entityType, req.params.entityId]);
    
    res.json(rows.map(log => ({
      ...log,
      user_name: log.first_name ? `${log.first_name} ${log.last_name}` : 'Unknown'
    })));
  } catch (error) {
    console.error('Error fetching entity activity logs:', error);
    res.status(500).json({ error: 'Failed to fetch entity activity logs' });
  }
});

module.exports = router;
