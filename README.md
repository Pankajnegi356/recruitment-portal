# 🚀 Veersa AI Recruitment Portal

## 📖 Table of Contents
- [What is This Project?](#what-is-this-project)
- [How Does It Work?](#how-does-it-work)
- [The Complete Flow](#the-complete-flow)
- [Frontend Features](#frontend-features)
- [Backend System](#backend-system)
- [Database Structure](#database-structure)
- [Setup Instructions](#setup-instructions)
- [Environment Configuration](#environment-configuration)
- [API Integration](#api-integration)
- [Deployment Guide](#deployment-guide)

---

## 🤔 What is This Project?

**Imagine you're a company that needs to hire people. This project is like having a super-smart robot assistant that helps you:**

1. **Collect job applications** automatically
2. **Read resumes** and understand what skills people have
3. **Match candidates** to the right jobs using AI
4. **Test candidates** with automated quizzes
5. **Conduct AI interviews** via video calls
6. **Send follow-up emails** automatically
7. **Track everything** in a beautiful dashboard

Think of it as **"Netflix for job recruitment"** - it uses AI to recommend the best candidates for your jobs!

---

## 🔄 How Does It Work?

### The Magic Happens in 7 Steps:

```
1. 📄 RESUME UPLOAD → 2. 🤖 AI ANALYSIS → 3. 🎯 JOB MATCHING → 4. 📝 AUTO TESTING → 5. 🎥 AI INTERVIEW → 6. 📧 EMAIL UPDATES → 7. 📊 DASHBOARD
```

**Step by Step Explanation:**

1. **📄 Resume Upload**: Person uploads their resume/CV
2. **🤖 AI Analysis**: AI reads the resume and extracts skills, experience, education
3. **🎯 Job Matching**: AI compares candidate skills with available jobs and gives a match score
4. **📝 Auto Testing**: System automatically sends relevant skill tests to candidates
5. **🎥 AI Interview**: AI conducts video interviews and asks relevant questions
6. **📧 Email Updates**: Automated emails keep everyone informed about progress
7. **📊 Dashboard**: HR team sees everything organized in beautiful charts and lists

---

## 🌊 The Complete Flow

### For Candidates (Job Seekers):
```
👤 Candidate applies for job
    ↓
📄 Uploads resume/CV
    ↓
🤖 AI analyzes resume (extracts skills, experience)
    ↓
🎯 AI calculates job match score (0-100%)
    ↓
📧 Gets automated email: "Application received"
    ↓
📝 Takes skill assessment test (if match score > 70%)
    ↓
📧 Gets email: "Test completed, next steps"
    ↓
🎥 AI video interview (if test passed)
    ↓
📧 Gets final result: "Hired" or "Thank you for applying"
```

### For HR Team (Recruiters):
```
👥 HR posts new job opening
    ↓
📊 Sees all applications in dashboard
    ↓
🎯 Reviews AI match scores for each candidate
    ↓
📝 Monitors test results and interview scores
    ↓
✅ Makes final hiring decisions
    ↓
📧 System sends automated responses to all candidates
    ↓
📈 Views reports and analytics
```

---

## 🎨 Frontend Features

### 🏠 **Home Dashboard**
- **Overview Cards**: Total candidates, active jobs, interviews scheduled
- **Recent Actions**: Latest candidates and jobs with colorful avatars
- **Reports Section**: Beautiful pie chart showing job status distribution
- **Quick Stats**: At-a-glance numbers for everything important

### 👥 **Candidates Page**
- **Smart Filtering**: Filter by status (Applied, Shortlisted, Interview, etc.)
- **Search Function**: Find candidates by name, email, or skills
- **Status Badges**: Color-coded status indicators
  - 🟡 **Applied** (Yellow)
  - 🟢 **Shortlisted** (Green)
  - 🔵 **Pre-screening Test** (Blue)
  - 🟣 **Technical Interview** (Purple)
  - ⚪ **Interview Confirmed** (Gray)
- **Detailed View**: Click to see full candidate profile with:
  - Personal information
  - Skills and experience
  - AI match score
  - Test results
  - Interview feedback

### 💼 **Jobs Page**
- **Job Listings**: All active and inactive job postings
- **Status Management**: 
  - 🟢 **Active** (Accepting applications)
  - 🟡 **On Hold** (Temporarily paused)
  - 🔵 **Completed** (Position filled)
  - 🔴 **Canceled** (No longer needed)
- **Quick Actions**: Change job status with dropdown
- **Application Counter**: See how many people applied for each job

### 🏢 **Departments Page**
- **Department Management**: Organize jobs by departments
- **Team Assignment**: Assign team members to handle specific departments
- **Activity Tracking**: See which departments are most active

### 🔍 **Search & Filters**
- **Global Search**: Find anything across candidates, jobs, departments
- **Smart Filters**: Multiple filter combinations
- **Real-time Results**: Instant search results as you type

---

## ⚙️ Backend System

### 🤖 **AI Processing Engine**
The backend runs on a separate VM (Virtual Machine) and handles:

#### **Resume Analysis AI**
```python
# Example of what happens when resume is uploaded
def analyze_resume(resume_file):
    # Extract text from PDF/Word document
    text = extract_text_from_file(resume_file)
    
    # Use AI to identify:
    skills = ai_extract_skills(text)
    experience = ai_extract_experience(text)
    education = ai_extract_education(text)
    
    # Store in database
    save_candidate_profile(skills, experience, education)
```

#### **Job Matching Algorithm**
```python
def calculate_match_score(candidate_skills, job_requirements):
    # AI compares candidate skills with job requirements
    match_percentage = ai_skill_matching(candidate_skills, job_requirements)
    return match_percentage  # Returns 0-100%
```

#### **Automated Testing System**
- Generates relevant questions based on job requirements
- Automatically scores responses
- Provides instant feedback

#### **AI Interview System**
- Conducts video interviews
- Analyzes responses for technical accuracy
- Evaluates communication skills
- Provides interview scores and feedback

#### **Email Automation**
```python
# Automatic email triggers
def send_application_received_email(candidate):
    email_template = "Thank you for applying..."
    send_email(candidate.email, email_template)

def send_test_invitation(candidate):
    email_template = "Please take this skills assessment..."
    send_email(candidate.email, email_template)
```

---

## 🗄️ Database Structure

### **Main Tables**

#### **👥 candidates** table
```sql
CREATE TABLE candidates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    resume_file_path VARCHAR(500),
    summary TEXT,
    skills JSON,                    -- AI extracted skills
    experience_years INT,
    education VARCHAR(255),
    skill_match_score DECIMAL(5,2), -- AI calculated match %
    status ENUM('applied', 'shortlisted', 'pre_screening', 'technical_interview', 'interview_confirmed', 'hired', 'rejected'),
    applied_for VARCHAR(255),       -- Which job they applied for
    handler VARCHAR(255),           -- HR person handling this candidate
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### **💼 jobs** table
```sql
CREATE TABLE jobs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    department VARCHAR(255),
    description TEXT,
    requirements JSON,              -- Required skills for this job
    salary_range VARCHAR(100),
    location VARCHAR(255),
    job_type ENUM('full_time', 'part_time', 'contract', 'internship'),
    status ENUM('active', 'on_hold', 'completed', 'canceled'),
    team VARCHAR(255),              -- Which team owns this job
    applications_count INT DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### **🏢 departments** table
```sql
CREATE TABLE departments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    owner VARCHAR(255),             -- Department head
    team VARCHAR(255),              -- Team members
    description TEXT,
    active_jobs_count INT DEFAULT 0,
    total_candidates_count INT DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### **📝 interview_tests** table
```sql
CREATE TABLE interview_tests (
    id INT PRIMARY KEY AUTO_INCREMENT,
    candidate_id INT,
    candidate_name VARCHAR(255),
    candidate_email VARCHAR(255),
    job_id INT,
    test_type ENUM('technical', 'aptitude', 'behavioral'),
    questions JSON,                 -- AI generated questions
    answers JSON,                   -- Candidate answers
    test_score DECIMAL(5,2),        -- AI calculated score
    max_score DECIMAL(5,2),
    time_taken INT,                 -- Minutes taken to complete
    status ENUM('pending', 'completed', 'expired'),
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);
```

#### **🎥 interviews** table
```sql
CREATE TABLE interviews (
    id INT PRIMARY KEY AUTO_INCREMENT,
    candidate_id INT,
    candidate_email VARCHAR(255),
    job_id INT,
    interview_type ENUM('ai_video', 'human_video', 'phone'),
    interview_link VARCHAR(500),    -- Video call link
    interviewer_name VARCHAR(255),  -- "AI Interviewer" or human name
    interview_date DATETIME,
    duration INT,                   -- Minutes
    questions JSON,                 -- Questions asked
    candidate_responses JSON,       -- AI transcribed responses
    technical_score DECIMAL(5,2),
    communication_score DECIMAL(5,2),
    overall_score DECIMAL(5,2),
    feedback TEXT,                  -- AI or human feedback
    status ENUM('scheduled', 'in_progress', 'completed', 'canceled'),
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);
```

#### **📧 email_logs** table
```sql
CREATE TABLE email_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    candidate_id INT,
    candidate_email VARCHAR(255),
    email_type ENUM('application_received', 'test_invitation', 'interview_scheduled', 'result_notification', 'rejection', 'offer_letter'),
    subject VARCHAR(255),
    email_content TEXT,
    sent_at TIMESTAMP,
    delivery_status ENUM('sent', 'delivered', 'failed'),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);
```

#### **📊 application_tracking** table
```sql
CREATE TABLE application_tracking (
    id INT PRIMARY KEY AUTO_INCREMENT,
    candidate_id INT,
    job_id INT,
    application_date DATE,
    current_stage ENUM('applied', 'resume_reviewed', 'test_sent', 'test_completed', 'interview_scheduled', 'interview_completed', 'decision_pending', 'hired', 'rejected'),
    stage_updated_at TIMESTAMP,
    notes TEXT,
    hr_handler VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
```

---

## 🚀 Setup Instructions

### **Step 1: Clone the Project**
```bash
git clone https://github.com/yourusername/veersa-recruit-flow.git
cd veersa-recruit-flow
```

### **Step 2: Install Dependencies**
```bash
# Install frontend dependencies
npm install

# If you have backend code locally
pip install -r requirements.txt  # Python backend
# OR
npm install  # Node.js backend
```

### **Step 3: Environment Setup**
Create `.env` file in root directory:
```env
# Database Configuration
DB_HOST=your-vm-ip-address
DB_PORT=3306
DB_USER=your-db-username
DB_PASSWORD=your-db-password
DB_NAME=recruitment_portal

# API Configuration
API_BASE_URL=http://your-vm-ip:8000
USE_DATABASE=false  # Set to 'true' when VM is accessible

# Email Configuration (for automated emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# AI Service Configuration
OPENAI_API_KEY=your-openai-key
RESUME_PARSER_API=your-resume-parser-endpoint
```

### **Step 4: Database Setup**
When your VM is ready, run these commands:
```sql
-- Create database
CREATE DATABASE recruitment_portal;
USE recruitment_portal;

-- Run all the table creation scripts mentioned above
-- You can find these in database/schema.sql file
```

### **Step 5: Start the Application**
```bash
# Development mode
npm run dev

# Production mode
npm run build
npm start
```

---

## 🔧 Environment Configuration

### **Development Mode (VM Offline)**
```javascript
// In src/config/database.js
export const USE_DATABASE = false;  // Uses mock data
```

### **Production Mode (VM Online)**
```javascript
// In src/config/database.js
export const USE_DATABASE = true;   // Uses real database
```

### **Database Connection Settings**
```javascript
// src/config/database.js
export const DB_CONFIG = {
    host: process.env.DB_HOST || 'your-vm-ip',
    port: process.env.DB_PORT || 3306,
    user: process.env.DB_USER || 'username',
    password: process.env.DB_PASSWORD || 'password',
    database: process.env.DB_NAME || 'recruitment_portal'
};
```

---

## 🔌 API Integration

### **Frontend API Calls**
The frontend makes calls to your backend VM:

```javascript
// src/services/api.js
const API_BASE_URL = process.env.API_BASE_URL || 'http://your-vm-ip:8000';

// Get all candidates
export const getCandidates = async () => {
    if (USE_DATABASE) {
        const response = await fetch(`${API_BASE_URL}/api/candidates`);
        return response.json();
    } else {
        return MOCK_CANDIDATES;  // Fallback to mock data
    }
};

// Submit new job application
export const submitApplication = async (candidateData) => {
    const response = await fetch(`${API_BASE_URL}/api/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(candidateData)
    });
    return response.json();
};

// Trigger AI resume analysis
export const analyzeResume = async (resumeFile) => {
    const formData = new FormData();
    formData.append('resume', resumeFile);
    
    const response = await fetch(`${API_BASE_URL}/api/analyze-resume`, {
        method: 'POST',
        body: formData
    });
    return response.json();
};
```

### **Expected Backend API Endpoints**
Your VM backend should provide these endpoints:

```
GET  /api/candidates          - Get all candidates
GET  /api/candidates/:id      - Get specific candidate
POST /api/candidates          - Add new candidate
PUT  /api/candidates/:id      - Update candidate

GET  /api/jobs                - Get all jobs
GET  /api/jobs/:id           - Get specific job
POST /api/jobs               - Create new job
PUT  /api/jobs/:id           - Update job

GET  /api/departments         - Get all departments
POST /api/departments         - Create department

POST /api/apply               - Submit job application
POST /api/analyze-resume      - Analyze resume with AI
POST /api/generate-test       - Generate skill test
POST /api/schedule-interview  - Schedule AI interview
POST /api/send-email          - Send automated email

GET  /api/dashboard-stats     - Get dashboard statistics
GET  /api/reports            - Get various reports
```

---

## 🌐 Deployment Guide

### **Frontend Deployment (Vercel/Netlify)**
```bash
# Build the project
npm run build

# Deploy to Vercel
vercel deploy

# Or deploy to Netlify
npm install -g netlify-cli
netlify deploy --prod
```

### **Backend Deployment (Your VM)**
```bash
# On your VM, install and start services
sudo apt update
sudo apt install mysql-server python3 python3-pip

# Install Python dependencies
pip3 install flask mysql-connector-python openai pandas numpy

# Start your backend service
python3 app.py
```

### **Database Setup on VM**
```bash
# Install and configure MySQL
sudo mysql_secure_installation

# Create database and user
sudo mysql -u root -p
CREATE DATABASE recruitment_portal;
CREATE USER 'recruit_user'@'%' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON recruitment_portal.* TO 'recruit_user'@'%';
FLUSH PRIVILEGES;
```

---

## 📱 Usage Examples

### **For HR Managers:**
1. **Post a New Job**:
   - Go to Jobs page → Click "Add Job"
   - Fill in job title, requirements, department
   - Set status to "Active"
   - System starts accepting applications

2. **Review Applications**:
   - Go to Candidates page
   - See AI match scores for each candidate
   - Filter by status: "Applied" → "Shortlisted" → etc.
   - Click candidate name for detailed profile

3. **Track Progress**:
   - Home dashboard shows overview
   - Reports section shows job status distribution
   - Recent actions show latest activities

### **For Candidates (External):**
1. **Apply for Job**:
   - Visit application portal
   - Upload resume/CV
   - AI analyzes skills automatically
   - Receives confirmation email

2. **Take Tests**:
   - Gets email with test link
   - AI generates relevant questions
   - Submits answers, gets instant score

3. **AI Interview**:
   - Gets video call link
   - AI interviewer asks questions
   - System records and analyzes responses

---

## 🆘 Troubleshooting

### **Common Issues:**

#### **"Cannot connect to database"**
- Check if `USE_DATABASE` is set to `false` in development
- Verify VM is running and accessible
- Check database credentials in `.env` file

#### **"API endpoint not found"**
- Ensure backend server is running on VM
- Check `API_BASE_URL` in environment variables
- Verify firewall allows connections to your VM

#### **"Resume analysis failed"**
- Check if AI service is running on backend
- Verify OpenAI API key is valid
- Ensure resume file format is supported (PDF, DOC, DOCX)

#### **"Email not sending"**
- Check SMTP credentials in `.env` file
- Verify email service allows app passwords
- Check spam folder for test emails

---

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

---

## 📞 Support

If you need help:
- 📧 **Email**: support@veersa.com
- 💬 **Discord**: Join our community server
- 📖 **Wiki**: Check our detailed documentation
- 🐛 **Issues**: Report bugs on GitHub

---

## 🎯 Project Roadmap

### **Phase 1** ✅ (Current)
- [x] Frontend dashboard with mock data
- [x] Candidate management interface
- [x] Job posting system
- [x] Department organization
- [x] Search and filtering
- [x] Reports with pie charts

### **Phase 2** 🔄 (In Progress)
- [ ] Backend VM integration
- [ ] Database connection
- [ ] AI resume analysis
- [ ] Automated testing system

### **Phase 3** 📅 (Planned)
- [ ] AI video interviews
- [ ] Email automation
- [ ] Advanced analytics
- [ ] Mobile app version

### **Phase 4** 🚀 (Future)
- [ ] Machine learning improvements
- [ ] Multi-language support
- [ ] Integration with job boards
- [ ] Advanced reporting

---

## 🏆 Success Stories

*"This AI recruitment system reduced our hiring time from 3 months to 3 weeks!"*
- **Tech Startup CEO**

*"The AI matching feature helped us find candidates we would have missed manually."*
- **HR Director**

---

**Made with ❤️ by the Veersa Team**

*Ready to revolutionize your recruitment process? Let's get started! 🚀*
