# utils.py

import re
import requests
import json
import time
from typing import Optional, Callable, Dict, Any

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:latest"

def analyze_response_llm(answer: str, question: str, difficulty: str = "medium", 
                         streaming: bool = False, 
                         callback: Optional[Callable[[str], None]] = None) -> dict:
    """Evaluate answer via LLM with robust parsing & fallback.

    Returns dict: {score:int, feedback:str, raw:str(optional), attempts:int}
    Will attempt up to 2 LLM calls if parsing fails.
    """
    if not answer or len(answer.strip()) < 10:
        return {"score": 0, "feedback": "Answer too short or empty. No score awarded."}

    # Request STRICT JSON to reduce parsing issues
    base_prompt = f"""
You are a technical interviewer. Evaluate the candidate's response.
Difficulty: {difficulty}
Question: {question}
Answer: {answer}

Scoring Guidance:
- EASY: basic correctness. 65+ if clear understanding.
- MEDIUM: practical depth & examples. 55+ if reasonable implementation detail.
- HARD: architectural / advanced depth. 50+ if comprehensive.
Penalize off-topic, filler, or shallow buzzword-only answers.

Return ONLY valid JSON with this exact structure:
{{"score": <0-100 integer>, "feedback": "<detailed feedback>"}}
No extra keys, no markdown, no commentary outside JSON.
"""

    def call_llm() -> str:
        payload = {"model": MODEL_NAME, "prompt": base_prompt, "stream": False}
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def parse(content: str):
        # Try JSON first
        try:
            obj = json.loads(content)
            if isinstance(obj, dict) and "score" in obj and "feedback" in obj:
                score = int(obj.get("score", 0))
                feedback = str(obj.get("feedback", "")).strip()
                if 0 <= score <= 100 and feedback:
                    return score, feedback
        except Exception:
            pass
        # Fallback regex (legacy format)
        score_match = re.search(r"SCORE:\s*(\d{1,3})", content)
        feedback_match = re.search(r"FEEDBACK:\s*(.*)", content, re.DOTALL)
        if score_match and feedback_match:
            try:
                score_val = int(score_match.group(1))
                if 0 <= score_val <= 100:
                    feedback_val = feedback_match.group(1).strip()
                    if feedback_val and "Unable to evaluate" not in feedback_val:
                        return score_val, feedback_val
            except ValueError:
                pass
        # Very last resort: first number 0-100 anywhere
        generic = re.search(r"\b(\d{1,2}|100)\b", content)
        if generic:
            try:
                gv = int(generic.group(1))
                if 0 <= gv <= 100:
                    return gv, content[:400].strip()
            except ValueError:
                pass
        return None

    raw_contents = []
    for attempt in range(1, 3):  # up to 2 attempts
        try:
            content = call_llm()
            raw_contents.append(content)
            parsed = parse(content)
            if parsed:
                score, feedback = parsed
                return {"score": score, "feedback": feedback, "attempts": attempt}
        except Exception as e:
            print(f"❌ LLM Evaluation Error (attempt {attempt}): {e}")
            raw_contents.append(f"ERROR: {e}")
            continue

    print("[EVAL_PARSE_FAILURE] Could not parse LLM output. Raw attempts:")
    for i, rc in enumerate(raw_contents, 1):
        print(f"--- Attempt {i} ---\n{rc[:1000]}\n------------------")
    return {"score": 0, "feedback": "Answer could not be evaluated. No score awarded.", "attempts": len(raw_contents), "raw": raw_contents[-1][:1000] if raw_contents else ""}

def classify_job_role(skills: list) -> str:
    """
    Uses Ollama to classify the job role based on required skills
    """
    skills_text = ", ".join(skills)
    prompt = f"""
Based on these required skills, classify the job role:

Skills: {skills_text}

Common job roles include:
- Data Engineer
- Software Engineer
- DevOps Engineer
- Data Analyst
- Cloud Engineer
- Full Stack Developer
- Backend Developer
- Frontend Developer
- Machine Learning Engineer
- System Administrator

Just return the most appropriate job role title.
"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        content = response.json().get("response", "").strip()
        return content if content else "Software Engineer"
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return "Software Engineer"  # Default fallback

def update_difficulty(current: str, score: int, passing_threshold: int) -> str:
    """
    Adjusts difficulty level based on answer score compared to passing threshold
    More lenient difficulty progression with new thresholds
    """
    levels = ["easy", "medium", "hard"]
    idx = levels.index(current)

    # If they scored exceptionally well (25+ points above threshold), jump two levels if possible
    if score >= passing_threshold + 25 and idx == 0:
        return "hard"  # Jump from easy to hard for exceptional performance
    # If they scored well above threshold (10+ points), increase difficulty
    elif score >= passing_threshold + 10 and idx < 2:
        return levels[idx + 1]
    # If they scored below threshold by 5+ points, decrease difficulty  
    elif score < passing_threshold - 5 and idx > 0:
        return levels[idx - 1]
    # Otherwise keep same difficulty (more stable progression)
    return current

def analyze_response_llm_streaming(answer: str, question: str, difficulty: str = "medium",
                                   print_callback: bool = True) -> dict:
    """
    Convenience wrapper for streaming evaluation with automatic printing.
    
    Args:
        answer: The candidate's answer to evaluate
        question: The original question asked  
        difficulty: Difficulty level (easy, medium, hard)
        print_callback: Whether to print chunks to console
        
    Returns:
        Dictionary with score and feedback
    """
    collected_feedback = []
    
    def stream_printer(chunk: str):
        """Callback to print streaming chunks and collect them"""
        if print_callback:
            print(chunk, end='', flush=True)
        collected_feedback.append(chunk)
    
    result = analyze_response_llm(
        answer=answer,
        question=question,
        difficulty=difficulty,
        streaming=True,
        callback=stream_printer
    )
    
    # Add newline after streaming completes
    if print_callback:
        print()  
    
    # Store the full collected feedback in result for reference
    result['full_feedback'] = ''.join(collected_feedback)
    
    return result

def calculate_final_score(questions: list, expected_total_questions: int = 5) -> dict:
    """
    Calculate weighted final score and overall assessment
    Unanswered questions are scored as 0 to penalize incomplete interviews
    """
    total_weighted_score = 0
    total_weight = 0
    passed_questions = 0
    answered_questions = 0
    
    difficulty_weights = {"easy": 1.0, "medium": 1.5, "hard": 2.0}
    
    # First, calculate scores for answered questions
    for q in questions:
        if q.get('score') != '' and q.get('score') is not None:
            score = int(q['score'])
            weight = difficulty_weights.get(q['difficulty'], 1.0)
            threshold = q['passing_threshold']
            
            total_weighted_score += score * weight
            total_weight += weight
            answered_questions += 1
            
            if score >= threshold:
                passed_questions += 1
    
    # Add penalty for unanswered questions (score = 0 with medium weight)
    unanswered_questions = expected_total_questions - answered_questions
    if unanswered_questions > 0:
        # Assume unanswered questions are medium difficulty for weight calculation
        unanswered_weight = difficulty_weights["medium"] * unanswered_questions
        total_weight += unanswered_weight
        # total_weighted_score += 0 (no need to add since it's 0)
    
    if total_weight == 0:
        return {"final_score": 0, "pass_rate": 0, "overall_status": "No answers evaluated"}
    
    final_score = round(total_weighted_score / total_weight, 1)
    pass_rate = round((passed_questions / expected_total_questions) * 100, 1) if expected_total_questions > 0 else 0
    
    # Determine overall status
    if pass_rate >= 80:
        overall_status = "Excellent"
    elif pass_rate >= 60:
        overall_status = "Good"
    elif pass_rate >= 40:
        overall_status = "Fair"
    else:
        overall_status = "Needs Improvement"
    
    return {
        "final_score": final_score,
        "pass_rate": pass_rate,
        "overall_status": overall_status,
        "questions_answered": answered_questions,
        "questions_passed": passed_questions,
        "total_questions": expected_total_questions
    }  
