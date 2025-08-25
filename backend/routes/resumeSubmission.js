const express = require('express');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const router = express.Router();

// Configure multer for file upload (store in memory)
const storage = multer.memoryStorage();
const upload = multer({
  storage: storage,
  limits: {
    fileSize: 10 * 1024 * 1024 // 10MB limit
  },
  fileFilter: (req, file, cb) => {
    // Accept only PDF, DOC, DOCX files
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ];
    
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only PDF, DOC, and DOCX files are allowed.'));
    }
  }
});

// POST /api/submit-candidate-resume - Submit resume for AI processing
router.post('/', upload.single('resume'), async (req, res) => {
  try {
    const {
      name,
      email,
      phone,
      position_applied,
      department_id,
      job_id,
      experience_years,
      current_salary,
      expected_salary,
      source
    } = req.body;

    // Validate required fields
    if (!name || !email) {
      return res.status(400).json({ error: 'Name and email are required' });
    }

    if (!req.file) {
      return res.status(400).json({ error: 'Resume file is required' });
    }

    console.log('📧 Submitting resume for processing:', {
      name,
      email,
      fileName: req.file.originalname,
      fileSize: req.file.size,
      position_applied
    });

    // Create email content with candidate information
    const emailContent = `
New Candidate Application - Resume for AI Processing

Candidate Details:
- Name: ${name}
- Email: ${email}
- Phone: ${phone || 'Not provided'}
- Position Applied: ${position_applied || 'Not specified'}
- Experience: ${experience_years ? experience_years + ' years' : 'Not specified'}
- Current Salary: ${current_salary ? '$' + current_salary : 'Not provided'}
- Expected Salary: ${expected_salary ? '$' + expected_salary : 'Not provided'}
- Source: ${source || 'direct'}
- Department ID: ${department_id || 'Not specified'}
- Job ID: ${job_id || 'Not specified'}

This resume has been submitted for AI analysis and processing.
The candidate will be automatically added to the system after skill matching analysis.

File Details:
- Original Filename: ${req.file.originalname}
- File Size: ${(req.file.size / 1024 / 1024).toFixed(2)} MB
- File Type: ${req.file.mimetype}
    `;

    // Prepare form data for email service
    const formData = new FormData();
    formData.append('to', 'notifications.veersa@gmail.com'); // Your email processing system
    formData.append('subject', `Resume Submission: ${name} - ${position_applied || 'General Application'}`);
    formData.append('content', emailContent);
    formData.append('attachment', req.file.buffer, {
      filename: req.file.originalname,
      contentType: req.file.mimetype
    });

    // Send email with resume attachment to your AI processing system
    const emailResponse = await axios.post('http://48.216.217.84:5002/send-email', formData, {
      headers: {
        ...formData.getHeaders(),
      },
      timeout: 30000 // 30 second timeout
    });

    console.log('✅ Email sent successfully:', emailResponse.status);

    // Return success response
    res.status(200).json({
      message: 'Resume submitted successfully for AI processing',
      candidate: {
        name,
        email,
        position_applied,
        status: 'submitted_for_processing'
      },
      email_status: emailResponse.status === 200 ? 'sent' : 'failed',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('❌ Resume submission error:', error);

    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ error: 'File size too large. Maximum 10MB allowed.' });
    }

    if (error.message.includes('Invalid file type')) {
      return res.status(400).json({ error: error.message });
    }

    if (error.code === 'ECONNREFUSED' || error.message.includes('timeout')) {
      return res.status(503).json({ 
        error: 'Email service temporarily unavailable. Please try again later.',
        details: 'Could not connect to email processing service'
      });
    }

    res.status(500).json({ 
      error: 'Failed to submit resume for processing',
      details: error.message 
    });
  }
});

module.exports = router;
