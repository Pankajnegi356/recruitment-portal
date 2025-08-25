const express = require('express');
const { pool } = require('../config/database');
const axios = require('axios');
const FormData = require('form-data');
const multer = require('multer');
const router = express.Router();

// Configure multer for memory storage (don't save to disk)
const upload = multer({ 
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB limit
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'application/pdf' || file.mimetype.startsWith('application/vnd.openxmlformats-officedocument')) {
      cb(null, true);
    } else {
      cb(new Error('Only PDF and Word documents are allowed'));
    }
  }
});

// GET /public/apply/:applicationCode - Get job details by application code
router.get('/apply/:applicationCode', async (req, res) => {
  try {
    const { applicationCode } = req.params;
    
    // Match job by reconstructing application code from title
    const [rows] = await pool.execute(`
      SELECT j.*, d.name as department_name
      FROM jobs j
      LEFT JOIN departments d ON j.department_id = d.id
      WHERE j.status IN ('draft', 'published', 'active')
    `);
    
    // Find matching job by application code
    console.log(`\n🔍 DEBUG: Looking for job with code: ${applicationCode}`);
    console.log(`📊 Found ${rows.length} jobs in database`);
    
    const matchingJob = rows.find(job => {
      // Use the EXACT same logic as generateApplicationCode
      const cleanTitle = job.title
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, '') // Remove special characters
        .replace(/\s+/g, '-') // Replace spaces with hyphens
        .substring(0, 20); // Limit length
      
      // Extract title part from application code (remove timestamp)
      const codeTitle = applicationCode.split('-').slice(0, -1).join('-');
      
      console.log(`🔄 Checking job: "${job.title}" -> cleanTitle: "${cleanTitle}" vs codeTitle: "${codeTitle}"`);
      
      const match = cleanTitle === codeTitle;
      if (match) {
        console.log(`✅ MATCH FOUND: ${job.title}`);
      }
      return match;
    });
    
    console.log(`🎯 Final result: ${matchingJob ? `Found "${matchingJob.title}"` : 'No match found'}\n`);
    
    if (!matchingJob) {
      return res.status(404).json({ error: 'Job not found or no longer available' });
    }
    
    res.json({
      id: matchingJob.id,
      title: matchingJob.title,
      description: matchingJob.description,
      department_name: matchingJob.department_name,
      location: matchingJob.location,
      employment_type: matchingJob.employment_type,
      experience_level: matchingJob.experience_level,
      requirements: matchingJob.requirements,
      salary_min: matchingJob.salary_min,
      salary_max: matchingJob.salary_max
    });
  } catch (error) {
    console.error('Error fetching job for application:', error);
    res.status(500).json({ error: 'Failed to fetch job details' });
  }
});

// POST /public/apply/:applicationCode - Submit job application
router.post('/apply/:applicationCode', upload.single('resume'), async (req, res) => {
  try {
    const { applicationCode } = req.params;
    const { name, email, resume_url } = req.body;
    const resumeFile = req.file;
    
    // Validate required fields
    if (!name || !email) {
      return res.status(400).json({ error: 'Name and email are required' });
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({ error: 'Invalid email format' });
    }
    
    // Find the specific job by application code
    const [allJobs] = await pool.execute(`
      SELECT j.id, j.title, j.department_id, d.name as department_name
      FROM jobs j
      LEFT JOIN departments d ON j.department_id = d.id
      WHERE j.status IN ('draft', 'published', 'active')
    `);
    
    // Find matching job using same logic as GET endpoint
    const matchingJob = allJobs.find(job => {
      const cleanTitle = job.title
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, '')
        .replace(/\s+/g, '-')
        .substring(0, 20);
      const codeTitle = applicationCode.split('-').slice(0, -1).join('-');
      return cleanTitle === codeTitle;
    });
    
    if (!matchingJob) {
      return res.status(404).json({ error: 'Job not found or no longer available' });
    }
    
    // Check if candidate already exists
    const [existingCandidate] = await pool.execute(`
      SELECT id FROM candidates WHERE email = ?
    `, [email]);
    
    let candidateId;
    
    if (existingCandidate.length > 0) {
      // Update existing candidate with job info
      candidateId = existingCandidate[0].id;
      await pool.execute(`
        UPDATE candidates 
        SET name = ?, resume_path = ?, job_id = ?, department_id = ?, status = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
      `, [name, resume_url || 'Resume attached to email', matchingJob.id, matchingJob.department_id, candidateId]);
    } else {
      // Create new candidate with status 1 (applied) and job info
      const [result] = await pool.execute(`
        INSERT INTO candidates (name, email, resume_path, job_id, department_id, source, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'public_application', 1, CURRENT_TIMESTAMP)
      `, [name, email, resume_url || 'Resume attached to email', matchingJob.id, matchingJob.department_id]);
      candidateId = result.insertId;
    }
    
    // Check if application already exists
    const [existingApplication] = await pool.execute(`
      SELECT id FROM job_applications 
      WHERE candidate_id = ? AND job_id = ?
    `, [candidateId, matchingJob.id]);
    
    if (existingApplication.length > 0) {
      return res.status(400).json({ 
        error: 'You have already applied for this position' 
      });
    }
    
    // Create job application
    const [applicationResult] = await pool.execute(`
      INSERT INTO job_applications (candidate_id, job_id, status, application_date)
      VALUES (?, ?, 'applied', CURRENT_TIMESTAMP)
    `, [candidateId, matchingJob.id]);

    // Create activity log entry for the application
    try {
      await pool.execute(`
        INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
      `, [
        null, // No user_id for public applications
        'applied for',
        'job',
        matchingJob.id,
        `${name} applied for ${matchingJob.title} position`
      ]);
    } catch (logError) {
      console.error('Failed to create activity log:', logError);
      // Don't fail the application if activity log fails
    }
    
    // Send email notification to HR team
    try {
      const emailContent = `
🎯 NEW JOB APPLICATION RECEIVED

📋 JOB DETAILS:
• Position: ${matchingJob.title}
• Department: ${matchingJob.department_name}
• Application Code: ${applicationCode}
• Job ID: ${matchingJob.id}

👤 CANDIDATE INFORMATION:
• Full Name: ${name}
• Email Address: ${email}
• Resume: Attached to this email
• Application Date: ${new Date().toLocaleString('en-US', { timeZone: 'UTC' })}

📊 APPLICATION DETAILS:
• Application ID: ${applicationResult.insertId}
• Candidate ID: ${candidateId}
• Source: Public Application Form

🔗 QUICK ACTIONS:
• View in Admin Panel: http://localhost:8080/candidates
• Contact Candidate: ${email}

This is an automated notification from Veersa AI Recruitment Portal.
      `;

      const formData = new FormData();
      formData.append('to', 'notifications.veersa@gmail.com');
      formData.append('subject', `New Application: ${name} - ${matchingJob.title}`);
      formData.append('content', emailContent);

      // Attach resume directly from uploaded file
      if (resumeFile) {
        formData.append('attachment', resumeFile.buffer, {
          filename: `${name}_Resume.pdf`,
          contentType: resumeFile.mimetype
        });
        console.log('✅ Resume attached to email');
      }

      // Send email notification
      const emailResponse = await axios.post('http://48.216.217.84:5002/send-email', formData, {
        headers: {
          ...formData.getHeaders(),
        },
        timeout: 10000 // 10 second timeout for email
      });

      console.log('✅ Application notification email sent:', emailResponse.status);
    } catch (emailError) {
      console.error('❌ Failed to send application notification email:', emailError.message);
      // Don't fail the application if email fails, just log it
    }

    res.status(201).json({
      message: 'Application submitted successfully',
      application_id: applicationResult.insertId,
      job_title: matchingJob.title,
      candidate_id: candidateId,
      status: 1 // Applied status
    });
    
  } catch (error) {
    console.error('Error submitting application:', error);
    res.status(500).json({ error: 'Failed to submit application' });
  }
});

module.exports = router;
