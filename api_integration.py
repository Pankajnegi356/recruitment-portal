# import os
# import base64
# import json
# import time
# import re
# from datetime import datetime
# import pytz
# import requests  
# import secrets   
# import string

# # To manage environment variables for the API key, you can use python-dotenv
# # pip install python-dotenv
# # from dotenv import load_dotenv
# # load_dotenv() # This line loads the .env file

# # Import the ollama library
# import ollama

# # --- Configuration ---
# # --- Local LLM Configuration ---
# LLM_MODEL_NAME = "llama3" # This should match the model you pulled with Ollama

# # --- Email Configuration ---
# # The interviewer's email is needed to know where to send the initial outreach.
# INTERVIEWER_EMAIL = "rubberband188@gmail.com"

# # --- API Endpoint Configuration ---
# BASE_URL = "http://48.216.217.84:5002"
# SEND_EMAIL_URL = f"{BASE_URL}/send-email"
# CHECK_INBOX_URL = f"{BASE_URL}/check-inbox"

# # --- State and Data Files ---
# CANDIDATES_FILE = 'candidates.json'
# STATE_FILE_NEGOTIATING = 'negotiating_threads.json' # We'll still use this to track conversations
# STATE_FILE_CONFIRMED = 'confirmed_interviews.json'



# def create_dynamic_meeting_link():
#     """
#     Generates a unique meeting link using the public Jitsi Meet service.
#     This creates a real, usable video call link.
#     """
#     # Generate a secure, random, URL-friendly string for the room name
#     room_name = secrets.token_urlsafe(16)
#     return f"https://meet.jit.si/{room_name}"


# def get_current_context_string():
#     """
#     Returns a formatted string with the current date, and time.
#     """
#     # This now returns the specific context provided by the user.
#     return "Current time is Sunday, July 27, 2025 at 5:23 PM IST."


# def send_email_via_api(to_email, subject, body):
#     """
#     Sends an email using the provided Flask API endpoint.
#     """
#     print(f"Sending email via API to: {to_email}")
#     data = {
#         "to": to_email,
#         "subject": subject,
#         "content": body
#     }
#     try:
#         response = requests.post(SEND_EMAIL_URL, data=data)
#         response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
#         print(f"SUCCESS: Email sent to {to_email}. Status Code: {response.status_code}")
#         # The API response might contain useful info, like a message ID.
#         # For now, we just confirm it was sent.
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         print(f'ERROR: An error occurred sending email via API: {e}')
#         return None

# def check_inbox_via_api():
#     """
#     Checks for the latest unread emails using the Flask API endpoint.
#     """
#     print("Checking for new emails via API...")
#     try:
#         response = requests.get(CHECK_INBOX_URL)
#         response.raise_for_status()
#         emails = response.json()
#         print(f"Found {len(emails)} new email(s).")
#         return emails
#     except requests.exceptions.RequestException as e:
#         print(f"ERROR: An error occurred checking inbox via API: {e}")
#         return []
#     except json.JSONDecodeError:
#         print("ERROR: Failed to decode JSON from inbox response. Response was:")
#         print(response.text)
#         return []


# def generate_initial_outreach_with_llm(candidate_name):
#     """
#     Uses the local LLM to generate a crisp, initial email to the interviewer.
#     """
#     print(f"Generating initial outreach email content for {candidate_name} with local model: {LLM_MODEL_NAME}...")

#     system_prompt = f"""You are an expert AI assistant. Your task is to write a polite, very crisp, and professional email to an Interviewer to ask for their availability. Respond ONLY with a valid JSON object: {{"subject": "...", "body": "..."}}"""
#     user_prompt = f"""{get_current_context_string()}\n\nDraft an extremely brief email to the interviewer. Ask them to provide a few available time slots for an interview with a new candidate, {candidate_name}. Sign off as 'The Scheduling Coordinator'."""

#     try:
#         response = ollama.chat(model=LLM_MODEL_NAME, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], options={"temperature": 0.2}, format="json")
#         return json.loads(response['message']['content'])
#     except Exception as e:
#         print(f"An error occurred calling the local Ollama model for initial outreach: {e}")
#         return {"error": str(e)}

# def is_interview_confirmed_with_llm(thread_content):
#     """
#     Analyzes the email thread to determine if a final confirmation has been made.
#     """
#     system_prompt = f"""You are a scheduling analyst. Your only job is to determine if an interview has been confirmed. A time is "CONFIRMED" only after one party proposes a time and the other party explicitly agrees to that exact time. A counter-proposal is NOT a confirmation.

# Respond with ONLY a JSON object with two keys: "confirmed" (true or false) and "time" (the confirmed time in "YYYY-MM-DD HH:MM" format if confirmed, otherwise null).
# """
#     user_prompt = f"""{get_current_context_string()}\n\nAnalyze the full thread below and determine if a final confirmation has been made.\n\n--- THREAD START ---\n{thread_content}\n--- THREAD END ---"""

#     try:
#         response = ollama.chat(model=LLM_MODEL_NAME, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], options={"temperature": 0.0}, format="json")
#         return json.loads(response['message']['content'])
#     except Exception as e:
#         print(f"An error occurred during confirmation analysis: {e}")
#         return {"confirmed": False, "time": None}

# def generate_email_content_with_llm(status, last_email_body, recipient, candidate_name, confirmed_time=None, meeting_link=None):
#     """
#     Generates a crisp, professional email reply or confirmation based on the determined status.
#     """
#     persona = "The Scheduling Team" if recipient == "candidate" else "The Scheduling Coordinator"
#     recipient_title = "candidate" if recipient == "candidate" else "interviewer"
#     other_party_title = f"the interviewer" if recipient == "candidate" else f"the candidate ({candidate_name})"

#     system_prompt = f"""You are an expert AI assistant drafting a scheduling email. Your task is to write a very crisp, professional, and anonymous email based on the provided context.
# - Your recipient is the **{recipient_title}**.
# - You must refer to the other party ONLY as "**{other_party_title}**".
# - You must sign off as "**{persona}**".
# - Respond ONLY with a valid JSON object: {{"subject": "...", "body": "..."}}"""

#     if status == "AWAITING_CANDIDATE_RESPONSE":
#         user_prompt = f"The interviewer has proposed the following for the interview with you:\n\n---\n{last_email_body}\n---\n\nDraft a brief email to the candidate. Relay the proposed times and ask them to either confirm one or suggest alternatives if they are unavailable."
#     elif status == "AWAITING_INTERVIEWER_RESPONSE":
#         user_prompt = f"The candidate, {candidate_name}, has replied with the following message regarding scheduling:\n\n---\n{last_email_body}\n---\n\nDraft a brief email to the interviewer. Relay the candidate's response and ask for confirmation or next steps."
#     elif status == "CONFIRMED":
#         if not meeting_link:
#             return {"error": "Meeting link is required for confirmation emails."}
#         user_prompt = f"The interview with {other_party_title} has been confirmed for {confirmed_time}. Draft a brief, professional confirmation email to the {recipient_title}. **Crucially, you must include the following meeting link in the email body:** {meeting_link}"
#     else:
#         return {"error": "Invalid status for reply generation."}

#     try:
#         response = ollama.chat(model=LLM_MODEL_NAME, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], options={"temperature": 0.1}, format="json")
#         return json.loads(response['message']['content'])
#     except Exception as e:
#         print(f"An error occurred during email generation: {e}")
#         return {"error": str(e)}

# def load_json_state(filename):
#     if os.path.exists(filename):
#         with open(filename, 'r') as f:
#             try: return json.load(f)
#             except json.JSONDecodeError: return {} if 'threads' in filename else []
#     return {} if 'threads' in filename else []

# def save_json_state(data, filename):
#     with open(filename, 'w') as f:
#         json.dump(data, f, indent=2)

# def load_and_validate_candidate():
#     """
#     Loads the first candidate from candidates.json and checks if they passed.
#     Returns candidate details if valid, otherwise None.
#     """
#     try:
#         with open(CANDIDATES_FILE, 'r') as f:
#             data = json.load(f)
#             candidates = data.get("results", [])
#             if not candidates:
#                 print("No candidates found in candidates.json.")
#                 return None

#             candidate = candidates[0]

#             if candidate.get("passed") == "pass":
#                 name = candidate.get("candidate_name")
#                 email = candidate.get("candidate_email")
#                 if name and email:
#                     print(f"Found valid candidate who passed: {name} ({email})")
#                     return {"name": name, "email": email}
#                 else:
#                     print("Candidate data is missing name or email.")
#                     return None
#             else:
#                 print(f"Candidate {candidate.get('candidate_name')} did not pass the assessment. Skipping.")
#                 return None

#     except (FileNotFoundError, json.JSONDecodeError) as e:
#         print(f"Error reading or parsing {CANDIDATES_FILE}: {e}. Exiting.")
#         return None

# def process_incoming_email(email_data, negotiating_threads, confirmed_candidates):
#     """
#     Processes a single email received from the API.
#     This replaces the 'process_thread' logic.
#     """
#     sender = email_data.get('from', '').lower()
#     subject = email_data.get('subject', '')
#     body = email_data.get('body', '')
    

#     candidate_email = None
#     thread_id = None # Using subject as a pseudo thread_id
#     for c_email, t_id in negotiating_threads.items():
#         if t_id in subject:
#             candidate_email = c_email
#             thread_id = t_id
#             break
            
#     if not candidate_email:
#         print(f"Could not associate email from '{sender}' with any ongoing negotiation. Skipping.")
#         return

#     # Reload candidate details
#     candidate = load_and_validate_candidate()
#     if not candidate or candidate['email'] != candidate_email:
#         print("Could not validate candidate for this email. Skipping.")
#         return
        
#     candidate_name = candidate['name']
    
#     print(f"\n--- Processing Email for Candidate: {candidate_name} ---")
    
#     # We don't have the full thread from the API, so we'll have to make decisions
#     # based on the last message and who sent it.
#     # For a more robust system, we would need to save the conversation history.
    
#     # For now, we'll just use the body of the last email as the 'full conversation'
#     # for the confirmation check. This is a limitation of the current API design.
#     full_conversation = f"From: {sender}\n\n{body}"
    
#     print("Analyzing email for confirmation...")
#     confirmation_check = is_interview_confirmed_with_llm(full_conversation)

#     if confirmation_check.get("confirmed"):
#         c = 1
#         print(f"✅✅ Interview CONFIRMED for {candidate_name}! Generating real meeting link from meet.jit.si...")
#         confirmed_time = confirmation_check.get("time")
        
#         # Dynamically create a unique, real meeting link for this confirmed interview
#         new_meeting_link = create_dynamic_meeting_link()
#         print(f"Generated meeting link: {new_meeting_link}")

#         candidate_email_content = generate_email_content_with_llm("CONFIRMED", "", "candidate", candidate_name, confirmed_time, meeting_link=new_meeting_link)
#         if "error" not in candidate_email_content:
#             send_email_via_api(candidate_email, candidate_email_content["subject"], candidate_email_content["body"])
#         else:
#             print(f"ERROR generating candidate confirmation: {candidate_email_content['error']}")

#         interviewer_email_content = generate_email_content_with_llm("CONFIRMED", "", "interviewer", candidate_name, confirmed_time, meeting_link=new_meeting_link)
#         if "error" not in interviewer_email_content:
#             send_email_via_api(INTERVIEWER_EMAIL, interviewer_email_content["subject"], interviewer_email_content["body"])
#         else:
#             print(f"ERROR generating interviewer confirmation: {interviewer_email_content['error']}")

#         # Update state
#         confirmed_candidates.add(candidate_email)
#         if candidate_email in negotiating_threads:
#             del negotiating_threads[candidate_email]
#         save_json_state(negotiating_threads, STATE_FILE_NEGOTIATING)
#         save_json_state(list(confirmed_candidates), STATE_FILE_CONFIRMED)
#         print(f"Successfully confirmed and saved state for {candidate_name}.")
#         return

#     print("Interview not confirmed. Determining next step...")
#     status = ""
#     if INTERVIEWER_EMAIL in sender:
#         status = "AWAITING_CANDIDATE_RESPONSE"
#     elif candidate_email in sender:
#         status = "AWAITING_INTERVIEWER_RESPONSE"
#     else:
#         print(f"Unknown sender: {sender}. No action taken.")
#         return

#     print(f"Status determined: {status}")

#     recipient_type = "candidate" if status == "AWAITING_CANDIDATE_RESPONSE" else "interviewer"
#     recipient_email = candidate_email if recipient_type == "candidate" else INTERVIEWER_EMAIL

#     print(f"Generating reply for {recipient_type}...")
#     reply_content = generate_email_content_with_llm(status, body, recipient_type, candidate_name)

#     if "error" in reply_content or not all(k in reply_content for k in ["subject", "body"]):
#         print(f"Failed to generate valid email reply: {reply_content}")
#         return
        
#     # Add the original subject (our thread_id) to maintain context
#     new_subject = f"Re: {thread_id}"
#     send_email_via_api(recipient_email, new_subject, reply_content["body"])
#     print(f"Reply sent. Negotiation continues for {candidate_name}.")


# def main():
#     global c #to stop the script after 1 confrimation
#     print("🚀 Starting AI Scheduling Mediator (API Version)...")

#     candidate = load_and_validate_candidate()
#     if not candidate:
#         print("No valid candidate to process. Exiting.")
#         c = 1
#         return

#     candidate_email = candidate["email"]
#     candidate_name = candidate["name"]

#     negotiating_threads = load_json_state(STATE_FILE_NEGOTIATING)
#     confirmed_candidates = set(load_json_state(STATE_FILE_CONFIRMED))

#     if candidate_email in confirmed_candidates:
#         c = 1
#         print(f"Candidate {candidate_name} already has a confirmed interview. No action needed.")
#         return

#     # --- INITIATION MODE ---
#     # If we aren't already talking to this candidate, start the conversation.
#     if candidate_email not in negotiating_threads:
#         print(f"\nFound new candidate: {candidate_name} ({candidate_email}). Initiating contact...")
#         outreach_content = generate_initial_outreach_with_llm(candidate_name)
#         if "error" in outreach_content or not all(k in outreach_content for k in ["subject", "body"]):
#             print(f"Failed to generate valid outreach email for {candidate_name}.")
#             return

#         # We will use the subject as a pseudo-thread ID to track the conversation
#         thread_id = outreach_content["subject"]
#         sent_message = send_email_via_api(INTERVIEWER_EMAIL, thread_id, outreach_content["body"])

#         if sent_message:
#             print(f"Conversation started for {candidate_name}. Tracking with subject: '{thread_id}'")
#             negotiating_threads[candidate_email] = thread_id
#             save_json_state(negotiating_threads, STATE_FILE_NEGOTIATING)
#         else:
#             print("Failed to initiate conversation. Exiting.")
#             return

#     # --- MONITORING MODE ---
#     # Check for new emails and process them.
#     print(f"\nMonitoring ongoing negotiations...")
#     new_emails = check_inbox_via_api()

#     if not new_emails:
#         print("No new emails to process. All done for now. ✨")
#         return

#     for email_data in new_emails:
#         process_incoming_email(email_data, negotiating_threads, confirmed_candidates)
#         # The state files are saved within process_incoming_email if a confirmation occurs

# # if __name__ == '__main__':
# #     main()


# if __name__ == '__main__':
#     POLLING_INTERVAL_SECONDS = 60 
#     c = 0
#     print("Starting automatic email scheduling agent...")
#     try:
#         while (c==0):
#             main()
#             print(f"\n--- Check complete. Waiting for {POLLING_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop. ---")
#             time.sleep(POLLING_INTERVAL_SECONDS)

#             if(c==1):
#                 print("\n--- Interview confirmed. Stopping script. ---")
#                 break
#     except KeyboardInterrupt:
#         print("\nScript stopped by user. Goodbye!")



# ================================================================
# ================================================================
# ================================================================
import os
import base64
import json
import time
import re
from datetime import datetime
import pytz
import requests  
import secrets   
import string
from python_backend.l1_interview_generator import L1InterviewGenerator  
import uuid
import mysql.connector

l1_generator = L1InterviewGenerator()

# Import the ollama library
from python_backend.config import OLLAMA_API_URL, OLLAMA_MODEL
from python_backend.env_config import get_frontend_ngrok_url, get_backend_ngrok_url

# --- Database Configuration ---
DB_CONFIG = {
    'host': '48.216.217.84',
    'port': 3306,
    'user': 'appuser',
    'password': 'strongpassword',
    'database': 'recruitment_portal',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# --- Email Configuration ---
INTERVIEWER_EMAIL = "notifications.veersa@gmail.com"

# --- API Endpoint Configuration ---
BASE_URL = "http://48.216.217.84:5002"
SEND_EMAIL_URL = f"{BASE_URL}/send-email"
CHECK_INBOX_URL = f"{BASE_URL}/check-inbox"

# --- State and Data Files ---
STATE_FILE_NEGOTIATING = 'negotiating_threads.json' # We'll still use this to track conversations
STATE_FILE_CONFIRMED = 'confirmed_interviews.json'


# PHASE 2: Database Helper Functions
def get_db_connection():
    """Establish MySQL database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None

def get_candidates_for_l1_email():
    """Get candidates ready for L1 interview email (status 3)"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT name, email FROM candidates WHERE status = 3")
        candidates = cursor.fetchall()
        print(f"🔍 Found {len(candidates)} candidates with status 3 (ready for L1 email)")
        return candidates
    except mysql.connector.Error as e:
        print(f"❌ Error fetching candidates: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

def mark_email_sent(email: str):
    """Update candidate status from 3 to 4 (negotiating interview date) after email sent"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE candidates SET status = 4, updated_at = NOW() WHERE email = %s",
            (email,)
        )
        connection.commit()
        print(f"✅ Updated {email} status to 4 (negotiating interview date)")
        return True
    except mysql.connector.Error as e:
        print(f"❌ Error updating email status: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def get_candidate_by_email(email):
    """Get candidate from database by email address"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT name, email, status FROM candidates WHERE email = %s", (email,))
        candidate = cursor.fetchone()
        return candidate
    except mysql.connector.Error as e:
        print(f"❌ Error fetching candidate: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def process_incoming_email(email_data):
    """
    Processes a single email received from the API.
    Uses database status instead of negotiating_threads.json
    """
    
    sender_email = email_data.get('sender', '') or email_data.get('from', '')
    subject = email_data.get('subject', '')
    body = email_data.get('body', '')

    print(f"🔍 DEBUG: Raw email data: sender='{sender_email}', subject='{subject}', body preview='{body[:50]}...'")

    # Extract email from sender (handle multiple formats)
    import re
    candidate_email = ""
    
    if sender_email:
        # Try format: "Name <email@domain.com>"
        email_match = re.search(r'<([^>]+)>', sender_email)
        if email_match:
            candidate_email = email_match.group(1).strip()
        else:
            # Try direct email format
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender_email)
            if email_match:
                candidate_email = email_match.group(0).strip()
            else:
                candidate_email = sender_email.strip()

    print(f"🔍 DEBUG: Extracted email: '{candidate_email}'")

    if not candidate_email:
        print(f"❌ Could not extract valid email from sender: '{sender_email}'. Skipping.")
        return

    # Check if this email belongs to a candidate with status 4 (negotiating interview date)
    candidate = get_candidate_by_email(candidate_email)
    if not candidate:
        print(f"❌ Could not find candidate with email '{candidate_email}' in database. Skipping.")
        return
    
    if candidate['status'] != 4:
        print(f"Candidate {candidate['name']} has status {candidate['status']}, not 4 (negotiating interview date). Skipping.")
        return

    candidate_name = candidate['name']
    
    print(f"\n--- Processing Email for Candidate: {candidate_name} ---")
    
    # Check if email indicates confirmation
    confirmation_keywords = ["yes", "confirm", "accept", "agree", "ok", "sure", "sounds good", "good", "available"]
    if any(keyword in body.lower() for keyword in confirmation_keywords):
        print(f"\n🎉 CONFIRMATION detected from {candidate_email}!")
        print(f"Subject: {subject}")
        print(f"Body snippet: {body[:100]}...")
        
        # Generate L1 interview questions and create session
        l1_session_id = str(uuid.uuid4())
        interview_link = get_dynamic_interview_link(l1_session_id)
        
        print(f"🔄 Generating AI questions for {candidate_name}...")
        questions = l1_generator.generate_l1_questions_direct("Data Science", candidate_email)
        
        if not questions:
            print("❌ Failed to generate questions with AI, using fallback questions")
            questions = [
                {"id": str(uuid.uuid4()), "question": "What is Data Science and its key components?", "difficulty": "easy", "job_role": "Data Science", "ans": "", "question_number": 1},
                {"id": str(uuid.uuid4()), "question": "Tell me about your experience in data analysis.", "difficulty": "easy", "job_role": "Data Science", "ans": "", "question_number": 2},
                {"id": str(uuid.uuid4()), "question": "How would you handle missing data in a dataset?", "difficulty": "medium", "job_role": "Data Science", "ans": "", "question_number": 3},
                {"id": str(uuid.uuid4()), "question": "Describe your approach to building a machine learning model.", "difficulty": "medium", "job_role": "Data Science", "ans": "", "question_number": 4},
                {"id": str(uuid.uuid4()), "question": "Design a recommendation system for an e-commerce platform with millions of users.", "difficulty": "hard", "job_role": "Data Science", "ans": "", "question_number": 5}
            ]
        
        # Create consolidated session data
        consolidated_session_data = {
            "session_id": l1_session_id,
            "interview_type": "L1",
            "status": "confirmed",
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "job_role": "Data Science",
            "questions": questions,
            "total_questions": len(questions),
            "interview_link": interview_link,
            "confirmed_at": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        # Save session file
        session_filepath = os.path.join("data", f"l1_interview_{l1_session_id}.json")
        os.makedirs("data", exist_ok=True)
        with open(session_filepath, 'w') as f:
            json.dump(consolidated_session_data, f, indent=2)
        
        print(f"✅ Created session file: {session_filepath}")
        print(f"🔗 Interview link: {interview_link}")
        
        # Send confirmation email with interview link
        confirmation_subject = f"L1 Interview Scheduled - {candidate_name}"
        confirmation_body = f"""Dear {candidate_name},

Thank you for confirming your availability! Your L1 technical interview has been scheduled.

Interview Details:
- Interview Link: {interview_link}
- Duration: 45 minutes
- Format: Technical Q&A

Please join the interview using the link above at your scheduled time.

Best regards,
Veersa Recruitment Team"""
        
        if send_email_via_api(candidate_email, confirmation_subject, confirmation_body):
            print(f"✅ Confirmation email sent to {candidate_name}")
        else:
            print(f"❌ Failed to send confirmation email to {candidate_name}")
        
        # Update database status from 4 to 5 (interview confirmed and link sent)
        if update_candidate_status(candidate_email, 5):
            print(f"✅ Updated {candidate_name} status to 5 (interview confirmed and link sent)")
        else:
            print(f"❌ Failed to update {candidate_name} status to 5")
        
        print(f"✅ Successfully confirmed interview for {candidate_name} with session ID: {l1_session_id}")
        return
    
    print("No confirmation detected in email. No action taken.")

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
        return True
    except mysql.connector.Error as e:
        print(f"❌ Error updating status: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def send_email_via_api(to_email, subject, body):
    """Send email using the Flask API endpoint"""
    try:
        payload = {
            "to": to_email,
            "subject": subject,
            "body": body
        }
        print(f"🔍 DEBUG: Sending email to {SEND_EMAIL_URL}")
        print(f"🔍 DEBUG: Payload: {payload}")
        
        response = requests.post(SEND_EMAIL_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ Email sent successfully to {to_email}")
            return True
        else:
            print(f"❌ Failed to send email: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def check_inbox_via_api():
    """Check for new emails using the Flask API endpoint"""
    try:
        response = requests.get(CHECK_INBOX_URL)
        if response.status_code == 200:
            response_data = response.json()
            # Handle both list and dict responses
            if isinstance(response_data, list):
                emails = response_data
            else:
                emails = response_data.get('emails', [])
            print(f"Found {len(emails)} new email(s).")
            return emails
        else:
            print(f"❌ Failed to check inbox: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error checking inbox: {e}")
        return []

def get_dynamic_interview_link(session_id):
    """Generate interview link for L1 session"""
    return f"http://48.216.217.84:5173/l1-interview/{session_id}"



# PHASE 2: Global variables for dual-timer system
last_db_check = 0
DB_CHECK_INTERVAL = 120  # 2 minutes for testing (120 seconds)
EMAIL_CHECK_INTERVAL = 30  # 30 seconds

def main():
    global last_db_check
    print("🚀 PHASE 2: Starting Database-Driven Email Follow-up System...")
    
    current_time = time.time()
    
    # --- DB CHECK MODE (Every 2 minutes) ---
    if current_time - last_db_check >= DB_CHECK_INTERVAL:
        print(f"\n🔍 DB CHECK: Fetching candidates with status 3...")
        candidates = get_candidates_for_l1_email()
        
        if candidates:
            print(f"📧 BATCH EMAIL: Processing {len(candidates)} candidates...")
            negotiating_threads = load_json_state(STATE_FILE_NEGOTIATING)
            
            for candidate in candidates:
                candidate_email = candidate["email"]
                candidate_name = candidate["name"]
                
                # Skip if already processed (status != 3)
                current_candidate = get_candidate_by_email(candidate_email)
                if not current_candidate or current_candidate['status'] != 3:
                    print(f"⏭️ Skipping {candidate_name} - status is not 3")
                    continue
                
                print(f"\n📧 Sending L1 email to: {candidate_name} ({candidate_email})")
                
                # Simple email template instead of LLM generation
                subject = f"L1 Technical Interview - {candidate_name}"
                body = f"""Dear {candidate_name},

Congratulations! You have successfully passed the prescreening assessment.

We would like to invite you for the next round - L1 Technical Interview.

Please reply to this email to confirm your availability, and we will send you the interview details.

Best regards,
Veersa Recruitment Team"""
                
                sent_message = send_email_via_api(candidate_email, subject, body)
                
                if sent_message:
                    # PHASE 2: Update database status 3 -> 4 immediately after email sent
                    if mark_email_sent(candidate_email):
                        print(f"✅ Email sent and status updated for {candidate_name}")
                    else:
                        print(f"⚠️ Email sent but DB update failed for {candidate_name}")
                else:
                    print(f"❌ Failed to send email to {candidate_name}")
            
            # No need to save negotiating_threads - using database status instead
        else:
            print("📭 No candidates with status 3 found")
        
        last_db_check = current_time
    
    # --- EMAIL CHECK MODE (Every 30 seconds) ---
    print(f"\n📬 EMAIL CHECK: Monitoring inbox for replies...")
    
    new_emails = check_inbox_via_api()
    
    if new_emails:
        print(f"📨 Processing {len(new_emails)} new emails...")
        for email_data in new_emails:
            process_incoming_email(email_data)
    else:
        print("📭 No new emails to process")
    
    print("✅ Cycle complete - continuing monitoring...")

if __name__ == '__main__':
    POLLING_INTERVAL_SECONDS = EMAIL_CHECK_INTERVAL  # 30 seconds
    print("🚀 PHASE 2: Starting Database-Driven Email Follow-up System...")
    print(f"⏰ DB Check: Every {DB_CHECK_INTERVAL} seconds")
    print(f"📧 Email Check: Every {EMAIL_CHECK_INTERVAL} seconds")
    
    try:
        while True:  # PHASE 2: Removed c==0 stopping mechanism - runs continuously
            main()
            print(f"\n--- Cycle complete. Waiting {POLLING_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop. ---")
            time.sleep(POLLING_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n🛑 Script stopped by user. Goodbye!")


