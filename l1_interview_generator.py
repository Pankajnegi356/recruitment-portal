"""
L1 Interview Question Generator
Processes passed candidates from prescreening and generates L1 interview questions
"""

import json
import uuid
import os
import requests
from typing import List, Dict, Any
import pytz
from datetime import datetime, timedelta

# from python_backend.question_engine import generate_all_questions_single_call  # Not needed for L1

class L1InterviewGenerator:
    def __init__(self):
        self.data_dir = "../data"
        self.candidates_file = "../candidates.json"
        self.metadata_dir = "../metadata"
        
        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
    
    def load_passed_candidates(self) -> List[Dict]:
        """Load passed candidates from candidates.json"""
        try:
            with open(self.candidates_file, 'r') as f:
                data = json.load(f)
            
            # Filter only passed candidates
            passed_candidates = [
                candidate for candidate in data.get("results", [])
                if candidate.get("passed") == "pass"
            ]
            
            print(f"Found {len(passed_candidates)} passed candidates for L1 interviews")
            return passed_candidates
            
        except FileNotFoundError:
            print(f"Candidates file not found: {self.candidates_file}")
            return []
        except Exception as e:
            print(f"Error loading candidates: {e}")
            return []
    
    def extract_skills_from_job_role(self, job_role: str) -> List[str]:
        """Extract relevant skills from job role for question generation"""
        job_role_lower = job_role.lower()
        
        # Map job roles to relevant skills
        skill_mappings = {
            "data scientist": ["python", "machine learning", "statistics", "pandas", "numpy", "sql"],
            "ml engineer": ["machine learning", "python", "tensorflow", "pytorch", "deployment", "docker"],
            "backend developer": ["python", "apis", "databases", "sql", "frameworks", "microservices"],
            "frontend developer": ["javascript", "react", "css", "html", "typescript", "ui/ux"],
            "full stack developer": ["javascript", "python", "react", "apis", "databases", "sql"],
            "devops engineer": ["docker", "kubernetes", "ci/cd", "aws", "linux", "monitoring"],
            "software engineer": ["programming", "algorithms", "data structures", "system design", "testing"]
        }
        
        # Find matching skills
        for role_key, skills in skill_mappings.items():
            if role_key in job_role_lower:
                return skills
        
        # Default skills for unknown roles
        return ["programming", "algorithms", "problem solving", "system design"]
    
    def generate_l1_questions_direct(self, job_role: str, candidate_email: str) -> List[Dict]:
        """Generate exactly 25 L1 interview questions using direct API call"""
        try:
            print(f"Generating L1 questions for {job_role} role...")
            
            # Extract skills from job role
            skills = self.extract_skills_from_job_role(job_role)
            skills_text = ", ".join(skills)
            
            # Create L1-specific prompt for exactly 25 questions
            prompt = f"""
Generate exactly 25 interview questions for a {job_role} position (L1 Technical Interview) based on these skills: {skills_text}

Requirements:
- 7 EASY questions (basic concepts, definitions, simple explanations)
- 13 MEDIUM questions (practical scenarios, implementation approaches, real-world usage)  
- 5 HARD questions (complex case studies, system design scenarios, detailed problem-solving)

QUESTION STYLE GUIDELINES:
EASY: Simple, straightforward questions about basic concepts
- "What is [technology]?"
- "Define [concept] and its purpose"
- "Explain the basic difference between [A] and [B]"

MEDIUM: Practical, implementation-focused questions
- "How would you implement [feature] using [technology]?"
- "Describe a scenario where you would use [approach]"
- "Explain the process of [technical task]"

HARD: Complex scenario-based questions requiring detailed explanations
- "Design a complete system for [complex business requirement]"
- "You have a company with [specific constraints] - architect a solution"
- "Analyze and solve this complex scenario: [detailed business case]"

Format each question as:
DIFFICULTY: question text

Example:
EASY: What is Python and how is it used in data science?
MEDIUM: How would you handle missing data in a large dataset?
HARD: Design a recommendation system for an e-commerce platform with millions of users.

Generate exactly 25 questions total (7 easy + 13 medium + 5 hard).
"""

            # Make API call to Ollama
            payload = {
                "model": "llama3.1:latest",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 2000
                }
            }
            
            print("🚀 Calling Ollama API for L1 questions...")
            response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
            
            if response.status_code != 200:
                print(f"❌ Ollama API error: {response.status_code}")
                return []
            
            response_data = response.json()
            llm_response = response_data.get("response", "")
            
            print(f"🔍 LLM Response Preview: {llm_response[:100]}...")
            
            # Parse the questions from LLM response
            print(f"🔍 Full LLM Response:\n{llm_response}")
            questions = self.parse_l1_questions(llm_response, job_role)
            
            print(f"📊 Parsed {len(questions)} questions from LLM response")
            
            # Ensure we have exactly the right distribution
            easy_questions = [q for q in questions if q.get("difficulty") == "easy"][:7]
            medium_questions = [q for q in questions if q.get("difficulty") == "medium"][:13]
            hard_questions = [q for q in questions if q.get("difficulty") == "hard"][:5]
            
            final_questions = easy_questions + medium_questions + hard_questions
            
            print(f"Generated {len(final_questions)} questions: {len(easy_questions)} easy, {len(medium_questions)} medium, {len(hard_questions)} hard")
            return final_questions
            
        except Exception as e:
            print(f"Error generating L1 questions: {e}")
            return []
    
    def parse_l1_questions(self, llm_response: str, job_role: str) -> List[Dict]:
        """Parse L1 questions from LLM response"""
        import re
        questions = []
        lines = llm_response.strip().split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Look for lines that start with number and difficulty levels
            # Pattern: "1. EASY: question text" or "EASY: question text"
            pattern = r'^(?:\d+\.\s*)?(EASY|MEDIUM|HARD):\s*(.+)'
            match = re.match(pattern, line, re.IGNORECASE)
            
            if match:
                difficulty = match.group(1).strip().lower()
                question_text = match.group(2).strip()
                
                if question_text:
                    questions.append({
                        "id": str(uuid.uuid4()),
                        "question": question_text,
                        "difficulty": difficulty,
                        "job_role": job_role,
                        "ans": "",
                        "question_number": len(questions) + 1
                    })
        
        return questions
    
    def save_l1_session(self, session_id: str, candidate_data: Dict, questions: List[Dict]) -> str:
        """Save L1 interview session data to file with scheduled 24-hour access"""
        try:
            from datetime import datetime, timedelta
            
            # Read scheduled date from candidate data
            scheduled_date_str = candidate_data.get("interview_date")  # Format: "YYYY-MM-DD"
            if not scheduled_date_str:
                raise ValueError("Scheduled interview date not provided for candidate")

            # Convert to datetime at start of day
            scheduled_start = datetime.fromisoformat(scheduled_date_str)  # 00:00:00 of that day
            scheduled_end = scheduled_start + timedelta(days=1)           # 24 hours later

            session_data = {
                "session_id": session_id,
                "interview_type": "L1",
                "candidate_name": candidate_data.get("candidate_name"),
                "candidate_email": candidate_data.get("candidate_email"),
                "job_role": candidate_data.get("job_role"),
                "prescreening_session_id": candidate_data.get("session_id"),
                "prescreening_score": f"{candidate_data.get('correct_answers', 0)}/{candidate_data.get('total_questions', 25)}",
                "questions": questions,
                "total_questions": len(questions),
                "difficulty_distribution": {
                    "easy": len([q for q in questions if q.get("difficulty") == "easy"]),
                    "medium": len([q for q in questions if q.get("difficulty") == "medium"]),
                    "hard": len([q for q in questions if q.get("difficulty") == "hard"])
                },
                "created_at": datetime.now().isoformat(),
                "scheduled_start": scheduled_start.isoformat(),
                "scheduled_end": scheduled_end.isoformat(),
                "status": "pending"
            }

            # Save to data directory
            filename = f"l1_interview_{session_id}.json"
            filepath = os.path.join(self.data_dir, filename)

            with open(filepath, 'w') as f:
                json.dump(session_data, f, indent=2)

            print(f"Saved L1 session: {filepath}")
            return filepath

        except Exception as e:
            print(f"Error saving L1 session: {e}")
        return ""

    
    def generate_interview_link(self, l1_session_id: str, scheduled_date: str) -> str:
        """
        Generate a time-bound interview link for the candidate.
        
        Args:
            l1_session_id (str): Unique session ID
            scheduled_date (str): Interview scheduled date in YYYY-MM-DD format
        
        Returns:
            str: Interview link (active only during valid time window)
        """
        # Convert scheduled_date to datetime
        tz = pytz.timezone("Asia/Kolkata")  # adjust if needed
        start_time = tz.localize(datetime.strptime(scheduled_date, "%Y-%m-%d"))
        created_at = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        expires_at = created_at + timedelta(days=1)  # next day midnight
        
        # Save session metadata
        session_data = {
            "session_id": l1_session_id,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        self.save_session_metadata(l1_session_id, session_data)
        
        # Generate dynamic interview link using env_config
        from env_config import get_frontend_ngrok_url
        frontend_url = get_frontend_ngrok_url()
        return f"{frontend_url}/interview/{l1_session_id}"

    def save_session_metadata(self, session_id: str, metadata: Dict[str, Any]) -> str:
        """
        Save session metadata (like created_at, expires_at) to a JSON file.
        Returns the path of the saved file.
        """
        try:
            filepath = os.path.join(self.metadata_dir, f"{session_id}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            print(f"💾 Session metadata saved: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Error saving session metadata for {session_id}: {e}")
            return ""

    # ----------------------------
    # Load session metadata
    # ----------------------------
    def load_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """
        Load session metadata from JSON file.
        Returns a dictionary if found, otherwise empty dict.
        """
        try:
            filepath = os.path.join(self.metadata_dir, f"{session_id}.json")
            if not os.path.exists(filepath):
                print(f"⚠️ Metadata file not found for session {session_id}")
                return {}

            with open(filepath, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            return metadata
        except Exception as e:
            print(f"❌ Error loading session metadata for {session_id}: {e}")
            return {}
        
    def process_all_candidates(self) -> Dict[str, Any]:
        """Process all passed candidates and generate L1 interviews"""
        passed_candidates = self.load_passed_candidates()
        
        if not passed_candidates:
            return {
                "status": "error",
                "message": "No passed candidates found",
                "results": []
            }
        
        results = []
        
        for candidate in passed_candidates:
            try:
                # Generate unique session ID for L1 interview
                l1_session_id = str(uuid.uuid4())
                
                # Generate questions
                questions = self.generate_l1_questions_direct(
                    job_role=candidate["job_role"],
                    candidate_email=candidate["candidate_email"]
                )
                
                if not questions:
                    print(f"Failed to generate questions for {candidate['candidate_email']}")
                    continue
                
                # Save L1 session
                session_file = self.save_l1_session(l1_session_id, candidate, questions)
                
                if session_file:
                    # Generate interview link
                    scheduled_date = candidate.get("interview_date", "2025-08-25")  # Default or from candidate data
                    interview_link = self.generate_interview_link(l1_session_id, scheduled_date)
                    
                    result = {
                        "candidate_name": candidate["candidate_name"],
                        "candidate_email": candidate["candidate_email"],
                        "job_role": candidate["job_role"],
                        "l1_session_id": l1_session_id,
                        "interview_link": interview_link,
                        "questions_generated": len(questions),
                        "session_file": session_file,
                        "prescreening_score": f"{candidate['correct_answers']}/{candidate['total_questions']}"
                    }
                    
                    results.append(result)
                    print(f"✅ L1 interview created for {candidate['candidate_name']}")
                
            except Exception as e:
                print(f"Error processing candidate {candidate.get('candidate_email', 'unknown')}: {e}")
                continue
        
        return {
            "status": "success",
            "message": f"Generated L1 interviews for {len(results)} candidates",
            "total_candidates": len(passed_candidates),
            "successful_generations": len(results),
            "results": results
        }

def main():
    """Main function to run L1 interview generation"""
    print("=== L1 Interview Generator ===")
    print("Processing passed candidates from prescreening...")
    
    generator = L1InterviewGenerator()
    results = generator.process_all_candidates()
    
    print("\n=== Generation Results ===")
    print(f"Status: {results['status']}")
    print(f"Message: {results['message']}")
    
    if results["results"]:
        print("\n=== Generated L1 Interview Links ===")
        for result in results["results"]:
            print(f"\nCandidate: {result['candidate_name']}")
            print(f"Email: {result['candidate_email']}")
            print(f"Job Role: {result['job_role']}")
            print(f"L1 Session ID: {result['l1_session_id']}")
            print(f"Interview Link: {result['interview_link']}")
            print(f"Questions: {result['questions_generated']}")
            print(f"Prescreening Score: {result['prescreening_score']}")
            print("-" * 50)
    
    return results

if __name__ == "__main__":
    main()
