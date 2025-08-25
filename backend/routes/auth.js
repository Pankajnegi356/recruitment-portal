const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { pool } = require('../config/database');
const router = express.Router();

// POST /api/auth/login - User login
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' });
    }
    
    // Find user by email
    const [users] = await pool.execute(`
      SELECT u.*, d.name as department_name
      FROM users u
      LEFT JOIN departments d ON u.department_id = d.id
      WHERE u.email = ? AND u.is_active = TRUE
    `, [email]);
    
    if (users.length === 0) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const user = users[0];
    
    // Verify password
    const isValidPassword = await bcrypt.compare(password, user.password_hash);
    if (!isValidPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    // Generate JWT token
    const token = jwt.sign(
      { 
        userId: user.id, 
        email: user.email, 
        role: user.role 
      },
      process.env.JWT_SECRET,
      { expiresIn: process.env.JWT_EXPIRES_IN }
    );
    
    // Remove password from response
    const { password_hash, ...userWithoutPassword } = user;
    
    res.json({
      user: userWithoutPassword,
      token
    });
  } catch (error) {
    console.error('Error during login:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

// POST /api/auth/register - User registration (for demo purposes)
router.post('/register', async (req, res) => {
  try {
    const { username, email, password, first_name, last_name, role, department_id } = req.body;
    
    if (!username || !email || !password || !first_name || !last_name) {
      return res.status(400).json({ error: 'All fields are required' });
    }
    
    // Hash password
    const saltRounds = 10;
    const password_hash = await bcrypt.hash(password, saltRounds);
    
    const [result] = await pool.execute(`
      INSERT INTO users (username, email, password_hash, first_name, last_name, role, department_id)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `, [username, email, password_hash, first_name, last_name, role || 'recruiter', department_id]);
    
    // Fetch the created user
    const [newUser] = await pool.execute(`
      SELECT u.*, d.name as department_name
      FROM users u
      LEFT JOIN departments d ON u.department_id = d.id
      WHERE u.id = ?
    `, [result.insertId]);
    
    const { password_hash: _, ...userWithoutPassword } = newUser[0];
    
    res.status(201).json({
      message: 'User registered successfully',
      user: userWithoutPassword
    });
  } catch (error) {
    console.error('Error during registration:', error);
    if (error.code === 'ER_DUP_ENTRY') {
      res.status(400).json({ error: 'Username or email already exists' });
    } else {
      res.status(500).json({ error: 'Registration failed' });
    }
  }
});

// GET /api/auth/users - Get all users (for admin purposes)
router.get('/users', async (req, res) => {
  try {
    const [users] = await pool.execute(`
      SELECT u.id, u.username, u.email, u.first_name, u.last_name, u.role, 
             u.is_active, u.created_at, d.name as department_name
      FROM users u
      LEFT JOIN departments d ON u.department_id = d.id
      ORDER BY u.created_at DESC
    `);
    
    res.json(users);
  } catch (error) {
    console.error('Error fetching users:', error);
    res.status(500).json({ error: 'Failed to fetch users' });
  }
});

// PUT /api/auth/users/:id/toggle-status - Toggle user active status
router.put('/users/:id/toggle-status', async (req, res) => {
  try {
    const { id } = req.params;
    const { is_active } = req.body;
    
    if (typeof is_active !== 'boolean') {
      return res.status(400).json({ error: 'is_active must be a boolean value' });
    }
    
    // Update user status
    const [result] = await pool.execute(`
      UPDATE users SET is_active = ? WHERE id = ?
    `, [is_active, id]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    res.json({ 
      message: `User ${is_active ? 'activated' : 'deactivated'} successfully`,
      is_active 
    });
  } catch (error) {
    console.error('Error updating user status:', error);
    res.status(500).json({ error: 'Failed to update user status' });
  }
});

// PUT /api/auth/users/:id - Update user department assignment
router.put('/users/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { department_id } = req.body;
    
    // Update user department
    const [result] = await pool.execute(`
      UPDATE users SET department_id = ? WHERE id = ?
    `, [department_id, id]);
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    res.json({ 
      message: 'User department updated successfully',
      department_id 
    });
  } catch (error) {
    console.error('Error updating user department:', error);
    res.status(500).json({ error: 'Failed to update user department' });
  }
});

module.exports = router;
