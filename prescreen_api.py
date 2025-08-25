from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import glob
from datetime import datetime, timedelta
import uuid
import requests
import hashlib
import traceback
import mysql.connector
# import ollama  # Replaced with direct HTTP requests

from mcq_generator import MCQGenerator, MCQQuestion, QuestionSet, ExperienceLevel
# Import AI-based skill matching
import sys
sys.path.append("AI-BasedSkillMatching")
from skill_matcher import process_resumes

app = FastAPI(
    title="Pre-Screening MCQ API",
    description="AI-powered MCQ generation for candidate pre-screening",
    version="1.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://48.216.217.84:5173",  # Frontend VM
        "*"                           # Allow all for production flexibility
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Database Configuration
DB_CONFIG = {
    'host': '48.216.217.84',
    'port': 3306,
    'user': 'appuser',
    'password': 'strongpassword',
    'database': 'recruitment_portal',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# Initialize MCQ Generator
mcq_generator = MCQGenerator()

# Database Helper Functions
def get_db_connection():
    """Establish MySQL database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None

def update_candidate_status(email: str, status: int):
    """Update candidate status in database"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE candidates SET status = %s, updated_at = NOW() WHERE email = %s",
            (status, email)
        )
        connection.commit()
        print(f"✅ Updated candidate {email} status to {status}")
        return True
    except mysql.connector.Error as e:
        print(f"❌ Error updating candidate status: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def save_test_result(candidate_email: str, session_id: str, test_score: int, status: int, candidate_name: str = "Unknown"):
    """Save test result to interview_tests table"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Get candidate_id from candidates table
        cursor.execute("SELECT id FROM candidates WHERE email = %s", (candidate_email,))
        result = cursor.fetchone()
        candidate_id = result[0] if result else None
        
        if not candidate_id:
            print(f"❌ Candidate not found for email: {candidate_email}")
            return False
        
        # Insert test result
        cursor.execute("""
            INSERT INTO interview_tests (candidate_id, test_score, status, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (candidate_id, test_score, status))
        
        connection.commit()
        print(f"✅ Saved test result for {candidate_email}: Score {test_score}, Status {status}")
        return True
    except mysql.connector.Error as e:
        print(f"❌ Error saving test result: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

# Request/Response Models
class GenerateQuestionsRequest(BaseModel):
    job_role: str
    candidate_email: str
    additional_skills: str = None  # Optional additional skills from job description

class SubmitAnswersRequest(BaseModel):
    session_id: str
    candidate_email: str
    candidate_name: str
    answers: Dict[int, str]  # {question_index: selected_option}

class QuestionResponse(BaseModel):
    session_id: str
    job_role: str
    candidate_email: str
    questions: List[Dict[str, Any]]  # Hide correct answers and explanations
    total_questions: int
    time_limit_minutes: int = 25

class ResultResponse(BaseModel):
    session_id: str
    candidate_email: str
    candidate_name: str
    job_role: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    pass_threshold: float
    passed: bool
    submitted_at: str

class SimpleResultResponse(BaseModel):
    session_id: str
    candidate_name: str
    candidate_email: str
    job_role: str
    total_questions: int
    correct_answers: int
    passed: str  # "pass" or "fail"

# AI Skill Assessment Models
class SkillAssessmentRequest(BaseModel):
    resume_jsons: List[str]  # List of resume JSON strings
    job_description: str     # Job description text

class CandidateSkillResult(BaseModel):
    name: str
    email: str
    phone: str
    summary: str
    score: float

class SkillAssessmentResponse(BaseModel):
    total_candidates: int
    results: List[CandidateSkillResult]

# In-memory storage for active sessions (in production, use a database)
active_sessions: Dict[str, QuestionSet] = {}

# Directory to store candidate responses
RESPONSES_DIR = "candidate_responses"
os.makedirs(RESPONSES_DIR, exist_ok=True)

# Directory to store link security data
LINK_SECURITY_DIR = "link_security"
os.makedirs(LINK_SECURITY_DIR, exist_ok=True)

@app.get("/")
async def root():
    return {
        "message": "Pre-Screening MCQ API",
        "status": "running",
        "endpoints": [
            "/generate-questions",
            "/submit-answers", 
            "/health",
            "/schedule-assessment"
        ]
    }

@app.get("/ping")
async def ping():
    """Simple ping endpoint for quick connectivity check"""
    return {"status": "ok", "message": "API is running"}

@app.get("/experience-levels")
async def get_experience_levels():
    """Get available experience levels"""
    return {
        "experience_levels": [
            {"value": "intern", "label": "Intern", "description": "Entry level - basic concepts within each difficulty level"},
            {"value": "junior", "label": "Junior", "description": "1-2 years experience - fundamental skills within each difficulty"},
            {"value": "mid_level", "label": "Mid Level", "description": "3-5 years experience - intermediate complexity within each difficulty"},
            {"value": "senior", "label": "Senior", "description": "5+ years experience - advanced complexity within each difficulty"},
            {"value": "lead", "label": "Lead", "description": "Leadership role - expert-level complexity within each difficulty"}
        ],
        "note": "All experience levels receive 25 questions (10 easy, 10 medium, 5 hard). Experience level affects the complexity of questions within each difficulty category."
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Use direct HTTP request to check Ollama health
        ollama_host = "http://20.197.14.111:11434"
        
        # Try to get model list via HTTP
        models_response = requests.get(f"{ollama_host}/api/tags", timeout=10)
        available_models = []
        
        if models_response.status_code == 200:
            models_data = models_response.json()
            if 'models' in models_data:
                for model in models_data['models']:
                    model_name = (
                        model.get('name') or 
                        model.get('model') or 
                        model.get('id') or 
                        f"Model-{len(available_models)+1}"
                    )
                    available_models.append(model_name)
        
        # Test actual model connection with a simple request
        try:
            test_payload = {
                "model": "llama3.1:latest",
                "prompt": "Hi",
                "stream": False,
                "options": {"num_predict": 5}
            }
            test_response = requests.post(
                f"{ollama_host}/api/generate", 
                json=test_payload, 
                timeout=30
            )
            model_test_success = test_response.status_code == 200
        except Exception as e:
            model_test_success = False
            print(f"Model test failed: {e}")
        
        return {
            "status": "healthy" if model_test_success else "degraded",
            "ollama_connected": models_response.status_code == 200 if 'models_response' in locals() else False,
            "model_test_passed": model_test_success,
            "available_models": available_models if available_models else ["llama3.1:latest (assumed)"],
            "primary_model": "llama3.1:latest",
            "ollama_host": ollama_host
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "ollama_connected": False,
            "error": str(e),
            "available_models": [],
            "model_test_passed": False,
            "ollama_host": "http://20.197.14.111:11434"
        }

@app.post("/generate-questions", response_model=QuestionResponse)
async def generate_questions(request: GenerateQuestionsRequest):
    """Generate 25 MCQ questions for a specific job role"""
    try:
        print(f"Generating questions for {request.job_role} - {request.candidate_email}")
        if request.additional_skills:
            print(f"Additional skills from JD: {request.additional_skills}")
        
        # Generate questions with additional skills if provided
        question_set = mcq_generator.generate_complete_question_set(request.job_role, request.additional_skills)
        
        if not question_set.questions:
            raise HTTPException(status_code=500, detail="Failed to generate questions")
        
        # Create session ID
        session_id = str(uuid.uuid4())
        
        # Store session with backup to file
        active_sessions[session_id] = question_set
        
        # Also save session to file as backup
        session_file = f"{RESPONSES_DIR}/session_{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump({
                "session_id": session_id,
                "job_role": question_set.job_role,
                "candidate_email": request.candidate_email,
                "questions": [q.dict() for q in question_set.questions],
                "total_questions": question_set.total_questions,
                "created_at": datetime.now().isoformat()
            }, f, indent=2)
        
        # Prepare response (hide correct answers and explanations)
        questions_for_frontend = []
        for i, question in enumerate(question_set.questions):
            questions_for_frontend.append({
                "index": i,
                "question": question.question,
                "options": question.options,
                "difficulty": question.difficulty
            })
        
        response = QuestionResponse(
            session_id=session_id,
            job_role=question_set.job_role,
            candidate_email=request.candidate_email,
            questions=questions_for_frontend,
            total_questions=question_set.total_questions
        )
        
        print(f"Successfully generated {len(questions_for_frontend)} questions")
        return response
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")

@app.post("/submit-answers", response_model=SimpleResultResponse)
async def submit_answers(request: SubmitAnswersRequest, http_request: Request):
    """Submit candidate answers and calculate score with browser verification"""
    try:
        # Verify browser fingerprint for security - ENABLED for submission protection
        current_fingerprint = generate_browser_fingerprint(http_request)
        is_locked, fingerprint_exists = is_link_locked(request.session_id, current_fingerprint)
        
        # Block submission if browser fingerprint doesn't match (security protection)
        if is_locked and fingerprint_exists:
            print(f"🚫 SUBMISSION BLOCKED: Different browser detected for session {request.session_id}")
            print(f"   Current fingerprint: {current_fingerprint[:8]}...")
            print(f"   This prevents cheating by opening assessment in multiple browsers")
            raise HTTPException(
                status_code=403, 
                detail="Assessment submission blocked. You must submit from the same browser where you accessed the assessment link."
            )
        else:
            print(f"✅ Fingerprint check passed for submission from session {request.session_id}")
            print(f"   Browser fingerprint: {current_fingerprint[:8]}...")
        
        # Check if session exists in memory
        question_set = None
        assessment_data = None
        
        if request.session_id in active_sessions:
            print(f"📦 Found session in active_sessions")
            question_set = active_sessions[request.session_id]
        else:
            print(f"🔍 Session not in active_sessions, checking scheduled_assessments")
            # Try to load from scheduled_assessments folder (email-first system)
            assessment_files = glob.glob(f"scheduled_assessments/assessment_{request.session_id}_*.json")
            
            if assessment_files:
                assessment_file = assessment_files[0]  # Take the first (should be only one)
                print(f"📂 Loading assessment from: {assessment_file}")
                with open(assessment_file, 'r') as f:
                    assessment_data = json.load(f)
                
                print(f"✅ Assessment data loaded, reconstructing question set...")
                # Reconstruct question set from scheduled assessment
                questions = []
                for q_data in assessment_data["questions"]:
                    question = MCQQuestion(**q_data)
                    questions.append(question)
                
                question_set = QuestionSet(
                    job_role=assessment_data["job_role"],
                    questions=questions,
                    total_questions=assessment_data["total_questions"]
                )
                print(f"✅ Question set reconstructed with {len(questions)} questions")
            else:
                print(f"🔍 No scheduled assessment found, checking session backup...")
                # Try to load from old session backup (fallback)
                session_file = f"{RESPONSES_DIR}/session_{request.session_id}.json"
                if os.path.exists(session_file):
                    print(f"📂 Loading session from backup file: {session_file}")
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # Reconstruct question set
                    questions = []
                    for q_data in session_data["questions"]:
                        question = MCQQuestion(**q_data)
                        questions.append(question)
                    
                    question_set = QuestionSet(
                        job_role=session_data["job_role"],
                        questions=questions,
                        total_questions=session_data["total_questions"]
                    )
                    print(f"✅ Question set loaded from backup with {len(questions)} questions")
                else:
                    print(f"❌ No session data found anywhere for {request.session_id}")
                    raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Calculate score
        correct_count = 0
        total_questions = len(question_set.questions)
        
        detailed_results = []
        
        for question_index, selected_answer in request.answers.items():
            if question_index < len(question_set.questions):
                question = question_set.questions[question_index]
                is_correct = selected_answer == question.correct_answer
                if is_correct:
                    correct_count += 1
                
                detailed_results.append({
                    "question_index": question_index,
                    "question": question.question,
                    "selected_answer": selected_answer,
                    "correct_answer": question.correct_answer,
                    "is_correct": is_correct,
                    "explanation": question.explanation,
                    "difficulty": question.difficulty
                })
        
        score_percentage = (correct_count / total_questions) * 100
        pass_threshold = 60.0  # 60% to pass
        passed = score_percentage >= pass_threshold
        
        # Create result
        result = ResultResponse(
            session_id=request.session_id,
            candidate_email=request.candidate_email,
            candidate_name=request.candidate_name,
            job_role=question_set.job_role,
            total_questions=total_questions,
            correct_answers=correct_count,
            score_percentage=round(score_percentage, 2),
            pass_threshold=pass_threshold,
            passed=passed,
            submitted_at=datetime.now().isoformat()
        )
        
        # PHASE 1: Removed response_*.json file creation - using database only
        
        # Clean up session files
        if request.session_id in active_sessions:
            del active_sessions[request.session_id]
        
        # Clean up old session backup
        session_file = f"{RESPONSES_DIR}/session_{request.session_id}.json"
        if os.path.exists(session_file):
            os.remove(session_file)
        
        # Clean up scheduled assessment file (remove after completion)
        if assessment_data:
            assessment_files = glob.glob(f"scheduled_assessments/assessment_{request.session_id}_*.json")
            for assessment_file in assessment_files:
                os.remove(assessment_file)
                print(f"Removed completed assessment: {assessment_file}")
        
        # Clean up link security file
        fingerprint_file = os.path.join(LINK_SECURITY_DIR, f"{request.session_id}_fingerprint.json")
        if os.path.exists(fingerprint_file):
            os.remove(fingerprint_file)
            print(f"Removed link security file: {fingerprint_file}")
        
        print(f"Candidate {request.candidate_email} scored {correct_count}/{total_questions} ({score_percentage:.1f}%)")
        
        # PHASE 1: Real-time Database Updates
        print("🔄 Updating database in real-time...")
        
        # Determine new candidate status
        new_candidate_status = 3 if passed else 0  # 3 = passed prescreening, 0 = failed
        test_status = 3 if passed else 0  # Same status for interview_tests table
        
        # Update candidate status immediately
        db_update_success = update_candidate_status(request.candidate_email, new_candidate_status)
        
        # Save test result immediately
        test_save_success = save_test_result(
            candidate_email=request.candidate_email,
            session_id=request.session_id,
            test_score=correct_count,  # Raw score (correct answers)
            status=test_status,
            candidate_name=request.candidate_name
        )
        
        if db_update_success and test_save_success:
            print(f"✅ Real-time DB update successful for {request.candidate_email}")
            print(f"   Candidate status: {new_candidate_status} ({'PASSED' if passed else 'FAILED'})")
            print(f"   Test score: {correct_count}/{total_questions}")
        else:
            print(f"⚠️ Database update had issues for {request.candidate_email}")
        
        # Return simplified response (your desired format)
        simple_result = SimpleResultResponse(
            session_id=request.session_id,
            candidate_name=request.candidate_name,
            candidate_email=request.candidate_email,
            job_role=question_set.job_role,
            total_questions=total_questions,
            correct_answers=correct_count,
            passed="pass" if passed else "fail"
        )
        
        return simple_result
        
    except Exception as e:
        print(f"Error submitting answers: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process answers: {str(e)}")

@app.get("/job-roles")
async def get_job_roles():
    """Get available job roles - now supports dynamic roles"""
    return {
        "message": "Job roles are now dynamically generated based on candidate skills and summary",
        "supported_examples": [
            "Data Scientist",
            "Machine Learning Engineer", 
            "Backend Developer",
            "DevOps Engineer",
            "Frontend Developer",
            "Full Stack Developer",
            "Software Engineer",
            "Core Computer Science Subjects"  # Fallback option
        ],
        "note": "Any job role can be used - questions will be generated dynamically"
    }

@app.get("/sessions")
async def get_active_sessions():
    """Get active sessions (for debugging)"""
    return {
        "active_sessions": len(active_sessions),
        "session_ids": list(active_sessions.keys())
    }

@app.post("/ai-skill-assessment", response_model=SkillAssessmentResponse)
async def ai_skill_assessment(request: SkillAssessmentRequest):
    """AI-based skill assessment for resumes against job description"""
    try:
        print(f"🤖 Starting AI skill assessment for {len(request.resume_jsons)} candidates")
        
        # Call the AI skill matching function
        results = process_resumes(request.resume_jsons, request.job_description)
        
        # Convert results to response format
        candidate_results = []
        for result in results:
            candidate_result = CandidateSkillResult(
                name=result.get("Name", "Unknown"),
                email=result.get("Email", "N/A"),
                phone=result.get("Phone", "N/A"),
                summary=result.get("Summary", "N/A"),
                score=result.get("Score", 0.0)
            )
            candidate_results.append(candidate_result)
        
        print(f"✅ AI skill assessment completed for {len(candidate_results)} candidates")
        
        # Sort by score (highest first)
        candidate_results.sort(key=lambda x: x.score, reverse=True)
        
        response = SkillAssessmentResponse(
            total_candidates=len(candidate_results),
            results=candidate_results
        )
        
        return response
        
    except Exception as e:
        print(f"❌ Error in AI skill assessment: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process AI skill assessment: {str(e)}")

@app.get("/results-summary")
async def get_results_summary():
    """Get simplified results summary for candidates who passed prescreening (status 3) - PHASE 1: Database-driven"""
    try:
        print("🔍 PHASE 1: Reading results from database instead of files...")
        
        connection = get_db_connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Query candidates who passed prescreening (status 3) with their test results
            query = """
            SELECT 
                c.name as candidate_name,
                c.email as candidate_email,
                c.job_role,
                it.test_score as correct_answers,
                25 as total_questions,
                'pass' as passed
            FROM candidates c
            JOIN interview_tests it ON c.id = it.candidate_id
            WHERE c.status = 3
            ORDER BY it.created_at DESC
            """
            
            cursor.execute(query)
            db_results = cursor.fetchall()
            
            # Convert to expected format
            results_summary = []
            for row in db_results:
                summary = {
                    "candidate_name": row["candidate_name"],
                    "candidate_email": row["candidate_email"],
                    "job_role": row["job_role"] or "Unknown",
                    "total_questions": row["total_questions"],
                    "correct_answers": row["correct_answers"],
                    "passed": row["passed"]
                }
                results_summary.append(summary)
            
            print(f"✅ PHASE 1: Found {len(results_summary)} candidates with status 3 (passed prescreening)")
            
            return {
                "total_assessments": len(results_summary),
                "results": results_summary
            }
            
        finally:
            cursor.close()
            connection.close()
        
    except Exception as e:
        print(f"Error getting results summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get results summary: {str(e)}")

@app.get("/results-summary-and-clean")
async def get_results_summary_and_clean():
    """
    Get all assessment results in simplified format and clean up processed files
    This endpoint returns results and then deletes the candidate response files
    Perfect for sending to other models without duplicate processing
    """
    try:
        results_summary = []
        processed_files = []
        
        # Read all result files from candidate_responses directory
        if os.path.exists(RESPONSES_DIR):
            result_files = glob.glob(f"{RESPONSES_DIR}/response_*.json")
            
            for result_file in result_files:
                try:
                    with open(result_file, 'r') as f:
                        result_data = json.load(f)
                    
                    session_info = result_data.get("session_info", {})
                    
                    # Create simplified summary
                    summary = {
                        "session_id": session_info.get("session_id"),
                        "candidate_name": session_info.get("candidate_name", "Unknown"),
                        "candidate_email": session_info.get("candidate_email"),
                        "job_role": session_info.get("job_role"), 
                        "total_questions": session_info.get("total_questions"),
                        "correct_answers": session_info.get("correct_answers"),
                        "passed": "pass" if session_info.get("passed") else "fail"
                    }
                    
                    results_summary.append(summary)
                    processed_files.append(result_file)
                    
                except Exception as e:
                    print(f"Error reading result file {result_file}: {e}")
                    continue
        
        # Clean up processed files after successful reading
        cleaned_files = 0
        for file_path in processed_files:
            try:
                os.remove(file_path)
                cleaned_files += 1
                print(f"✅ Cleaned up: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not delete {file_path}: {e}")
        
        # Also clean up session files for processed sessions
        if os.path.exists(RESPONSES_DIR):
            for summary in results_summary:
                session_file = f"{RESPONSES_DIR}/session_{summary['session_id']}.json"
                if os.path.exists(session_file):
                    try:
                        os.remove(session_file)
                        print(f"✅ Cleaned up session: {session_file}")
                    except Exception as e:
                        print(f"⚠️ Could not delete session file {session_file}: {e}")
        
        return {
            "total_assessments": len(results_summary),
            "results": results_summary,
            "cleanup_info": {
                "files_processed": len(processed_files),
                "files_cleaned": cleaned_files,
                "message": "All processed files have been cleaned up"
            }
        }
        
    except Exception as e:
        print(f"Error getting results summary and cleaning: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get results and clean: {str(e)}")

def generate_browser_fingerprint(request: Request) -> str:
    """Generate a browser fingerprint from request headers for link security"""
    user_agent = request.headers.get("user-agent", "")
    accept_language = request.headers.get("accept-language", "")
    accept_encoding = request.headers.get("accept-encoding", "")
    accept = request.headers.get("accept", "")
    connection = request.headers.get("connection", "")
    
    # Include client IP for additional security
    client_ip = request.client.host if request.client else ""
    
    # Create fingerprint from combined headers and IP
    fingerprint_data = f"{user_agent}:{accept_language}:{accept_encoding}:{accept}:{connection}:{client_ip}"
    fingerprint_hash = hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    print(f"🔍 Generated fingerprint: {fingerprint_hash[:8]}... for IP: {client_ip}")
    return fingerprint_hash

def is_link_expired(created_at: str) -> bool:
    """Check if assessment link has expired (24 hours)"""
    try:
        created_time = datetime.fromisoformat(created_at)
        expiry_time = created_time + timedelta(hours=24)
        return datetime.now() > expiry_time
    except:
        return True

def is_link_locked(session_id: str, current_fingerprint: str) -> tuple:
    """Check if link is locked to another browser. Returns (is_locked, fingerprint_file_exists)"""
    fingerprint_file = os.path.join(LINK_SECURITY_DIR, f"{session_id}_fingerprint.json")
    
    if os.path.exists(fingerprint_file):
        try:
            with open(fingerprint_file, 'r') as f:
                stored_data = json.load(f)
                stored_fingerprint = stored_data.get("fingerprint")
                
                # If fingerprints don't match, link is locked
                if stored_fingerprint != current_fingerprint:
                    return True, True
                else:
                    return False, True
        except:
            return True, True
    
    return False, False

def lock_link_to_browser(session_id: str, fingerprint: str):
    """Lock assessment link to current browser"""
    fingerprint_file = os.path.join(LINK_SECURITY_DIR, f"{session_id}_fingerprint.json")
    
    lock_data = {
        "session_id": session_id,
        "fingerprint": fingerprint,
        "locked_at": datetime.now().isoformat(),
        "fingerprint_short": fingerprint[:8],
        "lock_type": "browser_fingerprint"
    }
    
    with open(fingerprint_file, 'w') as f:
        json.dump(lock_data, f, indent=2)
    
    print(f"🔒 Link locked to fingerprint: {fingerprint[:8]}... at {datetime.now().strftime('%H:%M:%S')}")

def send_assessment_email(candidate_email: str, candidate_name: str, assessment_link: str, job_role: str) -> bool:
    """Send assessment email to candidate using external email API"""
    try:
        # Email API endpoint
        email_api_url = "http://48.216.217.84:5002/send-email"
        
        # Format job role for display
        job_title = job_role.replace('_', ' ').title()
        
        # Email content
        email_subject = f"Technical Assessment - {job_title} Position"
        email_body = f"""
Dear {candidate_name},

Thank you for your interest in the {job_title} position. We are pleased to invite you to complete our technical assessment.

📋 Assessment Details:
• Duration: 25 minutes
• Questions: 25 multiple choice questions
• Topics: Role-specific technical skills
• Pass Threshold: 60%

🔗 Assessment Link: {assessment_link}

⚠️ Important Instructions:
• This link is valid for exactly 24 hours from the time you receive this email
• Once you open the link, it will be locked to your browser session for security
• Please ensure stable internet connection before starting
• You cannot pause or resume the assessment once started
• Do not refresh or close the browser tab during assessment
• After 24 hours, the link will automatically expire and cannot be accessed

For any technical issues, please contact our support team.

Best regards,
Technical Assessment Team
        """
        
        # Prepare form data (NOT JSON!) - Email API expects form data
        form_data = {
            "to": candidate_email,
            "subject": email_subject,
            "content": email_body.strip()
        }
        
        print(f"🔍 Debug: Sending form data to email API")
        
        # Send as form data (this is what works!)
        response = requests.post(
            email_api_url,
            data=form_data,  # Use 'data' for form data, not 'json'
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Email sent successfully to {candidate_email}")
            return True
        else:
            print(f"❌ Email API failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Email sending failed - Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Email sending failed - General error: {e}")
        return False

@app.post("/schedule-assessment")
async def schedule_assessment(request: dict):
    """
    Schedule assessment for a candidate - generates questions and sends email
    Request: {"candidate_email": "email@example.com", "job_role": "machine_learning", "candidate_name": "John Doe", "experience_level": "senior"}
    """
    try:
        candidate_email = request.get("candidate_email")
        job_role = request.get("job_role") 
        candidate_name = request.get("candidate_name", "Candidate")
        additional_skills = request.get("additional_skills")
        difficulty_mix = request.get("difficulty_mix")  # Custom difficulty mix
        experience_level = request.get("experience_level")  # Experience level
        
        if not candidate_email or not job_role:
            raise HTTPException(status_code=400, detail="candidate_email and job_role are required")
        
        # Generate session ID for unique assessment link
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate questions in background
        print(f"🚀 Generating questions for {candidate_name} ({candidate_email}) - Job Role: {job_role}")
        if experience_level:
            print(f"👤 Experience Level: {experience_level}")
        
        # Job roles are now dynamic strings - no validation needed
        print(f"📝 Using dynamic job role: {job_role}")
        
        # Validate experience level if provided
        experience_level_enum = None
        if experience_level:
            try:
                experience_level_enum = ExperienceLevel(experience_level)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid experience level: {experience_level}. Valid options: {[e.value for e in ExperienceLevel]}")
        
        generator = MCQGenerator()
        question_set = generator.generate_complete_question_set(
            job_role, 
            additional_skills, 
            difficulty_mix,
            experience_level_enum
        )
        
        if not question_set.questions:
            raise HTTPException(status_code=500, detail="Failed to generate questions")
        
        # Store questions with session ID and expiry
        expiry_time = datetime.now() + timedelta(days=7)  # Extended to 7 days for testing
        questions_data = {
            "session_id": session_id,
            "candidate_email": candidate_email,
            "candidate_name": candidate_name,
            "job_role": job_role,
            "experience_level": experience_level,
            "questions": [q.__dict__ for q in question_set.questions],
            "total_questions": len(question_set.questions),
            "created_at": timestamp,
            "expires_at": expiry_time.isoformat(),
            "status": "scheduled",
            "link_locked": False
        }
        
        # Save to scheduled_assessments folder
        try:
            os.makedirs("scheduled_assessments", exist_ok=True)
            questions_file = f"scheduled_assessments/assessment_{session_id}_{timestamp}.json"
            
            print(f"💾 Saving assessment to: {questions_file}")
            with open(questions_file, 'w') as f:
                json.dump(questions_data, f, indent=2)
            print(f"✅ Assessment file saved successfully")
            
        except Exception as e:
            print(f"❌ Error saving assessment file: {e}")
            traceback.print_exc()
        
        # Generate assessment link
        assessment_link = f"http://48.216.217.84:5173/assessment/{session_id}"
        
        # Send email to candidate
        email_sent = send_assessment_email(candidate_email, candidate_name, assessment_link, job_role)
        
        print(f"✅ Assessment scheduled successfully for {candidate_name}")
        
        if email_sent:
            return {
                "message": "Assessment scheduled and email sent successfully",
                "session_id": session_id,
                "assessment_link": assessment_link,
                "candidate_name": candidate_name,
                "job_role": job_role,
                "total_questions": len(question_set.questions),
                "status": "scheduled"
            }
        else:
            return {
                "message": "Assessment scheduled but email sending failed",
                "session_id": session_id,
                "assessment_link": assessment_link,
                "candidate_name": candidate_name,
                "job_role": job_role,
                "total_questions": len(question_set.questions),
                "status": "scheduled_email_failed"
            }
    
    except Exception as e:
        print(f"❌ Error scheduling assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule assessment: {str(e)}")

@app.get("/assessment/{session_id}")
async def get_scheduled_assessment(session_id: str, request: Request):
    """Get scheduled assessment details by session ID with link security"""
    try:
        # Look for assessment file
        scheduled_dir = "scheduled_assessments"
        assessment_file = None
        
        if os.path.exists(scheduled_dir):
            for filename in os.listdir(scheduled_dir):
                if filename.startswith(f"assessment_{session_id}_"):
                    assessment_file = os.path.join(scheduled_dir, filename)
                    break
        
        if not assessment_file or not os.path.exists(assessment_file):
            raise HTTPException(status_code=404, detail="Assessment not found or expired")
        
        # Load assessment data
        with open(assessment_file, 'r') as f:
            assessment_data = json.load(f)
        
        # Check if link has expired (24 hours)
        expires_at = assessment_data.get("expires_at")
        created_at = assessment_data.get("created_at", "")
        
        if expires_at:
            expiry_time = datetime.fromisoformat(expires_at)
            current_time = datetime.now()
            if current_time > expiry_time:
                # Calculate how long ago it expired
                expired_hours = (current_time - expiry_time).total_seconds() / 3600
                print(f"🕐 Assessment {session_id} expired {expired_hours:.1f} hours ago")
                
                # Auto-cleanup expired assessment
                try:
                    os.remove(assessment_file)
                    print(f"🧹 Auto-removed expired assessment file")
                except:
                    pass
                
                raise HTTPException(
                    status_code=410, 
                    detail=f"Assessment link expired {expired_hours:.1f} hours ago. Links are valid for 24 hours only. Please request a new assessment link."
                )
        elif is_link_expired(created_at):
            # Calculate expiry time for better error message
            try:
                created_time = datetime.fromisoformat(created_at)
                expired_hours = (datetime.now() - created_time).total_seconds() / 3600 - 24
                
                # Auto-cleanup expired assessment
                try:
                    os.remove(assessment_file)
                    print(f"🧹 Auto-removed expired assessment file")
                except:
                    pass
                
                raise HTTPException(
                    status_code=410, 
                    detail=f"Assessment link expired {expired_hours:.1f} hours ago. Links are valid for 24 hours only. Please request a new assessment link."
                )
            except:
                raise HTTPException(
                    status_code=410, 
                    detail="Assessment link has expired. Links are valid for 24 hours only. Please request a new assessment link."
                )
        
        # Generate browser fingerprint
        current_fingerprint = generate_browser_fingerprint(request)
        
        # Check if link is locked to another browser (ENABLED for security)
        is_locked, fingerprint_exists = is_link_locked(session_id, current_fingerprint)
        
        # Block access if browser fingerprint doesn't match
        if is_locked and fingerprint_exists:
            print(f"🚫 BLOCKED: Different browser detected for session {session_id}")
            print(f"   Current fingerprint: {current_fingerprint[:8]}...")
            raise HTTPException(
                status_code=403, 
                detail="This assessment link has been locked to another browser session. Please use the same browser where you first opened the link."
            )
        
        # If not locked yet, lock it to current browser
        if not fingerprint_exists:
            lock_link_to_browser(session_id, current_fingerprint)
            print(f"🔒 Assessment {session_id} locked to browser: {current_fingerprint[:8]}...")
        else:
            print(f"✅ Assessment {session_id} accessed from authorized browser: {current_fingerprint[:8]}...")
        
        print(f"✅ Assessment {session_id} accessed successfully")
        
        # Return candidate info and questions (hide correct answers)
        questions_for_frontend = []
        for i, q in enumerate(assessment_data["questions"]):
            question_data = {
                "index": i,
                "question": q["question"],
                "options": q["options"]
                # Don't include correct_answer, explanation, or difficulty
            }
            questions_for_frontend.append(question_data)
        
        return {
            "session_id": session_id,
            "candidate_name": assessment_data.get("candidate_name"),
            "candidate_email": assessment_data.get("candidate_email"), 
            "job_role": assessment_data.get("job_role"),
            "questions": questions_for_frontend,
            "total_questions": len(questions_for_frontend),
            "time_limit_minutes": 25,
            "expires_at": assessment_data.get("expires_at"),
            "link_locked": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve assessment: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("prescreen_api:app", host="0.0.0.0", port=5174, reload=True)
