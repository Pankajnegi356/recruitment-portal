#!/usr/bin/env python3
"""
FastAPI Backend for AI Interview Platform - NO WEBSOCKET VERSION
Includes browser fingerprinting, session cleanup, and link locking
All WebSocket functionality has been removed for simplicity
"""

import os
import sys
import json
import asyncio
import tempfile
import numpy as np
import scipy.io.wavfile as wav
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import threading
import time
import hashlib
import uuid
import pytz
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from l1_interview_generator import L1InterviewGenerator


# Add current directory to path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our existing interview modules
from conversational_interview import (
    initialize_whisper, initialize_tts, conversational_speak,
    record_utterance, transcribe_audio, interview_state, voice_state,
    SAMPLE_RATE, SILENCE_DURATION
)
from utils import analyze_response_llm, classify_job_role, calculate_final_score
from question_engine import choose_next_question, load_existing_questions
from attention_analyzer import check_attention_threshold, create_attention_report
import config

# Import security modules
from interview_security import interview_security

# Import eye detection service
from eyedetection import EyeDetectionService
import base64
import cv2

# Eye tracking removed for clean backend

# ==================== SECURITY CONFIGURATION ====================
SESSION_EXPIRY_HOURS = 24  # Sessions expire after 24 hours
CLEANUP_INTERVAL_HOURS = 1  # Run cleanup every hour
INTERVIEW_TIME_LIMIT_MINUTES = 30  # 30-minute interview timer

# ==================== PERSISTENT SESSION ID SYSTEM ====================
PERSISTENT_SESSION_FILE = "persistent_sessions.json"
persistent_sessions = {}  # Maps user identifier to persistent session ID

# ==================== PYDANTIC MODELS ====================
class CandidateInfo(BaseModel):
    name: str
    email: str
    l1SessionId: Optional[str] = None

class InterviewStartRequest(BaseModel):
    candidate_info: CandidateInfo
    position: str = "Software Engineer"
    is_l1_interview: bool = False
    l1_session_id: Optional[str] = None

class InterviewEndRequest(BaseModel):
    session_id: str

class QuestionResponse(BaseModel):
    session_id: str
    answer_text: str
    question_id: int

# ==================== VIOLATION LOGGING MODELS ====================
class ViolationLogRequest(BaseModel):
    sessionId: str
    candidateEmail: str
    type: str
    timestamp: str
    duration: Optional[int] = None
    details: Optional[str] = None

# ==================== EYE DETECTION MODELS ====================
class EyeDetectionFrameRequest(BaseModel):
    session_id: str
    frame_data: str  # Base64 encoded frame
    timestamp: Optional[str] = None

# ==================== DATE-BASED LINK MODELS ====================
class GenerateInterviewLinkRequest(BaseModel):
    session_id: str
    interview_date: str  # YYYY-MM-DD format
    base_url: Optional[str] = None  # If not provided, will be extracted from request

class ValidateInterviewLinkRequest(BaseModel):
    token: str  # Encoded date token from URL



def load_persistent_sessions():
    """Load persistent session mappings from file"""
    global persistent_sessions
    try:
        if os.path.exists(PERSISTENT_SESSION_FILE):
            with open(PERSISTENT_SESSION_FILE, 'r') as f:
                persistent_sessions = json.load(f)
            print(f"📚 Loaded {len(persistent_sessions)} persistent session mappings")
        else:
            persistent_sessions = {}
            print("📚 No persistent sessions file found, starting fresh")
    except Exception as e:
        print(f"❌ Error loading persistent sessions: {e}")
        persistent_sessions = {}

def save_persistent_sessions():
    """Save persistent session mappings to file"""
    try:
        with open(PERSISTENT_SESSION_FILE, 'w') as f:
            json.dump(persistent_sessions, f, indent=2)
        print(f"💾 Saved {len(persistent_sessions)} persistent session mappings")
    except Exception as e:
        print(f"❌ Error saving persistent sessions: {e}")

def get_or_create_persistent_session_id(user_identifier: str) -> str:
    """Get existing persistent session ID or create new one for user"""
    if user_identifier in persistent_sessions:
        session_id = persistent_sessions[user_identifier]
        print(f"♻️ Using existing persistent session ID for {user_identifier[:50]}...: {session_id}")
        return session_id
    else:
        # Create new persistent session ID
        new_session_id = str(uuid.uuid4())
        persistent_sessions[user_identifier] = new_session_id
        save_persistent_sessions()
        print(f"🆕 Created new persistent session ID for {user_identifier[:50]}...: {new_session_id}")
        return new_session_id

def create_user_identifier(candidate_info: CandidateInfo, browser_fingerprint: str, l1_session_id: str = None) -> str:
    """Create a unique user identifier for persistent session mapping"""
    # For L1 interviews, use L1 session ID as primary identifier
    if l1_session_id:
        return f"L1_{l1_session_id}_{candidate_info.email}"
    else:
        # For regular interviews, use email + browser fingerprint
        return f"REG_{candidate_info.email}_{browser_fingerprint}"

# Load persistent sessions on startup
load_persistent_sessions()

# ==================== BROWSER FINGERPRINTING ====================
def generate_browser_fingerprint(request: Request) -> str:
    """Generate a very stable browser fingerprint - only use the most stable identifiers"""
    user_agent = request.headers.get("user-agent", "")
    
    # For ngrok, use the original client IP from forwarded headers
    client_ip = "unknown"
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        client_ip = forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.headers.get("x-real-ip", 
                    str(request.client.host) if request.client else "unknown")
    
    # Extract only the most stable browser info
    browser_info = "unknown"
    if "Chrome" in user_agent and "Edg" not in user_agent:  # Exclude Edge which contains Chrome
        browser_info = "Chrome"
    elif "Firefox" in user_agent:
        browser_info = "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        browser_info = "Safari"
    elif "Edg" in user_agent:  # Edge
        browser_info = "Edge"
    
    # Use ONLY browser type + client IP - ignore OS which can vary
    # This should be stable across refreshes in the same browser
    fingerprint_data = f"{browser_info}_{client_ip}"
    fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:12]  # Even shorter for more flexibility
    
    print(f"🔍 DEBUG: Stable fingerprint: {fingerprint} from {browser_info} + IP:{client_ip}")
    print(f"🔍 DEBUG: User-Agent used: {user_agent[:100]}...")
    return fingerprint


# ==================== TRANSCRIPT CLEANING ====================
def remove_massive_repetitions(cleaned_words: list) -> list:
    """Remove massive repetitions that Whisper sometimes generates at the end of transcripts"""
    if len(cleaned_words) > 10:  # Only check if we have enough words
        
        # Check for single word repeated many times at the end
        last_word = cleaned_words[-1].lower().strip('.,!?')
        if last_word:
            # Count how many times the last word appears at the end
            count = 0
            for j in range(len(cleaned_words) - 1, -1, -1):
                if cleaned_words[j].lower().strip('.,!?') == last_word:
                    count += 1
                else:
                    break
            
            # If last word repeats more than 3 times, keep only 1
            if count > 3:
                print(f"🧹 Found massive repetition: '{last_word}' repeated {count} times, keeping 1")
                # Remove the extras
                for _ in range(count - 1):
                    if cleaned_words and cleaned_words[-1].lower().strip('.,!?') == last_word:
                        cleaned_words.pop()
        
        # Check for 2-3 word phrases repeated many times at the end
        for phrase_len in range(2, 4):  # Check 2-3 word phrases
            if len(cleaned_words) >= phrase_len * 3:  # Need at least 3 repetitions to check
                
                # Get the last phrase
                last_phrase_words = cleaned_words[-phrase_len:]
                last_phrase = ' '.join(w.lower().strip('.,!?') for w in last_phrase_words)
                
                if last_phrase.strip():  # Make sure phrase is not empty
                    # Count consecutive repetitions of this phrase at the end
                    repetition_count = 0
                    pos = len(cleaned_words)
                    
                    while pos >= phrase_len:
                        # Check if the phrase at this position matches
                        check_phrase_words = cleaned_words[pos-phrase_len:pos]
                        check_phrase = ' '.join(w.lower().strip('.,!?') for w in check_phrase_words)
                        
                        if check_phrase == last_phrase:
                            repetition_count += 1
                            pos -= phrase_len
                        else:
                            break
                    
                    # If phrase repeats more than 2 times, keep only 1
                    if repetition_count > 2:
                        print(f"🧹 Found massive phrase repetition: '{' '.join(last_phrase_words)}' repeated {repetition_count} times, keeping 1")
                        # Remove the extra repetitions
                        remove_count = (repetition_count - 1) * phrase_len
                        for _ in range(remove_count):
                            if cleaned_words:
                                cleaned_words.pop()
                        break  # Only fix one pattern at a time
    
    return cleaned_words

def clean_transcript(text: str) -> str:
    """Clean transcript by removing repetitions, filler words, and artifacts"""
    if not text or not text.strip():
        return ""
    
    # Basic cleanup
    text = text.strip()
    
    # Remove common transcription artifacts and filler words
    artifacts = [
        "I'm not.", "I'm not", "I'm", "I am not", "I am not.",
        "you", "Thank you.", "Thank you", "thanks", "thanks.",
        "Bye.", "Bye", "bye", "bye.", "ok", "okay", "OK", "Okay",
        "um", "uh", "hmm", "mm", "er", "ah"
    ]
    
    # First, handle excessive word repetition (like "facilitated facilitated facilitated...")
    words = text.split()
    cleaned_words = []
    i = 0
    
    while i < len(words):
        current_word = words[i].lower().strip('.,!?;:')
        
        # Count consecutive repetitions of the same word
        repetition_count = 1
        j = i + 1
        while j < len(words) and words[j].lower().strip('.,!?;:') == current_word:
            repetition_count += 1
            j += 1
        
        # If word is repeated more than 3 times, it's likely a transcription error
        if repetition_count > 3:
            # Keep only the first occurrence
            cleaned_words.append(words[i])
            i = j
        else:
            # Keep all occurrences if reasonable repetition
            for k in range(i, min(i + repetition_count, len(words))):
                cleaned_words.append(words[k])
            i += repetition_count
    
    # Remove massive repetitions at the end
    cleaned_words = remove_massive_repetitions(cleaned_words)
    
    # Rejoin the text
    text = ' '.join(cleaned_words)
    
    # Split into sentences
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    cleaned_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Skip if sentence is just artifacts
        if sentence.lower() in [a.lower().rstrip('.') for a in artifacts]:
            continue
            
        # Remove sentences that are mostly repetitive words
        words_in_sentence = sentence.split()
        if len(words_in_sentence) > 5:
            unique_words = set(word.lower().strip('.,!?;:') for word in words_in_sentence)
            # If less than 30% unique words, it's likely gibberish
            if len(unique_words) / len(words_in_sentence) < 0.3:
                continue
        
        # Remove sentences that are too short and don't contain meaningful content
        if len(words_in_sentence) < 3 and not any(word.lower() in ['yes', 'no', 'okay', 'sure'] for word in words_in_sentence):
            continue
            
        cleaned_sentences.append(sentence)
    
    # Remove duplicate sentences
    unique_sentences = []
    for sentence in cleaned_sentences:
        # Check if this sentence is already present (case insensitive)
        is_duplicate = False
        for existing in unique_sentences:
            if sentence.lower().strip() == existing.lower().strip():
                is_duplicate = True
                break
            # Also check for substantial overlap (80% similarity)
            sentence_words = set(sentence.lower().split())
            existing_words = set(existing.lower().split())
            if sentence_words and existing_words:
                overlap = len(sentence_words & existing_words)
                similarity = overlap / max(len(sentence_words), len(existing_words))
                if similarity > 0.8:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            unique_sentences.append(sentence)
    
    # Join back with periods
    result = '. '.join(unique_sentences)
    if result and not result.endswith('.'):
        result += '.'
    
    return result

def _is_hallucination_simple(text: str) -> bool:
    """Detect hallucinations in transcription"""
    import re
    
    if not text:
        return True
    
    norm = re.sub(r"[^a-z ]", "", text.lower())
    words = norm.split()
    
    if len(words) == 0:
        return True
    
    hallucination_phrases = [
        "thank you", "thanks for watching", "please subscribe",
        "goodbye", "bye", "see you"
    ]
    
    for phrase in hallucination_phrases:
        if norm.count(phrase) >= 2 and len(words) < 15:
            return True
    
    if len(words) <= 4:
        for phrase in hallucination_phrases:
            if phrase in norm:
                return True
    
    return False

# ==================== TIMER FUNCTIONS ====================
def check_interview_timer(session_id: str, session: Dict[str, Any]) -> bool:
    """Check if interview timer has expired (30 minutes)"""
    timer_started = session.get("interview_timer_started")
    if not timer_started:
        return False
    
    if isinstance(timer_started, str):
        timer_started = datetime.fromisoformat(timer_started)
    
    elapsed_minutes = (datetime.now() - timer_started).total_seconds() / 60
    time_limit = session.get("time_limit_minutes", INTERVIEW_TIME_LIMIT_MINUTES)
    
    if elapsed_minutes >= time_limit:
        print(f"⏰ TIMER EXPIRED: Interview {session_id} has exceeded {time_limit} minutes")
        return True
    
    return False

def get_remaining_time_minutes(session: Dict[str, Any]) -> float:
    """Get remaining time in minutes for the interview"""
    timer_started = session.get("interview_timer_started")
    if not timer_started:
        return INTERVIEW_TIME_LIMIT_MINUTES
    
    if isinstance(timer_started, str):
        timer_started = datetime.fromisoformat(timer_started)
    
    elapsed_minutes = (datetime.now() - timer_started).total_seconds() / 60
    time_limit = session.get("time_limit_minutes", INTERVIEW_TIME_LIMIT_MINUTES)
    remaining = max(0, time_limit - elapsed_minutes)
    
    return round(remaining, 2)

def auto_end_expired_interviews():
    """Auto-end interviews that have exceeded the 30-minute limit"""
    expired_sessions = []
    
    for session_id, session in active_sessions.items():
        if session.get("status") == "active" and check_interview_timer(session_id, session):
            expired_sessions.append((session_id, session))
    
    for session_id, session in expired_sessions:
        print(f"🕐 AUTO-ENDING expired interview: {session_id}")
        
        # Mark as completed
        session["status"] = "completed"
        session["end_time"] = datetime.now()
        session["end_reason"] = "time_expired"
        
        # Calculate final results
        from utils import calculate_final_score
        final_results = calculate_final_score(session.get("results", []))
        session["final_results"] = final_results
        
        # Save results
        os.makedirs("results", exist_ok=True)
        results_filename = f"results/interview_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_TIME_EXPIRED.json"
        
        results_data = {
            "session_id": session_id,
            "candidate_info": session.get("candidate_info", {}),
            "position": session.get("position", "Unknown"),
            "start_time": session["start_time"].isoformat() if session.get("start_time") else "Unknown",
            "end_time": session["end_time"].isoformat(),
            "end_reason": "TIME_EXPIRED_30_MINUTES",
            "total_questions": session.get("total_questions", 0),
            "questions_answered": len(session.get("results", [])),
            "detailed_results": session.get("results", []),
            "final_results": final_results,
            "status": "completed",
            "time_limit_minutes": session.get("time_limit_minutes", INTERVIEW_TIME_LIMIT_MINUTES)
        }
        
        try:
            with open(results_filename, 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
            print(f"✅ Saved time-expired interview results: {results_filename}")
        except Exception as e:
            print(f"❌ Failed to save time-expired results: {e}")
        
        # Clean up L1 files if applicable
        if session.get("is_l1_interview") and session.get("l1_session_id"):
            l1_session_id = session['l1_session_id']
            l1_file_path = f"../data/l1_interview_{l1_session_id}.json"
            if os.path.exists(l1_file_path):
                try:
                    os.remove(l1_file_path)
                    print(f"🗑️ Deleted L1 file for time-expired interview: {l1_file_path}")
                except Exception as e:
                    print(f"❌ Failed to delete L1 file: {e}")
            
            # Remove link lock
            if l1_session_id in l1_link_locks:
                del l1_link_locks[l1_session_id]
                print(f"🔓 Released link lock for time-expired L1 session: {l1_session_id}")
            
            # Delete link security file
            security_file = f"link_security/l1_lock_{l1_session_id}.json"
            if os.path.exists(security_file):
                try:
                    os.remove(security_file)
                    print(f"🗑️ Deleted link security file for time-expired interview: {security_file}")
                except Exception as e:
                    print(f"❌ Failed to delete security file: {e}")
        
        print(f"⏰ Interview {session_id} auto-ended due to 30-minute time limit")
    
    return len(expired_sessions)

# ==================== GLOBAL STATE ====================
active_sessions: Dict[str, Dict[str, Any]] = {}
l1_link_locks: Dict[str, str] = {}  # Maps L1 session ID to browser fingerprint
eye_tracking_sessions: Dict[str, EyeDetectionService] = {}  # Maps session ID to EyeDetectionService
cleanup_thread = None

# ==================== SESSION CLEANUP ====================
def cleanup_expired_sessions():
    """Clean up expired sessions and their L1 files, also check for timer expiry"""
    while True:
        try:
            # Check for timer-expired interviews every 30 seconds
            time.sleep(30)  # Check more frequently for timer expiry
            current_time = datetime.now()
            
            # First, auto-end interviews that have exceeded the 30-minute limit
            expired_count = auto_end_expired_interviews()
            if expired_count > 0:
                print(f"⏰ Auto-ended {expired_count} interviews due to 30-minute time limit")
            
            # Then check for 24-hour session expiry (less frequent)
            # Only run full cleanup every hour
            if current_time.minute % 60 < 1:  # Run approximately every hour
                expired_sessions = []
                
                # Find expired sessions (24-hour expiry)
                for session_id, session_data in active_sessions.items():
                    created_at = session_data.get("created_at")
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)
                    elif not isinstance(created_at, datetime):
                        continue
                    
                    if (current_time - created_at).total_seconds() > SESSION_EXPIRY_HOURS * 3600:
                        expired_sessions.append(session_id)
                
                # Clean up expired sessions
                for session_id in expired_sessions:
                    session = active_sessions.pop(session_id, None)
                    if session:
                        # Delete L1 interview file if it's an L1 interview
                        if session.get("is_l1_interview") and session.get("l1_session_id"):
                            l1_session_id = session['l1_session_id']
                            l1_file_path = f"../data/l1_interview_{l1_session_id}.json"
                            if os.path.exists(l1_file_path):
                                try:
                                    os.remove(l1_file_path)
                                    print(f"🗑️ Deleted expired L1 file: {l1_file_path}")
                                except Exception as e:
                                    print(f"❌ Failed to delete L1 file: {e}")
                            # Also remove the link lock
                            if l1_session_id in l1_link_locks:
                                del l1_link_locks[l1_session_id]
                                print(f"🔓 Released link lock for L1 session: {l1_session_id}")
                        
                        print(f"🧹 Cleaned up expired session: {session_id}")
                
                if expired_sessions:
                    print(f"✅ Cleaned {len(expired_sessions)} expired sessions (24-hour expiry)")
                
        except Exception as e:
            print(f"❌ Error in cleanup thread: {e}")

# ==================== FASTAPI APP ====================
app = FastAPI(
    title="AI Interview Platform API - No WebSocket",
    description="Backend API for conversational AI interviews without WebSocket support",
    version="1.2.0"
)

# Add custom middleware to handle ngrok headers
@app.middleware("http")
async def add_ngrok_headers(request: Request, call_next):
    """Add headers to bypass ngrok browser warning"""
    response = await call_next(request)
    
    # Add headers to help with ngrok compatibility
    response.headers["ngrok-skip-browser-warning"] = "true"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    
    return response

# Import env_config for dynamic CORS origins
from env_config import get_ngrok_cors_origins

# Configure CORS with dynamic ngrok support
# Use env_config to get dynamic origins instead of hardcoded ones
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_ngrok_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all response headers
)

# ==================== STARTUP/SHUTDOWN ====================
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Starting AI Interview Platform API (No WebSocket Version)...")
    
    # Test question loading
    test_questions = load_existing_questions(silent=True)
    if test_questions:
        print(f"✅ Legacy questions available ({len(test_questions)} questions)")
    else:
        print("ℹ️ Using session-based question loading for L1 interviews")
    
    # Initialize Whisper STT model
    if not initialize_whisper():
        print("❌ Failed to initialize Whisper model")
        sys.exit(1)
    
    # Test TTS initialization
    if not initialize_tts():
        print("❌ Failed to initialize TTS engine")
        sys.exit(1)
    
    # Start cleanup thread
    global cleanup_thread
    cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
    cleanup_thread.start()
    print("🧹 Session cleanup thread started (24-hour expiry)")
    
    print("✅ All services initialized successfully (WebSocket disabled)")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🔄 Shutting down AI Interview Platform API...")
    active_sessions.clear()

# ==================== API ROUTES ====================

# Handle preflight CORS requests
@app.options("/api/{path:path}")
async def options_handler(path: str):
    """Handle preflight CORS requests"""
    return JSONResponse(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(active_sessions),
        "websocket_support": False
    }

@app.get("/api/l1/interview/{session_id}")
async def get_l1_interview_session(session_id: str, request: Request):
    """Get L1 interview session data - WITH LINK LOCKING AND DATE TOKEN VALIDATION"""
    try:
        print(f"🔍 DEBUG: L1 interview request for session: {session_id}")
        print(f"🔍 DEBUG: User-Agent: {request.headers.get('user-agent', 'Unknown')}")
        print(f"🔍 DEBUG: Origin: {request.headers.get('origin', 'None')}")
        print(f"🔍 DEBUG: Referer: {request.headers.get('referer', 'None')}")

        # ----------------------------
        # 1. Check for date token in query parameters
        # ----------------------------
        token = request.query_params.get("token", "")
        if token:
            print(f"🔒 Date token found in URL: {token[:20]}...")
            
            # Validate date token first
            can_access, token_message = interview_security.validate_interview_access(token)
            if not can_access:
                print(f"❌ Date token validation failed: {token_message}")
                return {
                    "status": "token_invalid",
                    "message": token_message,
                    "current_date": datetime.now().date().isoformat()
                }
            else:
                print(f"✅ Date token validation passed: {token_message}")
        else:
            print("ℹ️ No date token found, using legacy time validation")

        # ----------------------------
        # 2. Load session metadata for legacy validation (fallback)
        # ----------------------------
        generator = L1InterviewGenerator()
        metadata = generator.load_session_metadata(session_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Session metadata not found")

        # Convert to datetime and handle timezone properly (needed for response data)
        tz = pytz.timezone("Asia/Kolkata")  # adjust if needed
        
        # Parse dates from metadata
        created_at = datetime.fromisoformat(metadata["created_at"])
        expires_at = datetime.fromisoformat(metadata["expires_at"])
        
        # Make sure all datetimes are timezone-aware for comparison
        if created_at.tzinfo is None:
            created_at = tz.localize(created_at)
        if expires_at.tzinfo is None:
            expires_at = tz.localize(expires_at)
        
        now = datetime.now(tz)
        
        # Legacy time validation (only if no token provided)
        if not token:
            # Validate time window
            if now < created_at:
                return {
                    "status": "not_yet_active",
                    "message": f"Your interview link will be active on {created_at.strftime('%Y-%m-%d %H:%M')}"
                }
            elif now >= expires_at:
                return {
                    "status": "expired",
                    "message": "This interview link has expired."
                }
        
        
        # Generate browser fingerprint
        browser_fingerprint = generate_browser_fingerprint(request)
        
        # Check if this L1 session is already locked to a browser
        if session_id in l1_link_locks:
            locked_fingerprint = l1_link_locks[session_id]
            if locked_fingerprint != browser_fingerprint:
                print(f"🔒 L1 session {session_id} is locked to another browser")
                raise HTTPException(
                    status_code=403, 
                    detail="This interview link is already being accessed in another browser"
                )
            else:
                print(f"✅ L1 session {session_id} accessed by same browser")
        else:
            # First access - lock it to this browser
            l1_link_locks[session_id] = browser_fingerprint
            print(f"🔒 L1 session {session_id} locked to browser: {browser_fingerprint[:8]}...")
            
            # Save to link_security folder
            os.makedirs("link_security", exist_ok=True)
            security_data = {
                "l1_session_id": session_id,
                "browser_fingerprint": browser_fingerprint,
                "locked_at": datetime.now().isoformat(),
                "candidate_email": "",  # Will be filled when interview starts
                "status": "locked"
            }
            
            security_file = f"link_security/l1_lock_{session_id}.json"
            with open(security_file, 'w') as f:
                json.dump(security_data, f, indent=2)
            print(f"💾 Link lock saved to: {security_file}")
        
        # Use absolute path instead of relative path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        session_file = os.path.join(os.path.dirname(current_dir), "data", f"l1_interview_{session_id}.json")
        print(f"🔍 Looking for L1 session file at: {session_file}")
        
        if not os.path.exists(session_file):
            print(f"❌ File not found at {session_file}")
            # Remove lock if file doesn't exist
            if session_id in l1_link_locks:
                del l1_link_locks[session_id]
            raise HTTPException(status_code=404, detail=f"L1 interview session not found at {session_file}")
        
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        print(f"📋 Retrieved L1 session data for: {session_id}")
        return {
            "session_id": session_id,
            "candidate_name": session_data.get("candidate_name", "Unknown"),
            "candidate_email": session_data.get("candidate_email", ""),
            "job_role": session_data.get("job_role", "Data Engineer"),
            "prescreening_score": session_data.get("prescreening_score", ""),
            "interview_type": "L1",  # Add interview_type field for frontend validation
            "difficulty_distribution": session_data.get("difficulty_distribution", {"easy": 2, "medium": 2, "hard": 1}),
            "total_questions": config.NUM_QUESTIONS,  # Always return 5
            "status": session_data.get("status", "pending"),
            "created_at": session_data.get("created_at", ""),
            "locked": True,  # Indicate that the link is now locked
            "browser_locked": browser_fingerprint[:8], # Show which browser it's locked to
            "validity": {
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "now": now.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="L1 interview session not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid session data format")
    except Exception as e:
        print(f"❌ Error retrieving L1 session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve L1 session: {str(e)}")

@app.post("/api/interview/start")
async def start_interview(request: InterviewStartRequest, http_request: Request):
    """Start a new interview session with browser fingerprinting"""
    try:
        # Generate browser fingerprint for link locking
        browser_fingerprint = generate_browser_fingerprint(http_request)
        
        # Check if this is an L1 interview
        l1_session_id = request.l1_session_id or getattr(request.candidate_info, 'l1SessionId', None)
        is_l1_interview = bool(l1_session_id)
        
        # Create user identifier for persistent session ID
        user_identifier = create_user_identifier(request.candidate_info, browser_fingerprint, l1_session_id)
        
        # Get or create persistent session ID
        session_id = get_or_create_persistent_session_id(user_identifier)
        created_at = datetime.now()
        
        # Check for legitimate session resumption (same link + same browser)
        existing_session = None
        existing_session_id = None
        
        # DEBUG: Log current session details
        print(f"🔍 DEBUG: Starting interview for candidate: {request.candidate_info.email}")
        print(f"🔍 DEBUG: New session ID: {session_id}")
        print(f"🔍 DEBUG: L1 session ID: {l1_session_id}")
        print(f"🔍 DEBUG: Is L1 interview: {is_l1_interview}")
        print(f"🔍 DEBUG: Active sessions count: {len(active_sessions)}")
        
        if is_l1_interview:
            # For L1 interviews: Resume only if SAME L1 link + SAME browser + has progress
            for sid, session in active_sessions.items():
                if (session.get("l1_session_id") == l1_session_id and 
                    session.get("status") == "active" and
                    session.get("browser_fingerprint") == browser_fingerprint and
                    session.get("current_question_num", 0) > 1):  # Has made progress
                    
                    existing_session = session
                    existing_session_id = sid
                    print(f"🔄 RESUMING L1 session: Same link ({l1_session_id}) + Same browser + Progress exists")
                    print(f"🔄 Resuming from question {session['current_question_num']}")
                    break
        else:
            # For regular interviews: Resume only if SAME email + SAME browser + has progress  
            candidate_email = request.candidate_info.email
            for sid, session in active_sessions.items():
                if (session.get("candidate_info", {}).get("email") == candidate_email and
                    session.get("status") == "active" and
                    session.get("browser_fingerprint") == browser_fingerprint and
                    session.get("current_question_num", 0) > 1 and  # Has made progress
                    not session.get("is_l1_interview", False)):
                    
                    existing_session = session
                    existing_session_id = sid
                    print(f"🔄 RESUMING regular session: Same email + Same browser + Progress exists")
                    print(f"🔄 Resuming from question {session['current_question_num']}")
                    break
        
        # If found legitimate resumption, return existing session
        if existing_session and existing_session_id:
            current_question = existing_session.get("current_question", {})
            
            # Calculate remaining time from existing session
            remaining_time = get_remaining_time_minutes(existing_session)
            
            print(f"🔄 RESUME: Session has {remaining_time:.2f} minutes remaining")
            
            return {
                "session_id": existing_session_id,  # Use existing session ID
                "status": "resumed",
                "message": "Resuming your previous interview session",
                "current_question": current_question.get("question"),
                "current_question_num": existing_session.get("current_question_num", 1),
                "total_questions": existing_session.get("total_questions", 5),
                "introduction": "Welcome back! Let's continue where we left off.",
                "remaining_time_minutes": remaining_time,
                "interview_timer_started": existing_session.get("interview_timer_started", datetime.now()).isoformat() if isinstance(existing_session.get("interview_timer_started"), datetime) else existing_session.get("interview_timer_started")
            }
        
        # Otherwise, start fresh session
        print(f"🆕 Starting completely fresh interview session: {session_id}")
        
        if is_l1_interview:
            # First check if the L1 link is locked to a different browser
            if l1_session_id in l1_link_locks:
                if l1_link_locks[l1_session_id] != browser_fingerprint:
                    raise HTTPException(
                        status_code=403,
                        detail="This interview link is already being accessed in another browser"
                    )
        
        # Load questions based on interview type
        l1_data = None  # Initialize l1_data
        if is_l1_interview:
            # Load L1 questions from session file using absolute path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            l1_file_path = os.path.join(os.path.dirname(current_dir), "data", f"l1_interview_{l1_session_id}.json")
            
            if not os.path.exists(l1_file_path):
                raise HTTPException(status_code=404, detail="L1 interview session not found")
            
            with open(l1_file_path, 'r') as f:
                l1_data = json.load(f)
            
            question_pool = l1_data.get("questions", [])
            position = l1_data.get("job_role", request.position)
            total_questions = config.NUM_QUESTIONS  # Always use config NUM_QUESTIONS (5)
            
            print(f"📚 Loaded {len(question_pool)} questions for L1 interview {l1_session_id}")
            
            # Debug: Check for corrupted questions at load time
            corrupted_in_pool = [q for q in question_pool if "**" in q.get("question", "")]
            if corrupted_in_pool:
                print(f"⚠️ CRITICAL: Found {len(corrupted_in_pool)} corrupted questions at load time!")
                for i, q in enumerate(corrupted_in_pool[:3]):
                    print(f"   Corrupted Q{i+1}: {q.get('question', 'NO QUESTION')}")
            else:
                print(f"✅ All {len(question_pool)} questions in L1 pool are valid (no '**' corruption)")
        else:
            # Load generic questions
            question_pool = load_existing_questions()
            if not question_pool:
                raise HTTPException(status_code=500, detail="Failed to load question pool")
            position = request.position
            total_questions = config.NUM_QUESTIONS
            
            print(f"📚 Loaded {len(question_pool)} generic questions")
            
        session_data = {
            "session_id": session_id,
            "created_at": created_at,
            "browser_fingerprint": browser_fingerprint,  # For link locking
            "candidate_info": request.candidate_info.dict(),
            "position": position,
            "current_question_num": 0,
            "total_questions": total_questions,
            "question_pool": question_pool,
            "current_difficulty": "easy",
            "is_l1_interview": is_l1_interview,
            "l1_session_id": l1_session_id,
            "results": [],
            "start_time": datetime.now(),
            "interview_timer_started": datetime.now(),  # 30-minute timer starts when interview begins
            "time_limit_minutes": INTERVIEW_TIME_LIMIT_MINUTES,
            "status": "active"
        }
        
        active_sessions[session_id] = session_data
        
        # Get first question
        first_question = choose_next_question(question_pool, difficulty="easy")
        
        if first_question:
            active_sessions[session_id]["current_question"] = first_question
            active_sessions[session_id]["current_question_num"] = 1
        
        introduction = (
            f"Hey there! My name is Alex, and I'll be conducting your technical interview today. "
            f"I'm excited to learn about your experience and skills. "
            f"Before we dive in, let me explain how this will work. "
            f"I'll ask you a series of technical questions and evaluate your responses. "
            f"Please note that while there's a mute button available, try to avoid using it during the interview. "
            f"If you absolutely need to mute yourself, please do so only when you want to end an answer, "
            f"and make sure to unmute when the next question appears - not before. "
            f"Feel free to take your time with each response - I'm here to understand "
            f"your knowledge and thought process. "
            f"Let's start with our first question."
        )
        
        print(f"✅ Interview started: {session_id} (Browser locked: {browser_fingerprint[:8]}...)")
        
        return {
            "session_id": session_id,
            "status": "started",
            "message": f"Interview started for {request.candidate_info.name}",
            "first_question": first_question.get("question") if first_question else None,
            "introduction": introduction,
            "expires_in_hours": SESSION_EXPIRY_HOURS,
            "interview_timer_started": session_data["interview_timer_started"].isoformat(),
            "time_limit_minutes": INTERVIEW_TIME_LIMIT_MINUTES,
            "remaining_time_minutes": INTERVIEW_TIME_LIMIT_MINUTES  # Full time for new sessions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error starting interview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")

@app.post("/api/interview/transcribe")
async def transcribe_audio_endpoint(
    session_id: str,
    file: UploadFile = File(...),
    request: Request = None
):
    """Transcribe uploaded audio file with browser verification"""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = active_sessions[session_id]
        
        # Verify browser fingerprint for link locking
        if request:
            current_fingerprint = generate_browser_fingerprint(request)
            if session.get("browser_fingerprint") != current_fingerprint:
                raise HTTPException(
                    status_code=403,
                    detail="This session is locked to a different browser"
                )
        
        # Check if interview timer has expired
        if check_interview_timer(session_id, session):
            # Auto-end the interview due to time expiry
            session["status"] = "completed"
            session["end_time"] = datetime.now()
            session["end_reason"] = "time_expired"
            raise HTTPException(
                status_code=410,
                detail="Interview session has expired (30-minute time limit reached)"
            )
        
        if session.get("status") == "completed":
            raise HTTPException(status_code=400, detail="Interview session has been completed")
        
        # Read and process audio
        audio_data = await file.read()
        
        # Save to temporary file
        file_extension = ".webm"
        if file.content_type:
            if "wav" in file.content_type:
                file_extension = ".wav"
            elif "mp4" in file.content_type:
                file_extension = ".mp4"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(audio_data)
            tmp_path = tmp_file.name

        try:
            # Load audio with librosa
            import librosa
            audio, sr = librosa.load(tmp_path, sr=16000, mono=True)
            
            # Transcribe with Whisper using the imported function
            transcript = transcribe_audio(audio)
            
            # Clean transcript
            if transcript:
                transcript = clean_transcript(transcript)
            
            # Validate
            if not transcript or len(transcript.strip()) < 3:
                return {
                    "session_id": session_id,
                    "transcript": "",
                    "status": "silence_detected"
                }
            
            if _is_hallucination_simple(transcript):
                return {
                    "session_id": session_id,
                    "transcript": "",
                    "status": "hallucination_detected"
                }
            
            return {
                "session_id": session_id,
                "transcript": transcript,
                "status": "success"
            }

        finally:
            # Clean up
            try:
                os.unlink(tmp_path)
            except:
                pass

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/api/interview/answer")
async def process_answer(response: QuestionResponse, background_tasks: BackgroundTasks, request: Request = None):
    """Process candidate's answer with browser verification"""
    try:
        if response.session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = active_sessions[response.session_id]
        
        # Verify browser fingerprint
        if request:
            current_fingerprint = generate_browser_fingerprint(request)
            if session.get("browser_fingerprint") != current_fingerprint:
                raise HTTPException(
                    status_code=403,
                    detail="This session is locked to a different browser"
                )
        
        # Check if interview timer has expired
        if check_interview_timer(response.session_id, session):
            # Auto-end the interview due to time expiry
            session["status"] = "completed"
            session["end_time"] = datetime.now()
            session["end_reason"] = "time_expired"
            raise HTTPException(
                status_code=410,
                detail="Interview session has expired (30-minute time limit reached)"
            )
        
        if session.get("status") == "completed":
            raise HTTPException(status_code=400, detail="Interview session has been completed")
        
        current_question = session.get("current_question")
        if not current_question:
            raise HTTPException(status_code=400, detail="No active question found")
        
        # Evaluate the answer
        evaluation = analyze_response_llm(
            answer=response.answer_text,
            question=current_question["question"],
            difficulty=session["current_difficulty"]
        )
        
        # Store result with simple sequential numbering
        result = {
            "question_id": session["current_question_num"],  # Simple 1, 2, 3, 4, 5
            "question": current_question["question"],
            "answer": response.answer_text,
            "difficulty": session["current_difficulty"],
            "score": evaluation["score"],
            "feedback": evaluation["feedback"],
            "passing_threshold": current_question.get("passing_threshold", 50),
            "timestamp": datetime.now().isoformat()
        }
        
        session["results"].append(result)
        
        # Mark question as used
        for question in session["question_pool"]:
            if question.get("question") == current_question["question"]:
                question["ans"] = response.answer_text
                question["score"] = evaluation["score"]
                question["feedback"] = evaluation["feedback"]
                break
        
        # Update difficulty
        from utils import update_difficulty
        old_difficulty = session["current_difficulty"]
        new_difficulty = update_difficulty(
            old_difficulty,
            evaluation["score"],
            current_question.get("passing_threshold", 50)
        )
        session["current_difficulty"] = new_difficulty
        
        # Check if interview should continue
        questions_answered = len(session["results"])
        if questions_answered >= session["total_questions"]:
            # Interview complete
            session["status"] = "completed"
            session["end_time"] = datetime.now()
            final_results = calculate_final_score(session["results"])
            session["final_results"] = final_results
            
            # Save results
            os.makedirs("results", exist_ok=True)
            results_filename = f"results/interview_{response.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(results_filename, "w", encoding="utf-8") as f:
                json.dump({
                    "session_id": response.session_id,
                    "candidate_info": session["candidate_info"],
                    "position": session["position"],
                    "start_time": session["start_time"].isoformat(),
                    "end_time": session["end_time"].isoformat(),
                    "total_questions": session["total_questions"],
                    "questions_answered": len(session["results"]),
                    "results": session["results"],
                    "final_results": final_results
                }, f, indent=2, ensure_ascii=False)
            
            # Save eye tracking logs if session had eye tracking
            if response.session_id in eye_tracking_sessions:
                eye_service = eye_tracking_sessions[response.session_id]
                try:
                    eye_log_file = eye_service.save_session_log("eye_log")
                    if eye_log_file:
                        print(f"👁️ Saved eye tracking log: {eye_log_file}")
                except Exception as e:
                    print(f"❌ Failed to save eye tracking log: {e}")
                
                # Clean up eye tracking session
                del eye_tracking_sessions[response.session_id]
                print(f"👁️ Cleaned up eye tracking session: {response.session_id}")
            
            # Delete L1 interview file if it's an L1 interview
            if session.get("is_l1_interview") and session.get("l1_session_id"):
                l1_session_id = session['l1_session_id']
                l1_file_path = f"../data/l1_interview_{l1_session_id}.json"
                if os.path.exists(l1_file_path):
                    try:
                        os.remove(l1_file_path)
                        print(f"🗑️ Deleted completed L1 file: {l1_file_path}")
                    except Exception as e:
                        print(f"❌ Failed to delete L1 file: {e}")
                # Also remove the link lock and security file
                if l1_session_id in l1_link_locks:
                    del l1_link_locks[l1_session_id]
                    print(f"🔓 Released link lock for completed L1 session: {l1_session_id}")
                
                # Delete link security file
                security_file = f"link_security/l1_lock_{l1_session_id}.json"
                if os.path.exists(security_file):
                    try:
                        os.remove(security_file)
                        print(f"🗑️ Deleted link security file: {security_file}")
                    except Exception as e:
                        print(f"❌ Failed to delete security file: {e}")
            
            average_score = sum(r["score"] for r in session["results"]) / len(session["results"])
            
            return {
                "session_id": response.session_id,
                "status": "interview_complete",
                "evaluation": evaluation,
                "feedback": f"Interview completed! Your final score: {average_score:.1f}/100",
                "score": average_score,
                "final_score": average_score,
                "next_question": None,
                "alex_response": f"Thank you for completing the interview! Your final score is {average_score:.1f} out of 100.",
                "question_number": session["current_question_num"],
                "total_questions": session["total_questions"],
                "results_saved": results_filename
            }
        
        # Get next question
        next_question = choose_next_question(
            session["question_pool"],
            difficulty=new_difficulty
        )
        
        # Add safety check for corrupted question data
        if next_question and (not next_question.get("question") or 
                            "**" in next_question.get("question", "") or 
                            len(next_question.get("question", "").strip()) < 10):
            print(f"⚠️ WARNING: Corrupted question detected: {next_question}")
            next_question = None
        
        # Fallback to any unused question if needed
        if not next_question and questions_answered < session["total_questions"]:
            print(f"🔍 Looking for fallback question from {len(session['question_pool'])} questions")
            for q in session["question_pool"]:
                if (q.get("ans", "") == "" and 
                    q.get("question") and 
                    "**" not in q.get("question", "") and 
                    len(q.get("question", "").strip()) >= 10):
                    print(f"✅ Found valid fallback question: {q.get('question')[:50]}...")
                    next_question = q
                    break
            
            if not next_question:
                print(f"❌ No valid questions found in pool of {len(session['question_pool'])} questions")
                for i, q in enumerate(session["question_pool"][:5]):
                    print(f"   Q{i+1}: {q.get('question', 'NO QUESTION')} (ans: '{q.get('ans', '')}')")
        
        if next_question:
            session["current_question"] = next_question
            session["current_question_num"] += 1
            
            return {
                "session_id": response.session_id,
                "status": "question_processed",
                "evaluation": evaluation,
                "feedback": evaluation['feedback'][:200] + "..." if len(evaluation['feedback']) > 200 else evaluation['feedback'],
                "score": evaluation['score'],
                "next_question": next_question,
                "alex_response": f"Your next question is: {next_question['question']}",
                "question_number": session["current_question_num"],
                "total_questions": session["total_questions"]
            }
        else:
            # No more questions available
            session["status"] = "completed"
            
            # Delete L1 file if completed
            if session.get("is_l1_interview") and session.get("l1_session_id"):
                l1_session_id = session['l1_session_id']
                l1_file_path = f"../data/l1_interview_{l1_session_id}.json"
                if os.path.exists(l1_file_path):
                    try:
                        os.remove(l1_file_path)
                        print(f"🗑️ Deleted completed L1 file: {l1_file_path}")
                    except Exception as e:
                        print(f"❌ Failed to delete L1 file: {e}")
                
                # Also remove the link lock and security file
                if l1_session_id in l1_link_locks:
                    del l1_link_locks[l1_session_id]
                    print(f"🔓 Released link lock for completed L1 session: {l1_session_id}")
                
                # Delete link security file
                security_file = f"link_security/l1_lock_{l1_session_id}.json"
                if os.path.exists(security_file):
                    try:
                        os.remove(security_file)
                        print(f"🗑️ Deleted link security file: {security_file}")
                    except Exception as e:
                        print(f"❌ Failed to delete security file: {e}")
            
            return {
                "session_id": response.session_id,
                "status": "interview_complete",
                "evaluation": evaluation,
                "feedback": evaluation['feedback'][:200] + "..." if len(evaluation['feedback']) > 200 else evaluation['feedback'],
                "score": evaluation['score'],
                "next_question": None,
                "alex_response": "We've covered all the questions. Thank you for your time!",
                "question_number": session["current_question_num"],
                "total_questions": session["total_questions"]
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error processing answer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {str(e)}")

@app.post("/api/interview/end")
async def end_interview(request: InterviewEndRequest, http_request: Request = None):
    """End an interview session with browser verification"""
    try:
        if request.session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = active_sessions[request.session_id]
        
        # Verify browser fingerprint
        if http_request:
            current_fingerprint = generate_browser_fingerprint(http_request)
            if session.get("browser_fingerprint") != current_fingerprint:
                raise HTTPException(
                    status_code=403,
                    detail="This session is locked to a different browser"
                )
        
        session["status"] = "completed"
        session["end_time"] = datetime.now()
        
        # Calculate final scores
        final_results = calculate_final_score(session["results"])
        original_score = final_results.get("final_score", 0)
        
        # 🎯 AUTOMATIC FRAME PROCESSING
        print(f"🎬 Processing saved eye tracking frames for session: {request.session_id}")
        try:
            # Check if we have saved frames to process
            session_dir = os.path.join("eye_logs", f"session_{request.session_id}")
            if os.path.exists(session_dir):
                import glob
                frame_files = glob.glob(os.path.join(session_dir, "frame_*.jpg"))
                
                if frame_files:
                    print(f"📸 Found {len(frame_files)} frames to process")
                    
                    # Check if analysis already exists to avoid reprocessing
                    existing_analysis = glob.glob(f"eye_analysis/eye_analysis_{request.session_id}_*.json")
                    
                    if not existing_analysis:
                        print(f"🔄 Processing frames automatically...")
                        
                        # Import and use the FrameProcessor
                        from process_saved_frames import FrameProcessor
                        
                        # Create processor with optimal settings
                        processor = FrameProcessor(
                            simple_mode=False,  # Use advanced mode for better accuracy
                            smoothing_window=5,  # Good balance
                            confidence_threshold=3  # Moderate confidence requirement
                        )
                        
                        # Process the session frames
                        analysis_file = processor.process_session(session_dir, "eye_analysis")
                        
                        if analysis_file:
                            print(f"✅ Frame processing completed: {analysis_file}")
                        else:
                            print(f"⚠️ Frame processing failed for session {request.session_id}")
                    else:
                        print(f"📄 Using existing analysis: {existing_analysis[0]}")
                else:
                    print(f"📸 No frames found for session {request.session_id}")
            else:
                print(f"📁 No eye tracking directory found for session {request.session_id}")
                
        except Exception as frame_processing_error:
            print(f"❌ Error in automatic frame processing: {frame_processing_error}")
            # Continue with interview end even if frame processing fails
        
        # 🎯 ATTENTION THRESHOLD CHECKING
        print(f"👁️ Checking attention threshold for session: {request.session_id}")
        try:
            # Check attention and determine final status
            attention_status_code, attention_status_text, attention_analysis = check_attention_threshold(
                session_id=request.session_id, 
                original_score=original_score, 
                threshold=20.0  # 20% attention threshold
            )
            
            # Create comprehensive attention report
            attention_report = create_attention_report(
                session_id=request.session_id,
                original_score=original_score,
                threshold=20.0
            )
            
            print(f"👁️ Attention Analysis Results:")
            print(f"   Original Score: {original_score}")
            print(f"   Attention Status: {attention_status_text} (code: {attention_status_code})")
            print(f"   Attention %: {attention_analysis.get('attention_percentage', 'N/A')}%")
            
            # Update final results based on attention analysis
            if attention_status_code == 0:  # Failed due to attention threshold
                print(f"❌ ATTENTION THRESHOLD VIOLATION - Setting status to FAIL")
                # Override the final results to show failure
                final_results["final_score"] = original_score  # Keep original score for reference
                final_results["attention_override"] = True
                final_results["attention_status"] = attention_status_text
                final_results["overall_status"] = "FAILED - Low Attention"
                final_results["pass_rate"] = 0  # Override pass rate
            else:
                print(f"✅ ATTENTION THRESHOLD MET - Using original results")
                final_results["attention_override"] = False
                final_results["attention_status"] = attention_status_text
            
            # Add attention analysis to final results
            final_results["attention_analysis"] = attention_analysis
            final_results["attention_report"] = attention_report
            
        except Exception as attention_error:
            print(f"❌ Error in attention analysis: {attention_error}")
            # If attention analysis fails, continue with original results
            final_results["attention_override"] = False
            final_results["attention_status"] = "ANALYSIS_FAILED"
            final_results["attention_error"] = str(attention_error)
        
        session["final_results"] = final_results
        
        # Save results
        results_data = {
            "session_id": request.session_id,
            "candidate_info": session["candidate_info"],
            "position": session.get("position"),
            "start_time": session["start_time"].isoformat(),
            "end_time": session["end_time"].isoformat(),
            "total_questions": session["total_questions"],
            "questions_answered": len(session["results"]),
            "detailed_results": session["results"],
            "final_results": final_results,
            "status": "completed"
        }
        
        os.makedirs("results", exist_ok=True)
        results_filename = f"results/interview_{request.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(results_filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        # 🎯 DATABASE INTEGRATION: Save interview results to MySQL
        try:
            from db_results_saver import save_interview_to_database
            success = save_interview_to_database(results_data)
            if success:
                print(f"✅ Interview results saved to database for session {request.session_id}")
            else:
                print(f"⚠️ Failed to save interview results to database for session {request.session_id}")
        except Exception as db_error:
            print(f"❌ Database integration error for session {request.session_id}: {db_error}")
        
        # Delete L1 interview file if it's an L1 interview
        if session.get("is_l1_interview") and session.get("l1_session_id"):
            l1_session_id = session['l1_session_id']
            l1_file_path = f"../data/l1_interview_{l1_session_id}.json"
            if os.path.exists(l1_file_path):
                try:
                    os.remove(l1_file_path)
                    print(f"🗑️ Deleted L1 file after interview end: {l1_file_path}")
                except Exception as e:
                    print(f"❌ Failed to delete L1 file: {e}")
            
            # Also remove the link lock and security file
            if l1_session_id in l1_link_locks:
                del l1_link_locks[l1_session_id]
                print(f"🔓 Released link lock for ended L1 session: {l1_session_id}")
            
            # Delete link security file
            security_file = f"link_security/l1_lock_{l1_session_id}.json"
            if os.path.exists(security_file):
                try:
                    os.remove(security_file)
                    print(f"🗑️ Deleted link security file: {security_file}")
                except Exception as e:
                    print(f"❌ Failed to delete security file: {e}")
        
        
        # Save eye tracking logs if session had eye tracking
        if request.session_id in eye_tracking_sessions:
            eye_service = eye_tracking_sessions[request.session_id]
            try:
                eye_log_file = eye_service.save_session_log("eye_log")
                if eye_log_file:
                    print(f"👁️ Saved eye tracking log: {eye_log_file}")
            except Exception as e:
                print(f"❌ Failed to save eye tracking log: {e}")
            
            # Clean up eye tracking session
            del eye_tracking_sessions[request.session_id]
            print(f"👁️ Cleaned up eye tracking session: {request.session_id}")
        
        # Clean up session
        completed_session = active_sessions.pop(request.session_id, None)
        
        return {
            "session_id": request.session_id,
            "status": "completed",
            "message": "Interview completed successfully",
            "results": final_results,
            "final_score": final_results["final_score"],
            "questions_answered": len(session["results"]),
            "results_file": results_filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error ending interview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to end interview: {str(e)}")

@app.get("/api/interview/{session_id}/status")
async def get_interview_status(session_id: str, request: Request = None):
    """Get current interview status with browser verification"""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = active_sessions[session_id]
        
        # Verify browser fingerprint
        if request:
            current_fingerprint = generate_browser_fingerprint(request)
            if session.get("browser_fingerprint") != current_fingerprint:
                raise HTTPException(
                    status_code=403,
                    detail="This session is locked to a different browser"
                )
        
        # Check if interview timer has expired
        if check_interview_timer(session_id, session):
            # Auto-end the interview due to time expiry
            session["status"] = "completed"
            session["end_time"] = datetime.now()
            session["end_reason"] = "time_expired"
            raise HTTPException(
                status_code=410,
                detail="Interview session has expired (30-minute time limit reached)"
            )
        
        current_question = session.get("current_question")
        
        # Calculate score
        results = session.get("results", [])
        final_score = 0
        if results:
            total_score = sum(result.get("score", 0) for result in results)
            final_score = round(total_score / len(results), 1)
        
        # Get remaining time
        remaining_time = get_remaining_time_minutes(session)
        
        return {
            "session_id": session_id,
            "status": session["status"],
            "current_question_num": session["current_question_num"],
            "total_questions": session["total_questions"],
            "current_question": current_question,
            "candidate_info": session["candidate_info"],
            "results_count": len(session["results"]),
            "final_score": final_score,
            "remaining_time_minutes": remaining_time,
            "time_limit_minutes": session.get("time_limit_minutes", INTERVIEW_TIME_LIMIT_MINUTES),
            "interview_timer_started": session.get("interview_timer_started", datetime.now()).isoformat() if isinstance(session.get("interview_timer_started"), datetime) else session.get("interview_timer_started")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting interview status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get interview status: {str(e)}")

# ==================== VIOLATION LOGGING ====================

@app.post("/api/violation/log")
async def log_violation(request: ViolationLogRequest):
    """Log a violation/distraction event from the frontend"""
    try:
        print(f"🚨 Violation logged: {request.type} for session {request.sessionId}")
        
        # Create violations directory if it doesn't exist
        os.makedirs("violations", exist_ok=True)
        
        # Log the violation to a file
        violation_data = {
            "session_id": request.sessionId,
            "candidate_email": request.candidateEmail,
            "type": request.type,
            "timestamp": request.timestamp,
            "duration": request.duration,
            "details": request.details,
            "logged_at": datetime.now().isoformat()
        }
        
        # Save to violations log file (match main_fixed.py naming convention)
        violation_file = f"violations/session_{request.sessionId}_violations.json"
        violations_list = []
        
        # Load existing violations if file exists
        if os.path.exists(violation_file):
            try:
                with open(violation_file, 'r') as f:
                    violations_list = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                violations_list = []
        
        # Add new violation
        violations_list.append(violation_data)
        
        # Save back to file
        with open(violation_file, 'w') as f:
            json.dump(violations_list, f, indent=2)
        
        print(f"📝 Violation saved to: {violation_file}")
        
        # Also add to session if it exists
        if request.sessionId in active_sessions:
            if "violations" not in active_sessions[request.sessionId]:
                active_sessions[request.sessionId]["violations"] = []
            active_sessions[request.sessionId]["violations"].append(violation_data)
        
        return {
            "status": "success",
            "message": "Violation logged successfully",
            "violation_id": len(violations_list),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error logging violation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log violation: {str(e)}")

# ==================== SIMPLE FRAME CAPTURE ENDPOINT ====================

@app.post("/api/frames/capture")
async def capture_frame_simple(request: dict):
    """Simple frame capture endpoint - exactly as requested"""
    try:
        session_id = request.get("session_id")
        frame_data = request.get("frame_data")
        timestamp = request.get("timestamp", datetime.now().isoformat())
        
        if not session_id or not frame_data:
            return {"status": "error", "message": "Missing session_id or frame_data"}
        
        # Create session directory in eye_logs
        session_dir = os.path.join("eye_logs", f"session_{session_id}")
        os.makedirs(session_dir, exist_ok=True)
        
        # Get frame counter
        counter_file = os.path.join(session_dir, "frame_counter.txt")
        if os.path.exists(counter_file):
            with open(counter_file, 'r') as f:
                frame_count = int(f.read().strip()) + 1
        else:
            frame_count = 1
            
        # Save new counter
        with open(counter_file, 'w') as f:
            f.write(str(frame_count))
        
        # Decode and save frame
        if frame_data.startswith('data:image'):
            frame_data = frame_data.split(',')[1]
            
        frame_bytes = base64.b64decode(frame_data)
        
        # Save frame as JPEG
        frame_filename = f"frame_{frame_count:06d}.jpg"
        frame_path = os.path.join(session_dir, frame_filename)
        
        with open(frame_path, 'wb') as f:
            f.write(frame_bytes)
            
        # Save metadata
        metadata = {
            "frame_number": frame_count,
            "timestamp": timestamp,
            "filename": frame_filename,
            "session_id": session_id,
            "file_size": len(frame_bytes),
            "saved_at": datetime.now().isoformat()
        }
        
        metadata_file = os.path.join(session_dir, "metadata.json")
        metadata_list = []
        
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                try:
                    metadata_list = json.load(f)
                except:
                    metadata_list = []
                    
        metadata_list.append(metadata)
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata_list, f, indent=2)
            
        # Log every 10th frame to avoid spam
        if frame_count % 10 == 0:
            print(f"📸 Saved frame {frame_count} for session {session_id}")
        
        return {
            "status": "success",
            "frame_number": frame_count,
            "saved_to": frame_path,
            "total_frames": frame_count
        }
        
    except Exception as e:
        print(f"❌ Frame capture error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

# ==================== EYE DETECTION ENDPOINTS ====================

@app.get("/api/eye-detection/test")
async def test_eye_detection():
    """Simple test endpoint to verify eye detection API is working"""
    print("🧪 EYE DETECTION TEST ENDPOINT CALLED")
    return {
        "status": "working",
        "message": "Eye detection API is accessible",
        "timestamp": datetime.now().isoformat(),
        "endpoint": "/api/eye-detection/analyze-frame",
        "active_sessions": list(active_sessions.keys()),
        "session_count": len(active_sessions)
    }

@app.options("/api/eye-detection/analyze-frame")
async def options_analyze_frame():
    """Handle CORS preflight for frame endpoint"""
    print("🔍 CORS PREFLIGHT: Frame analyze endpoint")
    return JSONResponse(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )

@app.post("/api/eye-detection/analyze-frame")
async def analyze_eye_detection_frame(request: EyeDetectionFrameRequest, http_request: Request = None):
    """Save frame for offline eye detection analysis"""
    print(f"📸 FRAME ENDPOINT CALLED: Session {request.session_id}")
    print(f"📸 FRAME DATA LENGTH: {len(request.frame_data)}")
    print(f"📸 TIMESTAMP: {request.timestamp}")
    
    try:
        # Validate session exists and is active
        if request.session_id not in active_sessions:
            print(f"❌ DEBUG: Session {request.session_id} not found in active sessions")
            print(f"❌ DEBUG: Active sessions: {list(active_sessions.keys())}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = active_sessions[request.session_id]
        print(f"✅ DEBUG: Session found: {request.session_id}")
        print(f"✅ DEBUG: Session status: {session.get('status')}")
        
        # Verify browser fingerprint
        if http_request:
            current_fingerprint = generate_browser_fingerprint(http_request)
            if session.get("browser_fingerprint") != current_fingerprint:
                print(f"❌ DEBUG: Browser fingerprint mismatch")
                raise HTTPException(
                    status_code=403,
                    detail="This session is locked to a different browser"
                )
            print(f"✅ DEBUG: Browser fingerprint verified")
        
        # Check if interview timer has expired
        if check_interview_timer(request.session_id, session):
            # Auto-end the interview due to time expiry
            session["status"] = "completed"
            session["end_time"] = datetime.now()
            session["end_reason"] = "time_expired"
            raise HTTPException(
                status_code=410,
                detail="Interview session has expired (30-minute time limit reached)"
            )
        
        if session.get("status") != "active":
            raise HTTPException(status_code=400, detail="Interview session is not active")
        
        # Initialize frame counter for session if not exists
        if "frame_count" not in session:
            session["frame_count"] = 0
        
        session["frame_count"] += 1
        frame_number = session["frame_count"]
        print(f"🔢 DEBUG: Frame number: {frame_number}")
        
        # Create session directory for frames
        session_frame_dir = os.path.join("eye_logs", f"session_{request.session_id}")
        print(f"📁 CREATING DIRECTORY: {session_frame_dir}")
        try:
            os.makedirs(session_frame_dir, exist_ok=True)
            print(f"✅ DIRECTORY CREATED: {session_frame_dir}")
        except Exception as dir_error:
            print(f"❌ DIRECTORY CREATION FAILED: {dir_error}")
            raise
        
        if os.path.exists(session_frame_dir):
            print(f"✅ DEBUG: Directory exists: {session_frame_dir}")
        else:
            print(f"❌ DEBUG: Directory NOT created: {session_frame_dir}")
        
        # Save frame metadata and image
        try:
            # Remove data URL prefix if present
            frame_data = request.frame_data
            print(f"📷 DEBUG: Original frame data length: {len(frame_data)}")
            
            if frame_data.startswith('data:image'):
                frame_data = frame_data.split(',')[1]
                print(f"📷 DEBUG: Stripped data URL, new length: {len(frame_data)}")
            
            # Decode base64 to bytes to validate the frame
            try:
                frame_bytes = base64.b64decode(frame_data)
                print(f"✅ DEBUG: Base64 decode successful, bytes length: {len(frame_bytes)}")
            except Exception as decode_error:
                print(f"❌ DEBUG: Base64 decode failed: {decode_error}")
                raise
            
            # Save the raw frame as JPEG
            timestamp = datetime.now()
            frame_filename = f"frame_{frame_number:06d}_{timestamp.strftime('%H%M%S_%f')[:-3]}.jpg"
            frame_path = os.path.join(session_frame_dir, frame_filename)
            print(f"💾 DEBUG: Attempting to save file to: {frame_path}")
            
            # Write the decoded image bytes to file
            try:
                with open(frame_path, 'wb') as f:
                    f.write(frame_bytes)
                print(f"✅ FRAME SAVED: {frame_path}")
                print(f"✅ FILE SIZE: {len(frame_bytes)} bytes")
                
                # Verify file was actually created and has content
                if os.path.exists(frame_path):
                    file_size = os.path.getsize(frame_path)
                    print(f"✅ DEBUG: File exists with size: {file_size} bytes")
                else:
                    print(f"❌ DEBUG: File NOT found after writing: {frame_path}")
                    
            except Exception as write_error:
                print(f"❌ DEBUG: File write failed: {write_error}")
                raise
            
            # Create metadata entry
            metadata = {
                "frame_number": frame_number,
                "timestamp": timestamp.isoformat(),
                "filename": frame_filename,
                "session_id": request.session_id,
                "candidate_email": session.get("candidate_info", {}).get("email", "unknown"),
                "file_size": len(frame_bytes),
                "saved_at": datetime.now().isoformat()
            }
            
            # Append metadata to session log file
            metadata_file = os.path.join(session_frame_dir, "frames_metadata.json")
            metadata_list = []
            
            # Load existing metadata if file exists
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata_list = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    metadata_list = []
            
            # Add new metadata
            metadata_list.append(metadata)
            
            # Save updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata_list, f, indent=2)
            
            # Log progress every 10 frames to avoid spam
            if frame_number % 10 == 0:
                print(f"📸 Saved frame {frame_number} for session {request.session_id} -> {frame_path}")
            
            # Return simple success response (no heavy processing)
            return {
                "session_id": request.session_id,
                "status": "frame_saved",
                "frame_number": frame_number,
                "timestamp": timestamp.isoformat(),
                "saved_to": frame_path,
                "total_frames": frame_number,
                # Return neutral values since we're not processing
                "face_detected": True,  # Assume face is detected to avoid frontend issues
                "looking_forward": True,  # Assume looking forward
                "gaze_direction": "forward",
                "confidence": 0.8,  # Neutral confidence
                "violation_detected": False,  # No violations detected during saving
                "violation_type": None,
                "violation_duration": 0.0,
                "total_violations": 0
            }
                
        except Exception as e:
            print(f"❌ Error saving frame: {e}")
            return {
                "session_id": request.session_id,
                "status": "error",
                "error": f"Frame saving failed: {str(e)}",
                "frame_number": frame_number,
                # Return safe defaults on error
                "face_detected": True,
                "looking_forward": True,
                "violation_detected": False
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in frame saving endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Frame saving failed: {str(e)}")

# ==================== DATE-BASED LINK GENERATION ENDPOINTS ====================

@app.post("/api/interview/generate-link")
async def generate_interview_link(request: GenerateInterviewLinkRequest, http_request: Request):
    """Generate a secure interview link with encoded date"""
    try:
        print(f"🔗 Generating interview link for session {request.session_id} on date {request.interview_date}")
        
        # Extract base URL from request if not provided
        base_url = request.base_url
        if not base_url:
            # Extract from request headers
            host = http_request.headers.get("host", "localhost:8000")
            protocol = "https" if "ngrok" in host or http_request.headers.get("x-forwarded-proto") == "https" else "http"
            base_url = f"{protocol}://{host}"
        
        # Generate the secure link
        interview_url = interview_security.generate_interview_link(
            base_url=base_url,
            session_id=request.session_id,
            interview_date=request.interview_date
        )
        
        return {
            "status": "success",
            "interview_url": interview_url,
            "session_id": request.session_id,
            "interview_date": request.interview_date,
            "expires_after_24_hours": True,
            "message": f"Interview link generated for {request.interview_date}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error generating interview link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate interview link: {str(e)}")

@app.post("/api/interview/validate-link")
async def validate_interview_link(request: ValidateInterviewLinkRequest):
    """Validate if an interview link can be accessed today"""
    try:
        print(f"🔍 Validating interview link token")
        
        # Validate the link
        can_access, message = interview_security.validate_interview_access(request.token)
        
        if can_access:
            # Extract date for additional info
            interview_date = interview_security.extract_date_from_url_token(request.token)
            
            return {
                "status": "valid",
                "can_access": True,
                "message": message,
                "interview_date": interview_date,
                "current_date": datetime.now().date().isoformat()
            }
        else:
            return {
                "status": "invalid",
                "can_access": False,
                "message": message,
                "current_date": datetime.now().date().isoformat()
            }
    
    except Exception as e:
        print(f"❌ Error validating interview link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate interview link: {str(e)}")

# ==================== DEBUG/ADMIN ENDPOINTS ====================

@app.get("/api/debug/fingerprint")
async def debug_fingerprint(request: Request):
    """Debug endpoint to see current browser fingerprint"""
    fingerprint = generate_browser_fingerprint(request)
    return {
        "fingerprint": fingerprint,
        "headers": {
            "user-agent": request.headers.get("user-agent", "None"),
            "x-forwarded-for": request.headers.get("x-forwarded-for", "None"),
            "x-real-ip": request.headers.get("x-real-ip", "None"),
            "client_host": str(request.client.host) if request.client else "None"
        },
        "active_locks": list(l1_link_locks.keys()),
        "lock_count": len(l1_link_locks)
    }

@app.post("/api/debug/reset-lock/{session_id}")
async def reset_link_lock(session_id: str):
    """Reset link lock for a specific L1 session ID - for debugging"""
    try:
        # Remove from memory lock
        if session_id in l1_link_locks:
            del l1_link_locks[session_id]
            print(f"🔓 DEBUG: Removed link lock for session: {session_id}")
        
        # Remove security file
        security_file = f"link_security/l1_lock_{session_id}.json"
        if os.path.exists(security_file):
            try:
                os.remove(security_file)
                print(f"🗑️ DEBUG: Deleted security file: {security_file}")
            except Exception as e:
                print(f"❌ Failed to delete security file: {e}")
        
        return {
            "status": "success",
            "message": f"Link lock reset for session {session_id}",
            "session_id": session_id,
            "remaining_locks": list(l1_link_locks.keys())
        }
        
    except Exception as e:
        print(f"❌ Error resetting link lock: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset link lock: {str(e)}")

@app.post("/api/debug/clear-all-locks")
async def clear_all_locks():
    """Clear all link locks - for debugging"""
    try:
        cleared_count = len(l1_link_locks)
        l1_link_locks.clear()
        
        # Remove all security files
        security_dir = "link_security"
        if os.path.exists(security_dir):
            import shutil
            shutil.rmtree(security_dir)
            print(f"🗑️ DEBUG: Removed all security files from {security_dir}")
        
        print(f"🔓 DEBUG: Cleared all {cleared_count} link locks")
        
        return {
            "status": "success",
            "message": f"Cleared {cleared_count} link locks",
            "cleared_count": cleared_count
        }
        
    except Exception as e:
        print(f"❌ Error clearing link locks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear link locks: {str(e)}")

# WebSocket functionality has been completely removed

# ==================== MAIN ====================
if __name__ == "__main__":
    print("🎤 AI Interview Platform Backend - No WebSocket Version")
    print("=" * 60)
    print("Features:")
    print("  ✓ Browser Fingerprinting (Link Locking)")
    print("  ✓ 30-Minute Interview Timer")
    print("  ✓ 24-Hour Session Expiry")
    print("  ✓ Automatic Session Cleanup")
    print("  ✓ L1 File Deletion After Completion")
    print("  ✓ UUID Session IDs")
    print("  ✓ Enhanced Violation Logging (Tab Close/Navigation Detection)")
    print("  ✓ Resume/Recovery System")
    print("  ✓ Transcript Processing")
    print("  ✗ WebSocket Support (Removed)")
    print("=" * 60)
    
    # Check required files
    required_files = ["conversational_interview.py", "utils.py", "config.py", "question_engine.py"]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("Please ensure all Python modules are in the same directory")
        sys.exit(1)
    
    # Start server
    uvicorn.run(
        "no_websocket:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
