# conversational_interview.py
"""
Conversational Interview System
Merges voice_chat.py streaming architecture with interview.py logic
Provides real-time conversational interview experience with streaming responses
"""

import os
import json
import time
import re
import tempfile
import requests
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import pyttsx3
from faster_whisper import WhisperModel
from pathlib import Path
import threading
from queue import Queue

# Import interview-specific modules
from question_engine import choose_next_question, load_existing_questions
from utils import analyze_response_llm, update_difficulty, calculate_final_score
import config

# ==================== CONFIGURATION ====================
# Whisper STT Configuration (default to GPU if available)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "medium.en")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE_TYPE = os.environ.get(
    "WHISPER_COMPUTE_TYPE",
    "float16" if WHISPER_DEVICE == "cuda" else "float32"
)

# Ollama LLM Configuration with Streaming
LLM_MODEL = os.environ.get("LLM_MODEL", config.OLLAMA_MODEL)
OLLAMA_URL = os.environ.get("OLLAMA_API_URL", config.OLLAMA_API_URL)
OLLAMA_GENERATE_URL = f"{OLLAMA_URL.rsplit('/api', 1)[0]}/api/generate"

# Audio Configuration
SAMPLE_RATE = 16000
FRAME_DURATION = 0.5  # seconds per frame
SILENCE_THRESHOLD = 15  # RMS * 1000
SILENCE_DURATION = 15.0  # seconds of silence to end utterance
MIN_UTTERANCE_SECONDS = 0.8  # minimum utterance length
MAX_UTTERANCE_SECONDS = 180  # maximum utterance length (3 minutes)

# Interview Configuration
NUM_QUESTIONS = config.NUM_QUESTIONS
STREAMING_ENABLED = True  # Enable streaming responses
SHOW_REALTIME_FEEDBACK = True  # Show feedback as it's generated

# TTS Configuration
TTS_RATE = 165  # Speech rate for TTS
TTS_VOLUME = 1.0

# ==================== GLOBAL STATE ====================
# Interview state tracking
interview_state = {
    "current_question_num": 0,
    "total_questions": NUM_QUESTIONS,
    "question_pool": None,
    "current_difficulty": "easy",
    "interview_active": False,
    "results": [],
    "start_time": None,
    "end_time": None
}

# Voice interaction state
voice_state = {
    "whisper_model": None,
    "tts_engine": None,
    "assistant_speaking": False,
    "last_tts_end_time": None,
    "user_interrupted": False
}

# ==================== WHISPER STT INITIALIZATION ====================
def initialize_whisper():
    """Initialize Whisper model for speech-to-text"""
    print(f"🎤 Loading Whisper model '{WHISPER_MODEL}' on {WHISPER_DEVICE} ({WHISPER_COMPUTE_TYPE})...")
    try:
        voice_state["whisper_model"] = WhisperModel(
            WHISPER_MODEL, 
            device=WHISPER_DEVICE, 
            compute_type=WHISPER_COMPUTE_TYPE
        )
        print("✅ Whisper model loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to load Whisper model: {e}")
        return False

# ==================== TTS FUNCTIONS ====================
def initialize_tts():
    """Initialize TTS engine with optimal settings"""
    # Don't cache the engine - create fresh each time
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', TTS_RATE)
        engine.setProperty('volume', TTS_VOLUME)
        
        # Try to set a more natural voice if available
        voices = engine.getProperty('voices')
        if voices:
            # Prefer female voice for interviews (often clearer)
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
        
        return engine
    except Exception as e:
        print(f"❌ Failed to initialize TTS: {e}")
        return None

def speak(text: str, max_chunk=220, wait=True):
    """Basic TTS function - simplified and fixed"""
    if not text:
        return
    
    engine = initialize_tts()
    if not engine:
        print(f"[TTS Error] Cannot speak: {text}")
        return
    
    voice_state["assistant_speaking"] = True
    
    try:
        # Simple approach - just speak the text
        engine.say(text)
        engine.runAndWait()
        
    except Exception as e:
        print(f"[TTS Error] {e}")
    finally:
        voice_state["assistant_speaking"] = False
        voice_state["last_tts_end_time"] = time.time()

def conversational_speak(text: str, chunk_size=150, pause_between_chunks=0.3):
    """Alex's speaking function - FULLY FIXED with proper engine management
    This is the main function for Alex to speak.
    """
    if not text:
        return
    
    # Create a fresh engine instance for each speech to ensure proper completion
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', TTS_RATE)
        engine.setProperty('volume', TTS_VOLUME)
        
        # Try to set a better voice if available
        voices = engine.getProperty('voices')
        if voices:
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
    except Exception as e:
        print(f"[TTS Error] Cannot initialize TTS engine: {e}")
        return
    
    voice_state["assistant_speaking"] = True
    voice_state["user_interrupted"] = False
    
    # Normalize text
    normalized_text = re.sub(r"\s+", " ", text).strip()
    
    # Visual feedback - show Alex's message
    print(f"\n💬 Alex (AI Interviewer): {normalized_text}\n")
    
    try:
        # Speak the entire text and ensure it completes
        engine.say(normalized_text)
        engine.runAndWait()
        # Add a small pause after speaking to ensure completion
        time.sleep(0.3)
        
    except Exception as e:
        print(f"[TTS Error] {e}")
        # Try alternative approach if first fails
        try:
            # Create new engine instance
            engine2 = pyttsx3.init()
            engine2.setProperty('rate', TTS_RATE)
            engine2.setProperty('volume', TTS_VOLUME)
            engine2.say(normalized_text)
            engine2.runAndWait()
            time.sleep(0.3)
        except Exception as e2:
            print(f"[TTS Critical Error] {e2}")
    finally:
        voice_state["assistant_speaking"] = False
        voice_state["last_tts_end_time"] = time.time()
        # Ensure engine is properly cleaned up
        try:
            engine.stop()
        except:
            pass

# ==================== AUDIO RECORDING ====================
def record_utterance(custom_prompt=None):
    """Enhanced audio recording with robust silence detection and validation.
    
    Features:
    - 15-second silence detection for natural pauses
    - Minimum utterance length validation (0.8 seconds)
    - Better audio frame handling
    - Visual feedback during recording
    """
    frame_samples = int(FRAME_DURATION * SAMPLE_RATE)
    max_frames = int(MAX_UTTERANCE_SECONDS / FRAME_DURATION)
    silence_frames_needed = int(SILENCE_DURATION / FRAME_DURATION)
    audio_frames = []
    silent_frames = 0
    
    if custom_prompt:
        print(f"🎤 {custom_prompt}")
    
    # Visual indicator for recording
    print("┌" + "─" * 50 + "┐")
    print("│ Recording... (15 seconds of silence to stop)    │")
    print("└" + "─" * 50 + "┘")
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1) as stream:
        for frame_num in range(max_frames):
            frame, _ = stream.read(frame_samples)
            frame = frame.flatten()
            audio_frames.append(frame)
            
            # Calculate RMS for silence detection (matching voice_chat.py approach)
            rms = np.sqrt(np.mean(frame ** 2)) * 1000
            
            if rms < SILENCE_THRESHOLD:
                silent_frames += 1
                # Show progress for silence detection
                if silent_frames % 10 == 0 and silent_frames > 0:
                    remaining = SILENCE_DURATION - (silent_frames * FRAME_DURATION)
                    if remaining > 0:
                        print(f"  ⏱️  Silence detected... {remaining:.1f}s until stop", end='\r')
            else:
                # Reset silence counter when sound detected
                if silent_frames > 0:
                    print(" " * 60, end='\r')  # Clear the line
                silent_frames = 0
            
            # Check if we've reached required silence duration
            if silent_frames >= silence_frames_needed:
                print("\n✅ Recording complete")
                break
    
    # Concatenate frames and ensure proper dtype
    audio = np.concatenate(audio_frames) if audio_frames else np.array([], dtype=np.float32)
    
    # Validate minimum utterance length
    if audio.size > 0:
        duration = audio.size / SAMPLE_RATE
        if duration < MIN_UTTERANCE_SECONDS:
            print(f"⚠️ Recording too short ({duration:.1f}s), minimum is {MIN_UTTERANCE_SECONDS}s")
            return np.array([], dtype=np.float32)
    
    return audio

# ==================== TRANSCRIPTION ====================
def transcribe_audio(audio: np.ndarray):
    """Enhanced transcription with improved anti-hallucination checks.
    
    Features:
    - Minimum utterance length validation (0.8 seconds)
    - Multiple temperature attempts for better accuracy
    - Robust hallucination filtering
    - VAD filter for cleaner transcription
    """
    if audio.size == 0:
        return ""
    
    # Validate minimum utterance length
    duration = audio.size / SAMPLE_RATE
    if duration < MIN_UTTERANCE_SECONDS:
        print(f"⚠️ Audio too short for reliable transcription ({duration:.1f}s)")
        return ""
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav.write(tmp.name, SAMPLE_RATE, audio)
        temp_path = tmp.name
    
    try:
        print("🔄 Transcribing your response...")
        # Use same parameters as voice_chat.py for consistency
        segments, _ = voice_state["whisper_model"].transcribe(
            temp_path,
            vad_filter=True,  # Voice Activity Detection to filter out non-speech
            beam_size=5,      # Higher beam size for better quality
            best_of=5,        # Generate multiple candidates and pick best
            temperature=[0.0, 0.2, 0.5],  # Multiple temperatures for robustness
            condition_on_previous_text=False,  # Avoid context pollution
        )
        
        # Concatenate segments
        text = " ".join(seg.text.strip() for seg in segments).strip()
        
        # Enhanced hallucination filtering
        if _is_hallucination(text):
            print("⚠️ Detected potential hallucination, filtering out...")
            return ""
        
        return text
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return ""
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

def _is_hallucination(text: str) -> bool:
    """Enhanced hallucination detection matching voice_chat.py.
    
    Detects common Whisper hallucinations including:
    - Repeated filler phrases
    - Common false positives like "thank you", "please subscribe"
    - Very short responses that are likely misdetections
    """
    if not text:
        return True
    
    # Normalize text for checking
    norm = re.sub(r"[^a-z ]", "", text.lower())
    words = norm.split()
    
    # Extended list of common Whisper hallucinations
    hallucination_phrases = [
        "thank you", "thank you very much", "thanks for watching", 
        "please subscribe", "you", "thankyou", "goodbye",
        "thanks", "bye", "see you", "subscribe", "like and subscribe"
    ]
    
    # Check for repetitive hallucinations (phrase appears 2+ times in short text)
    for phrase in hallucination_phrases:
        # Count occurrences of the phrase
        phrase_count = norm.count(phrase)
        if phrase_count >= 2 and len(words) < 15:
            return True
    
    # Check for single short hallucinations (4 or fewer words containing hallucination phrase)
    if len(words) <= 4:
        for phrase in hallucination_phrases:
            if phrase in norm:
                return True
    
    # Check for suspiciously repetitive single words
    if len(words) > 0:
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        # If any single word appears more than 50% of the time in short text
        max_count = max(word_counts.values())
        if max_count > len(words) / 2 and len(words) < 10:
            return True
    
    return False

# ==================== LLM STREAMING ====================
def generate_streaming_response(prompt: str, callback=None):
    """Generate LLM response with streaming support"""
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": STREAMING_ENABLED
    }
    
    try:
        with requests.post(OLLAMA_GENERATE_URL, json=payload, stream=True, timeout=600) as r:
            r.raise_for_status()
            full_response = []
            
            for line in r.iter_lines():
                if not line:
                    continue
                
                try:
                    obj = json.loads(line.decode('utf-8'))
                except json.JSONDecodeError:
                    continue
                
                if 'response' in obj:
                    chunk = obj['response']
                    full_response.append(chunk)
                    
                    # Call callback with chunk if provided
                    if callback and chunk:
                        callback(chunk)
                
                if obj.get('done'):
                    break
            
            return "".join(full_response).strip()
            
    except Exception as e:
        return f"Error generating response: {e}"

# ==================== INTERVIEW LOGIC ====================
def load_interview_questions():
    """Load pre-generated interview questions"""
    question_pool = load_existing_questions()
    
    if question_pool is None:
        print("❌ No pre-generated questions found!")
        print("🔧 Please run 'python question_engine.py' first to generate questions.")
        return None
    
    print(f"✅ Loaded {len(question_pool)} interview questions")
    return question_pool

def create_contextual_question_intro(question_num: int, question: dict, current_difficulty: str, 
                                    prev_difficulty: str = None, prev_score: int = None) -> str:
    """Create context-aware introduction for questions based on difficulty changes and performance"""
    import random
    
    question_text = question['question']
    
    # First question - simple introduction
    if question_num == 1:
        intros = [
            f"Let's begin with our first question. {question_text} Take your time to think about it, and when you're ready, go ahead and share your answer.",
            f"Here's our opening question to get us started. {question_text} Feel free to take a moment to organize your thoughts before responding.",
            f"Let's kick things off with this question. {question_text} Remember, there's no rush - take your time to provide a thoughtful answer."
        ]
        return random.choice(intros)
    
    # Check for difficulty changes and performance context
    intro_part = ""
    
    # If they did well on previous question (score >= 70)
    if prev_score and prev_score >= 70:
        if current_difficulty == "hard" and prev_difficulty in ["easy", "medium"]:
            # Moving up to hard after doing well
            intro_part = random.choice([
                "Great job on that last one! Let's try something a bit more challenging. ",
                "Excellent work! I think you're ready for something more advanced. ",
                "That was really well done! Let's step it up a notch with this next question. ",
                "Fantastic answer! You're clearly ready for a tougher challenge. "
            ])
        elif current_difficulty == "medium" and prev_difficulty == "easy":
            # Moving from easy to medium
            intro_part = random.choice([
                "Nice work on that! Let's move on to something with a bit more depth. ",
                "Good job! Let's explore this topic a bit further. ",
                "Well done! Ready for something slightly more involved? ",
                "That was solid! Let's build on that foundation. "
            ])
        else:
            # Maintaining difficulty after good performance
            intro_part = random.choice([
                "Great answer! Let's continue with another question. ",
                "Excellent! Moving on to our next topic. ",
                "Well done! Here's another one for you. ",
                "Good work! Let's keep the momentum going. "
            ])
    
    # If they struggled on previous question (score < 50)
    elif prev_score and prev_score < 50:
        if current_difficulty == "easy" and prev_difficulty in ["medium", "hard"]:
            # Moving down to easier question after struggling
            intro_part = random.choice([
                "No worries, let me ask you something different. ",
                "That's okay, let's try a different angle. ",
                "Don't worry about that one. Let's move on to something else. ",
                "No problem at all. Let me ask you about something else. "
            ])
        else:
            # Encouraging transition after struggle
            intro_part = random.choice([
                "Let's move forward with a fresh question. ",
                "Alright, here's a new opportunity to show your knowledge. ",
                "Let's try something different. ",
                "Moving on to our next area. "
            ])
    
    # Moderate performance (50-69)
    else:
        intro_part = random.choice([
            "Alright, moving on to our next topic. ",
            "Let's continue with another question. ",
            "Here's our next question for you. ",
            "Moving forward, let me ask you this. ",
            "Let's explore another area. "
        ])
    
    # Add question number context for middle and later questions
    if question_num > 3:
        position_context = random.choice([
            f"This is question {question_num}. ",
            f"For question number {question_num}, ",
            f"Here's question {question_num} for you. ",
            ""
        ])
    else:
        position_context = ""
    
    # Combine all parts
    full_intro = f"{intro_part}{position_context}{question_text} "
    
    # Add closing encouragement
    closing = random.choice([
        "Take your time to think about it, and when you're ready, go ahead and share your answer.",
        "Feel free to take a moment to organize your thoughts before responding.",
        "When you're ready, I'd love to hear your thoughts on this.",
        "Take your time and share your answer when you're ready."
    ])
    
    return full_intro + closing

def create_contextual_transition(current_question_num: int, total_questions: int, 
                                last_score: int, last_threshold: int, struggle_count: int) -> str:
    """Create natural transitions between questions based on context"""
    import random
    
    questions_remaining = total_questions - current_question_num
    
    # Check performance on last question
    did_well = last_score >= last_threshold
    
    # Special handling for struggling candidates (3+ consecutive poor performances)
    if struggle_count >= 3:
        encouragement = random.choice([
            "I know some of these questions are challenging, but you're doing great by staying engaged. ",
            "Remember, every interview is a learning experience. Keep going! ",
            "I appreciate your persistence. Let's continue. ",
            "You're showing great determination. Let's keep moving forward. "
        ])
    else:
        encouragement = ""
    
    # Transitions based on progress through interview
    if questions_remaining == 1:
        # Last question coming up
        transitions = [
            f"{encouragement}We're almost done! Just one more question to go.",
            f"{encouragement}Great, we're on our final question now.",
            f"{encouragement}Alright, let's wrap up with one last question.",
            f"{encouragement}Perfect timing - here's our final question."
        ]
    elif questions_remaining <= 3:
        # Near the end
        transitions = [
            f"{encouragement}We're in the home stretch now! Let's continue.",
            f"{encouragement}Just a few more questions to go. Ready for the next one?",
            f"{encouragement}We're making great progress. Let's keep going.",
            f"{encouragement}Almost there! Here's our next question."
        ]
    elif current_question_num <= 2:
        # Early in the interview
        if did_well:
            transitions = [
                "Excellent start! Let's build on that momentum.",
                "Great beginning! Ready for the next question?",
                "You're off to a strong start. Let's continue.",
                "Good work so far! Moving on to the next topic."
            ]
        else:
            transitions = [
                "No worries, we're just getting started. Let's try another one.",
                "That's okay, plenty more opportunities ahead. Ready for the next question?",
                "Let's keep going. Here comes another question.",
                "Moving forward, let's explore a different area."
            ]
    else:
        # Middle of interview
        if did_well:
            transitions = [
                f"{encouragement}Great! Let's continue with the next question.",
                f"{encouragement}Well done! Ready for another one?",
                f"{encouragement}Excellent! Let's keep this momentum going.",
                f"{encouragement}Nice work! Moving on to our next topic.",
                f"{encouragement}Good job! Let's explore another area."
            ]
        else:
            transitions = [
                f"{encouragement}Let's move on to our next topic.",
                f"{encouragement}Alright, here's a fresh question for you.",
                f"{encouragement}Let's try something different.",
                f"{encouragement}Moving forward with another question.",
                f"{encouragement}Let's continue our conversation.",
                f"{encouragement}Alright, let's keep going with the next question.",
                f"{encouragement}Moving forward, let's explore another topic."  
            ]
    
    return random.choice(transitions)

def conduct_interview_question(question_num: int):
    """Conduct a single interview question with conversational flow"""
    # Get previous performance context if available
    prev_score = None
    prev_difficulty = None
    if interview_state["results"]:
        prev_score = interview_state["results"][-1].get('score', None)
        prev_difficulty = interview_state["results"][-1].get('difficulty', None)
    
    # Choose next question
    question = choose_next_question(
        interview_state["question_pool"], 
        interview_state["current_difficulty"]
    )
    
    # Display question info
    print(f"\n{'='*60}")
    print(f"📝 Question {question_num}/{interview_state['total_questions']} ({question['difficulty'].upper()})")
    print(f"{'='*60}")
    
    # Create context-aware introduction based on difficulty change and performance
    question_text = create_contextual_question_intro(
        question_num, 
        question, 
        interview_state["current_difficulty"],
        prev_difficulty,
        prev_score
    )
    
    conversational_speak(question_text)
    time.sleep(1.5)  # Give more time after question is spoken
    
    # Record and transcribe response  
    # Don't show "Please provide your answer..." until Alex finishes speaking
    print("\n🎤 Please provide your answer...")
    audio = record_utterance()
    response_text = transcribe_audio(audio)
    
    if not response_text:
        print("⚠️ No response detected. Let me ask again...")
        conversational_speak("I didn't catch your response. Could you please answer the question again?")
        audio = record_utterance()
        response_text = transcribe_audio(audio)
    
    # Add acknowledgment after receiving the answer
    if response_text:
        # Use the specific phrase you requested
        acknowledgment = "Alright, let me analyze what you've explained..."
        conversational_speak(acknowledgment)  # This will both print and speak
        time.sleep(1.0)  # Give time for speech to complete and natural thinking pause
    
    print(f"\n📜 Your answer: {response_text}\n")
    
    # Store the answer
    question['ans'] = response_text
    
    # Evaluate the response
    evaluation_result = evaluate_response(response_text, question)
    
    # Store evaluation
    question['score'] = evaluation_result['score']
    question['feedback'] = evaluation_result['feedback']
    
    # Provide immediate feedback
    provide_conversational_feedback(evaluation_result, question)
    
    # Update difficulty for next question
    new_difficulty = update_difficulty(
        interview_state["current_difficulty"],
        evaluation_result['score'],
        question['passing_threshold']
    )
    interview_state["current_difficulty"] = new_difficulty
    
    return question

def evaluate_response(response_text: str, question: dict):
    """Evaluate candidate response with streaming real-time feedback"""
    import random
    
    # Check for too short or empty responses
    if len(response_text.strip()) < 3:
        return {
            "score": 0,
            "feedback": "Your answer was too brief to evaluate properly. Try to provide more detail in your responses."
        }
    
    # Check for non-technical responses
    non_technical_phrases = [
        "i don't know", "not sure", "don't have experience",
        "my name is", "i work at", "sorry", "can't answer"
    ]
    
    if any(phrase in response_text.lower() for phrase in non_technical_phrases):
        return {
            "score": 10,
            "feedback": "I notice you weren't able to provide a technical answer. Let's focus on demonstrating your knowledge of the concepts asked about."
        }
    
    # Remove thinking phrases - we already have acknowledgment above
    # Don't speak these intermediate messages
    pass  # Skip thinking phrases to avoid duplicate speech
    
    # Use streaming evaluation for real-time feedback
    # Remove this print - let Alex speak without extra messages
    pass
    
    # Use the regular analyze_response_llm function
    if SHOW_REALTIME_FEEDBACK:
        print("🤖 Analyzing response...")
    
    evaluation = analyze_response_llm(
        response_text,
        question['question'],
        question['difficulty']
    )
    
    return evaluation

def provide_conversational_feedback(evaluation: dict, question: dict):
    """Provide conversational feedback on the answer with encouragement"""
    score = evaluation['score']
    threshold = question['passing_threshold']
    difficulty = question['difficulty']
    
    # Track struggling patterns
    if not hasattr(interview_state, 'struggle_count'):
        interview_state['struggle_count'] = 0
    
    # Determine performance level
    if score >= threshold + 15:
        performance = "excellent"
        interview_state['struggle_count'] = 0  # Reset struggle counter
    elif score >= threshold:
        performance = "good"
        interview_state['struggle_count'] = 0  # Reset struggle counter
    elif score >= threshold - 10:
        performance = "fair"
        interview_state['struggle_count'] = max(0, interview_state['struggle_count'] - 1)
    else:
        performance = "needs improvement"
        interview_state['struggle_count'] += 1
    
    # IMPORTANT: DO NOT SPEAK THE FEEDBACK - ONLY LOG IT
    # Just acknowledge and move to next question
    feedback_intros = {
        "excellent": [
            "Wow, that was an excellent answer! I'm really impressed with your knowledge.",
            "Outstanding! You really nailed that one.",
            "Fantastic response! Your understanding is crystal clear.",
            "That's exactly the kind of answer I was hoping for. Excellent work!"
        ],
        "good": [
            "Good job on that question! You clearly understand the concept.",
            "Well done! You've got a solid grasp of this topic.",
            "Nice work! Your answer shows good understanding.",
            "That's a good answer! You're definitely on the right track."
        ],
        "fair": [
            "That was a reasonable attempt. You're on the right track.",
            "Not bad! You've got some of the key points there.",
            "You're getting there! Just need to flesh out some details.",
            "Decent effort! Let me help you strengthen that answer."
        ],
        "needs improvement": [
            "I appreciate your effort on that one. Let me give you some feedback that might help.",
            "Thanks for giving it a try. Let's work through this together.",
            "No worries, this is a learning opportunity. Here's what to consider.",
            "Don't worry if that was challenging. Let me share some insights."
        ]
    }
    
    # Add special encouragement for struggling candidates
    encouragement_messages = [
        "Don't be discouraged - everyone has different strengths, and you're doing your best.",
        "Remember, interviews are also learning experiences. You're gaining valuable insights.",
        "Keep your confidence up! Every question is a new opportunity to showcase your knowledge.",
        "Stay positive! Your effort and willingness to try are what matter most."
    ]
    
    # Select feedback intro (rotate through options for variety)
    import random
    feedback_intro = random.choice(feedback_intros[performance])
    
    # Construct feedback message
    feedback_message = f"{feedback_intro} "
    
    # Add score information
    if score >= threshold:
        feedback_message += f"You scored {score} out of 100, which passes the threshold of {threshold}. "
    else:
        feedback_message += f"You scored {score} out of 100, which is below the passing threshold of {threshold}. "
    
    # Add brief evaluation insight
    feedback_snippet = evaluation['feedback'][:150] if len(evaluation['feedback']) > 150 else evaluation['feedback']
    feedback_message += feedback_snippet
    
    # Add special encouragement for candidates who are struggling (3+ poor performances)
    if interview_state.get('struggle_count', 0) >= 3:
        encouragement = random.choice(encouragement_messages)
        feedback_message += f" {encouragement}"
    
    # DO NOT SPEAK THE FEEDBACK - Just acknowledge and move on
    # The feedback is only for logging and evaluation purposes
    
    # Print score and feedback for logging only
    print(f"📊 Score: {score}/100 ({'✅ PASS' if score >= threshold else '❌ NEEDS IMPROVEMENT'})")
    print(f"💬 Feedback: {evaluation['feedback']}")

def run_conversational_interview():
    """Main interview loop with conversational flow"""
    print("\n" + "="*60)
    print("🎯 CONVERSATIONAL AI INTERVIEW SYSTEM")
    print("="*60)
    
    # Initialize components
    if not initialize_whisper():
        print("❌ Failed to initialize Whisper. Exiting.")
        return
    
    if not initialize_tts():
        print("❌ Failed to initialize TTS. Exiting.")
        return
    
    # Load questions
    interview_state["question_pool"] = load_interview_questions()
    if not interview_state["question_pool"]:
        return
    
    # Start interview
    interview_state["interview_active"] = True
    interview_state["start_time"] = time.time()
    
    # Warm, professional conversational introduction using Alex persona
    introduction = (
        "Hey there! My name is Alex, and I'll be conducting your technical interview today. "
        "I'm excited to learn about your experience and skills. "
        "Before we dive in, let me explain how this will work. "
        "I'll ask you a series of technical questions, and after each answer, "
        "I'll provide you with constructive feedback. "
        "Feel free to take your time with each response - I'm here to understand "
        "your knowledge and thought process. "
        "Let's start with our first question,"
    )
    
    # Use the new conversational_speak function for natural flow
    conversational_speak(introduction)
    time.sleep(1.5)  # Natural pause before starting
    
    # Conduct interview questions
    for i in range(1, NUM_QUESTIONS + 1):
        interview_state["current_question_num"] = i
        question_result = conduct_interview_question(i)
        interview_state["results"].append(question_result)
        
        # Create contextual transition to next question
        if i < NUM_QUESTIONS:
            # Simple transition without speaking the feedback
            transition = f"Thanks for your response! Now, let's move on to question {i+1}."
            conversational_speak(transition)
            time.sleep(1.2)
    
    # End interview
    interview_state["interview_active"] = False
    interview_state["end_time"] = time.time()
    
    # Calculate and present final results
    present_final_results()

def present_final_results():
    """Present final interview results in an enhanced conversational manner"""
    print("\n" + "="*60)
    print("📊 INTERVIEW COMPLETE - FINAL RESULTS")
    print("="*60)
    
    # Calculate final scores - use only the questions that were actually answered
    final_results = calculate_final_score(interview_state["results"])
    
    # Display results
    print(f"\n🎯 Overall Score: {final_results['final_score']}/100")
    print(f"📈 Pass Rate: {final_results['pass_rate']}% ({final_results['questions_passed']}/{final_results['questions_answered']} questions)")
    print(f"🏆 Overall Performance: {final_results['overall_status']}")
    
    # Calculate interview duration
    duration = interview_state["end_time"] - interview_state["start_time"]
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    print(f"⏱️ Interview Duration: {minutes}m {seconds}s")
    
    # Deliver enhanced conversational final feedback
    deliver_enhanced_final_feedback(final_results, minutes, seconds)
    
    # Save results
    save_interview_results(final_results)

def deliver_enhanced_final_feedback(final_results: dict, minutes: int, seconds: int):
    """Deliver personalized, conversational final feedback with streaming delivery
    
    This function provides a more human-like closing experience with:
    - Natural opening transition
    - Personalized performance assessment
    - Specific strengths and areas for improvement
    - Encouraging and professional closing
    """
    import random
    
    # Start with a natural transition and appreciation
    opening_messages = [
        "Well, that brings us to the end of our interview session. Thank you so much for your time today. Let me share how you did...",
        "And with that, we've completed all the questions. Thank you so much for your time today. Let me share how you did...",
        "That was our final question! Thank you so much for your time today. Let me share how you did...",
        "Excellent, we've finished the interview. Thank you so much for your time today. Let me share how you did..."
    ]
    
    opening = random.choice(opening_messages)
    
    # Build personalized feedback based on performance
    score = final_results['final_score']
    pass_rate = final_results['pass_rate']
    questions_passed = final_results['questions_passed']
    questions_answered = final_results['questions_answered']
    
    # Categorize performance more granularly
    if pass_rate >= 90:
        performance_category = "exceptional"
    elif pass_rate >= 75:
        performance_category = "excellent"
    elif pass_rate >= 60:
        performance_category = "good"
    elif pass_rate >= 45:
        performance_category = "moderate"
    elif pass_rate >= 30:
        performance_category = "developing"
    else:
        performance_category = "early-stage"
    
    # Create performance-specific feedback with natural language
    performance_feedback = create_performance_feedback(
        performance_category, score, pass_rate, 
        questions_passed, questions_answered
    )
    
    # Add specific insights about their performance patterns
    insights = generate_performance_insights()
    
    # Create personalized encouragement
    encouragement = create_personalized_encouragement(performance_category)
    
    # Professional closing
    closing_messages = {
        "exceptional": [
            "It was truly impressive speaking with you today. Best of luck with your next steps!",
            "It's been a pleasure interviewing someone with your level of expertise. Best of luck!",
            "Outstanding work today! It was great speaking with you. Best of luck!"
        ],
        "excellent": [
            "You did really well today! It was great speaking with you. Best of luck!",
            "Excellent performance! It was a pleasure speaking with you. Best of luck!",
            "Great job today! It was wonderful speaking with you. Best of luck!"
        ],
        "good": [
            "Good work today! It was nice speaking with you. Best of luck with everything!",
            "You showed solid knowledge today. It was great speaking with you. Best of luck!",
            "Nice job overall! It was good speaking with you. Best of luck!"
        ],
        "moderate": [
            "Thank you for your effort today. It was good speaking with you. Best of luck with your continued learning!",
            "I appreciate your time and effort. It was nice speaking with you. Best of luck!",
            "Thanks for sharing your knowledge today. It was great speaking with you. Best of luck!"
        ],
        "developing": [
            "Thank you for your time and effort today. Keep learning and growing! It was great speaking with you. Best of luck!",
            "I appreciate you taking on this challenge. Keep building those skills! It was nice speaking with you. Best of luck!",
            "Thanks for your persistence today. Keep working on those fundamentals! It was great speaking with you. Best of luck!"
        ],
        "early-stage": [
            "Thank you for participating today. Every expert was once a beginner - keep learning! It was great speaking with you. Best of luck!",
            "I appreciate your courage in taking this interview. Keep studying and practicing! It was nice speaking with you. Best of luck!",
            "Thanks for your time today. Remember, this is all part of the learning journey! It was great speaking with you. Best of luck!"
        ]
    }
    
    closing = random.choice(closing_messages.get(performance_category, closing_messages["moderate"]))
    
    # Combine all parts into a natural flowing conversation
    full_message = f"{opening} {performance_feedback} {insights} {encouragement} {closing}"
    
    # Use conversational speak for natural delivery with pauses
    conversational_speak(full_message, chunk_size=200, pause_between_chunks=0.4)
    
    # Add a brief pause before saving results notification
    time.sleep(1.0)
    
    # Final administrative note (spoken more casually)
    admin_message = "I've saved a detailed report of your performance for your review. "
    if performance_category in ["exceptional", "excellent", "good"]:
        admin_message += "Keep up the fantastic work!"
    else:
        admin_message += "Remember, every interview is a stepping stone to success!"
    
    conversational_speak(admin_message)

def create_performance_feedback(category: str, score: int, pass_rate: float, 
                               questions_passed: int, questions_answered: int) -> str:
    """Create natural performance feedback based on results"""
    import random
    
    feedback_templates = {
        "exceptional": [
            f"You delivered an exceptional performance today! With a {pass_rate:.0f}% pass rate and "
            f"an overall score of {score} out of 100, you demonstrated mastery across the topics we covered. "
            f"You successfully answered {questions_passed} out of {questions_answered} questions at or above the expected level.",
            
            f"Your performance was truly outstanding! You achieved a remarkable {pass_rate:.0f}% pass rate "
            f"with a final score of {score} points. You excelled in {questions_passed} out of {questions_answered} questions, "
            f"showing deep understanding of the technical concepts."
        ],
        "excellent": [
            f"You did excellently! With a {pass_rate:.0f}% pass rate and a score of {score} out of 100, "
            f"you showed strong technical knowledge. You passed {questions_passed} out of {questions_answered} questions, "
            f"which demonstrates solid expertise.",
            
            f"Great performance today! You achieved a {pass_rate:.0f}% success rate with {score} points overall. "
            f"Successfully handling {questions_passed} out of {questions_answered} questions shows you have "
            f"a strong grasp of the material."
        ],
        "good": [
            f"You performed well today! You achieved a {pass_rate:.0f}% pass rate with an overall score of {score}. "
            f"You successfully answered {questions_passed} out of {questions_answered} questions, "
            f"showing good understanding of many concepts.",
            
            f"Good job overall! With {score} points and a {pass_rate:.0f}% success rate, "
            f"you demonstrated competence in several areas. You passed {questions_passed} of the {questions_answered} questions."
        ],
        "moderate": [
            f"You showed moderate performance with a {pass_rate:.0f}% pass rate and {score} points overall. "
            f"You successfully handled {questions_passed} out of {questions_answered} questions. "
            f"There's definitely room for growth, but you showed knowledge in several areas.",
            
            f"Your performance was mixed, achieving {score} points with a {pass_rate:.0f}% success rate. "
            f"You passed {questions_passed} questions out of {questions_answered}, showing familiarity with some concepts."
        ],
        "developing": [
            f"You're still developing your skills, achieving a {pass_rate:.0f}% pass rate with {score} points. "
            f"You passed {questions_passed} out of {questions_answered} questions. "
            f"This shows you're on the learning path, though there's more work ahead.",
            
            f"With {score} points and passing {questions_passed} of {questions_answered} questions, "
            f"you achieved a {pass_rate:.0f}% success rate. You're building your foundation, "
            f"and continued study will help strengthen your knowledge."
        ],
        "early-stage": [
            f"You completed the interview with a {pass_rate:.0f}% pass rate and {score} points, "
            f"passing {questions_passed} out of {questions_answered} questions. "
            f"While challenging, this experience gives you a clear roadmap for improvement.",
            
            f"You tackled {questions_answered} questions today, passing {questions_passed} of them "
            f"for a {pass_rate:.0f}% rate and {score} total points. "
            f"This baseline will help you focus your studies going forward."
        ]
    }
    
    templates = feedback_templates.get(category, feedback_templates["moderate"])
    return random.choice(templates)

def generate_performance_insights() -> str:
    """Generate insights about performance patterns"""
    import random
    
    # Analyze question difficulty performance
    easy_questions = [q for q in interview_state["results"] if q.get('difficulty') == 'easy']
    medium_questions = [q for q in interview_state["results"] if q.get('difficulty') == 'medium']
    hard_questions = [q for q in interview_state["results"] if q.get('difficulty') == 'hard']
    
    insights = []
    
    if easy_questions:
        easy_avg = sum(q.get('score', 0) for q in easy_questions) / len(easy_questions)
        if easy_avg >= 70:
            insights.append("You handled the fundamental questions very well.")
        elif easy_avg >= 50:
            insights.append("You showed understanding of basic concepts.")
    
    if medium_questions:
        medium_avg = sum(q.get('score', 0) for q in medium_questions) / len(medium_questions)
        if medium_avg >= 70:
            insights.append("Your performance on intermediate topics was particularly strong.")
        elif medium_avg >= 50:
            insights.append("You demonstrated capability with moderate complexity topics.")
    
    if hard_questions:
        hard_avg = sum(q.get('score', 0) for q in hard_questions) / len(hard_questions)
        if hard_avg >= 60:
            insights.append("You even tackled the challenging questions successfully!")
        elif hard_avg >= 40:
            insights.append("You made good attempts at the more complex questions.")
        elif hard_avg > 0:
            insights.append("The advanced questions were challenging, which is completely normal.")
    
    # If no specific insights, provide general observation
    if not insights:
        insights.append("Your answers showed engagement with the material across different topics.")
    
    return " ".join(insights)

def create_personalized_encouragement(category: str) -> str:
    """Create personalized encouragement based on performance"""
    import random
    
    encouragement_messages = {
        "exceptional": [
            "Your expertise really shone through today. You should be very proud of this performance!",
            "This was genuinely one of the stronger interviews I've conducted. Fantastic work!",
            "Your depth of knowledge is impressive. You're clearly well-prepared for senior roles."
        ],
        "excellent": [
            "You clearly put in the work to prepare, and it shows. Well done!",
            "Your strong foundation will serve you well in your career. Keep building on it!",
            "You demonstrated the kind of knowledge that comes from real understanding, not just memorization."
        ],
        "good": [
            "You're on the right track! A bit more practice with advanced topics will take you to the next level.",
            "Your foundation is solid. Focus on deepening your knowledge in a few key areas.",
            "You show good potential. Keep pushing yourself with more challenging problems."
        ],
        "moderate": [
            "You've got the basics, and that's a great starting point. Keep building from here!",
            "Focus on strengthening your fundamentals and gradually tackle more complex topics.",
            "Every expert started where you are. Consistent practice will get you there."
        ],
        "developing": [
            "Don't be discouraged - technical interviews are tough! Use this as a learning experience.",
            "I see potential in your answers. With focused study, you'll see significant improvement.",
            "The fact that you completed this interview shows determination. That counts for a lot!"
        ],
        "early-stage": [
            "Remember, everyone starts somewhere. This interview gives you a clear path forward.",
            "Technical skills can be learned with dedication. You've taken the first step today.",
            "Use this experience to identify areas to focus on. You'll be surprised how quickly you can improve."
        ]
    }
    
    messages = encouragement_messages.get(category, encouragement_messages["moderate"])
    return random.choice(messages)

def save_interview_results(final_results: dict):
    """Save interview results to file"""
    try:
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)
        
        # Save detailed results with answered questions
        results_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "final_results": final_results,
            "questions_answered": interview_state["results"],  # Only the questions that were answered
            "duration_seconds": interview_state["end_time"] - interview_state["start_time"],
            "num_questions": interview_state["current_question_num"],
            "interview_config": {
                "total_questions_planned": NUM_QUESTIONS,
                "starting_difficulty": "easy"
            }
        }
        
        # Save to timestamped file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = f"data/interview_results_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Interview results saved to {results_file}")
        
        # DO NOT overwrite the original questions.json file
        # It should remain as the clean question bank
        # The interview results are already saved in the timestamped file above
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")

# ==================== MAIN ENTRY POINT ====================
def main():
    """Main entry point for the conversational interview system"""
    try:
        print("\n🚀 Starting Conversational Interview System...")
        print("This system combines real-time voice interaction with structured interview assessment.")
        print("\nPress Ctrl+C at any time to stop the interview.\n")
        
        # Run the interview
        run_conversational_interview()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interview interrupted by user")
        if interview_state["interview_active"]:
            conversational_speak("The interview has been stopped. Thank you for your time.")
            # Save partial results if any
            if interview_state["results"]:
                print("💾 Saving partial results...")
                interview_state["end_time"] = time.time()
                save_interview_results(calculate_final_score(interview_state["results"]))
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        conversational_speak("I apologize, but an error occurred. The interview will need to end here.")
    finally:
        print("\n👋 Interview session ended")

if __name__ == "__main__":
    main()
