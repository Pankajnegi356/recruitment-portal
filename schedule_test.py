import requests
import json
import os
import re
from typing import List, Dict, Any

from pprint import pprint

def check_api_health():
    """Check if API is running"""
    print("🔍 Checking API Health...")
    
    try:
        response = requests.get("http://48.216.217.84:5174/health", timeout=30)
        if response.status_code == 200:
            health = response.json()
            print("✅ API is running")
            print(f"Status: {health.get('status')}")
            print(f"Model: {health.get('primary_model')}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API - make sure backend is running")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def schedule_assessment(candidate_email, job_role, candidate_name, additional_skills=None, experience_level=None):
    """Schedule assessment for a candidate"""
    
    url = "http://48.216.217.84:5174/schedule-assessment"
    
    payload = {
        "candidate_email": candidate_email,
        "job_role": job_role,
        "candidate_name": candidate_name
    }
    
    if additional_skills:
        payload["additional_skills"] = additional_skills
        
    if experience_level:
        payload["experience_level"] = experience_level
    
    try:
        print(f"🚀 Scheduling assessment for {candidate_name}...")
        print("⏳ Generating questions...")
        
        response = requests.post(url, json=payload, timeout=None)
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS!")
            print("="*50)
            print(f"Session ID: {result['session_id']}")
            print(f"Assessment Link: {result['assessment_link']}")
            print(f"Total Questions: {result.get('total_questions', 'N/A')}")
            print(f"Status: {result['status']}")
            print("="*50)
            print("\n📧 The candidate should receive an email with the assessment link!")
            
            return True
            
        else:
            print(f"\n❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the API. Make sure the backend is running on http://48.216.217.84:5174")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def schedule_candidate_assessment(candidate_name, candidate_email, job_role, skills, experience_level=None):
    """Schedule assessment with direct job role and optional experience level"""
    success = schedule_assessment(
        candidate_email=candidate_email,
        job_role=job_role,
        candidate_name=candidate_name,
        additional_skills=", ".join([str(skill) for skill in skills]) if skills else "",
        experience_level=experience_level
    )
    
    return success



def extract_job_role_from_response(raw_response: str) -> str:
    """Extract valid job role from Ollama response"""
    # Define valid job roles
    valid_roles = {
        "dataengineer": "Data Engineer",
        "backenddeveloper": "Backend Developer", 
        "frontenddeveloper": "Frontend Developer",
        "fullstackdeveloper": "Full Stack Developer",
        "devopsengineer": "DevOps Engineer",
        "machinelearningengineer": "Machine Learning Engineer",
        "datascientist": "Data Scientist",
        "softwareengineer": "Software Engineer",
        "qaengineer": "QA Engineer",
        "mobiledeveloper": "Mobile Developer"
    }
    
    # Clean and normalize the response
    cleaned_response = raw_response.lower().strip()
    cleaned_response = cleaned_response.replace('"', '').replace("'", '')
    
    # Check for exact matches first
    if cleaned_response in valid_roles:
        return valid_roles[cleaned_response]
    
    # Check if any valid role is contained in the response
    for role_key, role_value in valid_roles.items():
        if role_key in cleaned_response:
            return role_value
    
    # Check for common variations
    if any(word in cleaned_response for word in ['data', 'etl', 'pipeline', 'warehouse']):
        return "Data Engineer"
    elif any(word in cleaned_response for word in ['backend', 'server', 'api']):
        return "Backend Developer"
    elif any(word in cleaned_response for word in ['frontend', 'react', 'angular', 'javascript']):
        return "Frontend Developer"
    elif any(word in cleaned_response for word in ['devops', 'docker', 'kubernetes', 'infrastructure']):
        return "DevOps Engineer"
    elif any(word in cleaned_response for word in ['machine', 'learning', 'ml', 'ai']):
        return "Machine Learning Engineer"
    elif any(word in cleaned_response for word in ['scientist', 'analytics', 'statistics']):
        return "Data Scientist"
    elif any(word in cleaned_response for word in ['qa', 'quality', 'testing']):
        return "QA Engineer"
    elif any(word in cleaned_response for word in ['mobile', 'android', 'ios']):
        return "Mobile Developer"
    
    return None  # No valid role found

def extract_experience_level(profile_summary: str) -> str:
    """Extract experience level from profile summary text."""
    summary = profile_summary.lower() if profile_summary else ""
    # Match prescreen_api.py allowed values: intern, junior, mid_level, senior, lead
    if any(x in summary for x in ["team lead", "tech lead", "lead engineer", "leadership role", "principal", "head of", "team leader", "project lead"]):
        return "lead"
    if any(x in summary for x in ["senior", "5+ years", "6+ years", "7+ years", "8+ years", "9+ years", "10+ years", "more than 5", "over 5", "above 5"]):
        return "senior"
    if any(x in summary for x in ["mid-level", "mid level", "3-5 years", "4 years", "5 years", "3+ years", "4+ years", "3-4 years"]):
        return "mid_level"
    if any(x in summary for x in ["junior", "entry", "1-2 years", "2 years", "1 year", "fresh", "recent graduate", "new grad", "1+ years", "2+ years"]):
        return "junior"
    if any(x in summary for x in ["intern", "internship", "student", "trainee", "fresher", "entry-level"]):
        return "intern"
    # Fallback: if 'year' and a number is present
    import re
    match = re.search(r'(\d+)\s*year', summary)
    if match:
        years = int(match.group(1))
        if years >= 5:
            return "senior"
        elif years >= 3:
            return "mid_level"
        elif years >= 1:
            return "junior"
    return None

def detect_job_role_with_ollama(skills: list = None, summary: str = None) -> str:
    """Use Ollama to detect job role from skills or summary, with core subjects fallback."""
    
    # Prepare input for Ollama
    input_text = ""
    
    if skills and len(skills) > 0:
        input_text = f"Skills: {', '.join([str(skill) for skill in skills])}"
        print(f"🤖 Detecting job role from JD_Skills: {input_text[:100]}...")
    elif summary and summary.strip():
        input_text = f"Professional Summary: {summary.strip()}"
        print(f"🤖 Detecting job role from Summary: {input_text[:100]}...")
    else:
        print(f"🔄 No skills or summary available, using Core CS Subjects")
        return "Core Computer Science Subjects"
    
    try:
        # Ollama prompt for job role detection
        prompt = f"""
Based on the following information, choose the most appropriate job role from these STANDARD categories:

{input_text}

Available job roles (choose EXACTLY one single word):
- DataEngineer
- BackendDeveloper
- FrontendDeveloper
- FullStackDeveloper
- DevOpsEngineer
- MachineLearningEngineer
- DataScientist
- SoftwareEngineer
- QAEngineer
- MobileDeveloper

Respond with ONLY one word phrase from the above list. Answers MUST be exactly as shown.
Avoid additional words or phrases. Do not create new titles.
If skills involve databases, ETL, data pipelines, or data processing → DataEngineer
If skills involve servers, APIs, databases, backend frameworks → BackendDeveloper
If skills involve React, Angular, HTML, CSS, JavaScript → FrontendDeveloper
"""
        
        # Call Ollama API
        payload = {
            "model": "llama3.1:latest",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower temperature for more consistent results
                "num_predict": 50,   # Short response expected
                "stop": ["\n", "."]  # Stop at newline or period
            }
        }
        
        response = requests.post(
            "http://20.197.14.111:11434/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            raw_response = response_data.get('response', '').strip()
            
            # Extract only the job role
            job_role = extract_job_role_from_response(raw_response)
            
            if job_role:
                print(f"✅ Ollama detected job role: '{job_role}'")
                return job_role
            else:
                print(f"⚠️ Ollama returned invalid response: '{raw_response[:50]}...', using Core CS fallback")
                return "Core Computer Science Subjects"
        else:
            print(f"❌ Ollama API failed: {response.status_code}, using Core CS fallback")
            return "Core Computer Science Subjects"
            
    except Exception as e:
        print(f"❌ Error calling Ollama for job role detection: {e}")
        print(f"🔄 Using Core CS fallback")
        return "Core Computer Science Subjects"

def extract_job_role(profile_summary: str, skills: list) -> str:
    """New flow: Use Ollama to detect job role from skills or summary with fallback."""
    
    # Step 1: Try with JD_Skills if available
    if skills and len(skills) > 0:
        job_role = detect_job_role_with_ollama(skills=skills)
        if job_role != "Core Computer Science Subjects":
            return job_role
    
    # Step 2: Try with Summary if JD_Skills failed or unavailable
    if profile_summary and profile_summary.strip():
        job_role = detect_job_role_with_ollama(summary=profile_summary)
        if job_role != "Core Computer Science Subjects":
            return job_role
    
    # Step 3: Fallback to Core CS subjects
    print(f"🔄 Using Core Computer Science Subjects as final fallback")
    return "Core Computer Science Subjects"

def main():
    """Example main function - not used when called from your main script"""
    print("🚀 Schedule Test - This file is meant to be imported from your main script")
    print("Use schedule_assessments_from_output(output) function instead")

def schedule_assessments_from_output(output):
    """Take the output from skill matching and schedule assessments for all candidates"""
    print("🤖 Starting Assessment Scheduling...")
    
    # Check API Health
    if not check_api_health():
        print("❌ Cannot proceed with scheduling. Please start the backend.")
        return
    
    # Process candidates
    candidates = output if isinstance(output, list) else [output]
    successful_count = 0
    failed_count = 0
    
    for i, candidate in enumerate(candidates, 1):
        print(f"\n--- Processing Candidate {i}/{len(candidates)} ---")
        
        if not isinstance(candidate, dict):
            print(f"❌ Invalid candidate data format, skipping...")
            failed_count += 1
            continue
        
        # Extract candidate details from output
        candidate_name = candidate.get("Name", "Candidate")
        candidate_email = candidate.get("Email")
        skills = candidate.get("JD_Skills", [])
        profile_summary = candidate.get("Summary", "")
        ai_score = candidate.get("Score", "N/A")
        
        # Extract job role and experience level
        job_role = extract_job_role(profile_summary, skills)
        experience_level = extract_experience_level(profile_summary)
        
        if not candidate_email or not job_role:
            print(f"❌ Missing email ({candidate_email}) or job_role ({job_role}) for {candidate_name}")
            failed_count += 1
            continue
        
        print(f"📊 AI Score: {ai_score}")
        print(f"📧 Email: {candidate_email}")
        print(f"💼 Job Role: {job_role}")
        print(f"👤 Experience Level: {experience_level}")
        
        # Schedule assessment
        success = schedule_candidate_assessment(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            job_role=job_role,
            skills=skills,
            experience_level=experience_level
        )
        
        if success:
            successful_count += 1
        else:
            failed_count += 1
    
    # Final summary
    print(f"\n🎉 SCHEDULING SUMMARY")
    print("="*50)
    print(f"✅ Successful: {successful_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📧 Total emails sent: {successful_count}")
    print("="*50)

if __name__ == "__main__":
    main()
