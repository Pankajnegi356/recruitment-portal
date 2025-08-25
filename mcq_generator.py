# import ollama  # Replaced with direct HTTP requests
import json
import random
import requests
from typing import List, Dict, Any
from pydantic import BaseModel
from enum import Enum

# Configure Ollama host for direct HTTP requests
OLLAMA_HOST = 'http://20.197.14.111:11434'

# Removed JobRole enum as roles are now dynamic strings

class ExperienceLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"
    LEAD = "lead"

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class MCQQuestion(BaseModel):
    question: str
    options: Dict[str, str]  # {"A": "option1", "B": "option2", "C": "option3", "D": "option4"}
    correct_answer: str  # "A", "B", "C", or "D"
    difficulty: str
    explanation: str

class QuestionSet(BaseModel):
    job_role: str
    questions: List[MCQQuestion]
    total_questions: int

class MCQGenerator:
    def __init__(self, model_name: str = "llama3.1:latest"):
        self.model_name = model_name
        
        # Experience-level question complexity mapping (affects how questions are generated, not distribution)
        self.experience_complexity = {
            ExperienceLevel.INTERN: "entry_level",
            ExperienceLevel.JUNIOR: "beginner", 
            ExperienceLevel.MID_LEVEL: "intermediate",
            ExperienceLevel.SENIOR: "advanced",
            ExperienceLevel.LEAD: "expert"
        }

    def generate_question_prompt(self, job_role: str, difficulty: Difficulty, num_questions: int, existing_questions: List[str] = None, additional_skills: str = None, experience_level: ExperienceLevel = None) -> str:
        # Default topics ONLY for Core Computer Science Subjects fallback
        default_topics = "SQL, Operating Systems, Computer Networks, Data Structures & Algorithms, Database Management"

        # Use ONLY job-specific skills if available, otherwise use default topics
        if job_role.lower() == "core computer science subjects" or (not additional_skills and not job_role):
            # This is the fallback case - use core CS topics
            combined_topics = default_topics
        elif additional_skills:
            # Use ONLY the job-specific skills, NOT combined with defaults
            combined_topics = additional_skills.strip()
        else:
            # If we have a job role but no additional skills, use the job role as topic
            combined_topics = job_role

        # Create context about existing questions to avoid duplicates
        existing_context = ""
        if existing_questions and len(existing_questions) > 0:
            existing_context = f"""
IMPORTANT - AVOID DUPLICATES:
The following questions have already been generated. DO NOT create similar or duplicate questions:
{chr(10).join([f"- {q}" for q in existing_questions[-10:]])}  # Show last 10 to keep context manageable

You MUST create completely different questions that cover different aspects of the topics.
"""

        # Add experience level context to the prompt
        experience_context = ""
        if experience_level:
            complexity_level = self.experience_complexity[experience_level]
            experience_context = f"""
EXPERIENCE LEVEL CONTEXT:
Target candidate experience level: {experience_level.value.upper()} ({complexity_level})
Adjust question complexity within {difficulty.value} difficulty to match this experience level:
- {ExperienceLevel.INTERN.value}: Very basic concepts, simple definitions, foundational knowledge
- {ExperienceLevel.JUNIOR.value}: Fundamental practices, basic problem-solving, standard procedures
- {ExperienceLevel.MID_LEVEL.value}: Intermediate concepts, practical applications, some optimization
- {ExperienceLevel.SENIOR.value}: Advanced concepts, complex problem-solving, architecture decisions
- {ExperienceLevel.LEAD.value}: Expert-level scenarios, system design, advanced troubleshooting

"""

        prompt = f"""
You are an expert technical interviewer creating {difficulty.value} level MCQ questions for a {job_role} position.

Generate {num_questions} UNIQUE multiple choice questions covering these topics: {combined_topics}

{experience_context}{existing_context}

CRITICAL QUESTION QUALITY REQUIREMENTS:
1. Each question MUST test PRACTICAL KNOWLEDGE, not just definitions
2. Questions should be SCENARIO-BASED when possible (What would you do if..., Which approach is best for...)
3. AVOID circular questions (e.g., "What is X?" with X as an option)
4. AVOID obvious answers or questions with technical terms in both question and correct answer
5. Test UNDERSTANDING and APPLICATION, not just memorization
6. Include realistic code snippets, error scenarios, or problem-solving situations
7. Options should be plausible and test common misconceptions
8. Focus on PRACTICAL SKILLS used in real work environments

BANNED QUESTION PATTERNS:
❌ "What type of X technique is Y?" (when Y is the answer)
❌ "Which of the following is Z?" (when Z is obviously the answer)
❌ Pure definition questions without context
❌ Questions where the answer is stated in the question
❌ Trivial syntax questions without practical application

PREFERRED QUESTION PATTERNS:
✅ "You need to prevent overfitting in your model. Which technique would be most effective?"
✅ "Your code is running slowly. Which optimization would provide the biggest performance gain?"
✅ "You encounter this error: [error]. What is the most likely cause?"
✅ "Which approach is best for handling [specific scenario]?"
✅ "You need to [accomplish task]. What would you implement?"

TECHNICAL REQUIREMENTS:
1. Each question MUST have exactly 4 options (A, B, C, D)
2. Only ONE option should be correct
3. Questions should be {difficulty.value} level appropriate for the role
4. MUST include explanation field for every question
5. Return ONLY valid JSON - no extra text before or after
6. DO NOT use single quotes (') inside question text - use double quotes only
7. DO NOT use backticks (`) anywhere in the JSON
8. Escape all quotes properly in JSON strings
9. Keep code examples simple without complex formatting
10. Each question MUST be completely UNIQUE and DIFFERENT from others
11. Avoid repetitive patterns - vary question structure and topics
12. If existing questions are provided, ensure NO similarity or overlap
13. Respond with JSON only - no additional text or explanations

EXACT JSON FORMAT (no deviations allowed):
{{
  "questions": [
    {{
      "question": "Your question here?",
      "options": {{
        "A": "First option",
        "B": "Second option", 
        "C": "Third option",
        "D": "Fourth option"
      }},
      "correct_answer": "A",
      "difficulty": "{difficulty.value}",
      "explanation": "Brief explanation why this answer is correct"
    }}
  ]
}}

DIFFICULTY GUIDELINES:
- Easy: Basic problem-solving, common scenarios, fundamental best practices
- Medium: Intermediate problem-solving, debugging, choosing between approaches
- Hard: Complex optimization, architecture decisions, advanced troubleshooting

EXAMPLES OF GOOD QUESTIONS BY DIFFICULTY:

EASY EXAMPLE:
"You want to split your dataset for training and testing. What is the recommended ratio?"
A) 50/50 split
B) 80/20 split  
C) 90/10 split
D) 70/30 split

MEDIUM EXAMPLE:
"Your machine learning model has high training accuracy but low validation accuracy. What should you do first?"
A) Increase the learning rate
B) Add regularization techniques
C) Reduce the number of features
D) Collect more training data

HARD EXAMPLE:
"You need to deploy a model that processes 1M requests per day with sub-100ms latency. Which architecture would be most suitable?"
A) Batch processing with daily model updates
B) Real-time inference with model caching
C) Serverless functions with cold starts
D) Single-threaded synchronous processing

Generate exactly {num_questions} questions following these quality standards:
"""
        return prompt

    def validate_response(self, response_text: str, expected_difficulty: str = None) -> Dict[str, Any]:
        """Validate and parse the LLM response with robust error handling"""
        try:
            # Clean the response - remove any markdown formatting and extra text
            cleaned_response = response_text.strip()
            
            # Remove any text before JSON starts
            lines = cleaned_response.split('\n')
            json_start_line = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('{') or '"questions"' in line:
                    json_start_line = i
                    break
            
            if json_start_line >= 0:
                cleaned_response = '\n'.join(lines[json_start_line:])
            
            # Remove markdown code blocks
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
                
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            # Find JSON boundaries more precisely
            start_idx = cleaned_response.find('{')
            if start_idx == -1:
                print("❌ No opening brace found")
                return {"questions": []}
            
            # Find the matching closing brace
            brace_count = 0
            end_idx = -1
            for i in range(start_idx, len(cleaned_response)):
                char = cleaned_response[i]
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if end_idx == -1:
                print("❌ No matching closing brace found")
                return {"questions": []}
            
            json_content = cleaned_response[start_idx:end_idx]
            
            print(f"🧹 Extracted JSON (first 200 chars): {json_content[:200]}...")
            
            # Multiple parsing attempts with progressively more fixes
            for attempt in range(3):
                try:
                    if attempt == 0:
                        # First attempt: direct parsing
                        data = json.loads(json_content)
                    elif attempt == 1:
                        # Second attempt: fix common issues
                        fixed_json = self.fix_json_quotes(json_content)
                        data = json.loads(fixed_json)
                        print("✅ JSON fixed with quote escaping!")
                    else:
                        # Third attempt: aggressive fixing
                        fixed_json = self.aggressive_json_fix(json_content)
                        data = json.loads(fixed_json)
                        print("✅ JSON fixed with aggressive repair!")
                    
                    # If we get here, parsing succeeded
                    return self.validate_and_filter_questions(data, expected_difficulty)
                    
                except json.JSONDecodeError as e:
                    if attempt < 2:
                        print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                        continue
                    else:
                        print(f"❌ All parsing attempts failed: {e}")
                        return {"questions": []}
        
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return {"questions": []}
    
    def fix_json_quotes(self, json_content: str) -> str:
        """Fix common quote issues in JSON"""
        import re
        
        # Fix unescaped quotes in question text and explanations
        lines = json_content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Handle quotes in "question" fields
            if '"question":' in line:
                # Extract the value part after "question":
                match = re.match(r'(\s*"question":\s*")(.*?)("(?:,\s*$|$))', line)
                if match:
                    prefix, content, suffix = match.groups()
                    # Escape internal quotes
                    content = content.replace('"', '\\"')
                    line = prefix + content + suffix
            
            # Handle quotes in "explanation" fields
            elif '"explanation":' in line:
                match = re.match(r'(\s*"explanation":\s*")(.*?)("(?:,\s*$|$))', line)
                if match:
                    prefix, content, suffix = match.groups()
                    # Escape internal quotes
                    content = content.replace('"', '\\"')
                    line = prefix + content + suffix
            
            # Handle quotes in option values
            elif re.search(r'"[ABCD]":\s*"', line):
                match = re.match(r'(\s*"[ABCD]":\s*")(.*?)("(?:,\s*$|$))', line)
                if match:
                    prefix, content, suffix = match.groups()
                    # Escape internal quotes
                    content = content.replace('"', '\\"')
                    line = prefix + content + suffix
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def aggressive_json_fix(self, json_content: str) -> str:
        """Aggressively fix JSON structure issues"""
        import re
        
        # Start with quote fixing
        fixed = self.fix_json_quotes(json_content)
        
        # Fix missing commas between objects
        lines = fixed.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            current_line = line.rstrip()
            
            # Check if we need a comma after this line
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                
                # Add comma after } if next line starts with {
                if (current_line.endswith('}') and 
                    next_line.startswith('{') and 
                    not current_line.endswith(',') and
                    not current_line.endswith('},')
                ):
                    current_line += ','
                
                # Add comma after " if next line contains field
                if (current_line.endswith('"') and 
                    next_line.startswith('"') and 
                    ':' in next_line and
                    not current_line.endswith(',') and
                    not current_line.endswith('",')
                ):
                    current_line = current_line[:-1] + '",'
            
            fixed_lines.append(current_line)
        
        # Join and do final cleanup
        result = '\n'.join(fixed_lines)
        
        # Fix common structural issues
        result = re.sub(r'}\s*{', '},{', result)  # Fix missing commas between objects
        result = re.sub(r'"\s*"([ABCD]"):', r'",\n    "\1:', result)  # Fix missing commas in options
        
        # Ensure proper closing
        if not result.rstrip().endswith('}'):
            open_braces = result.count('{')
            close_braces = result.count('}')
            if open_braces > close_braces:
                result += '}' * (open_braces - close_braces)
        
        return result
    
    def validate_and_filter_questions(self, data: Dict[str, Any], expected_difficulty: str = None) -> Dict[str, Any]:
        """Validate structure and filter out incomplete questions"""
        if "questions" not in data or not isinstance(data["questions"], list):
            return {"questions": []}
        
        valid_questions = []
        for i, q in enumerate(data["questions"]):
            try:
                # Check required fields
                if not all(field in q and q[field] for field in ["question", "options", "correct_answer"]):
                    continue
                
                # Validate options structure
                if not isinstance(q["options"], dict) or set(q["options"].keys()) != {"A", "B", "C", "D"}:
                    continue
                
                # Validate correct answer
                if q["correct_answer"] not in ["A", "B", "C", "D"]:
                    continue
                
                # Add default explanation if missing
                if "explanation" not in q or not q["explanation"]:
                    q["explanation"] = f"This is the correct answer for this {expected_difficulty or 'level'} question."
                
                # Set difficulty
                q["difficulty"] = expected_difficulty or "standard"
                
                valid_questions.append(q)
                
            except Exception:
                continue  # Skip invalid questions
        
        print(f"✅ Validation passed: {len(valid_questions)} valid questions found")
        return {"questions": valid_questions}


    def generate_questions(self, job_role: str, difficulty: Difficulty, num_questions: int, existing_questions: List[str] = None, additional_skills: str = None, experience_level: ExperienceLevel = None) -> List[MCQQuestion]:
        """Generate questions for a specific difficulty level using Ollama"""
        print(f"🔄 Generating {num_questions} {difficulty.value} questions for {job_role}...")
        
        try:
            # Generate prompt
            prompt = self.generate_question_prompt(job_role, difficulty, num_questions, existing_questions, additional_skills, experience_level)
            
            # Make request to Ollama
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 4000
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                response_data = response.json()
                response_text = response_data.get('response', '')
                
                print(f"📝 Raw Ollama response (first 200 chars): {response_text[:200]}...")
                
                # Validate and parse response
                validated_data = self.validate_response(response_text, difficulty.value)
                
                if validated_data and "questions" in validated_data and validated_data["questions"]:
                    questions = []
                    for q_data in validated_data["questions"]:
                        question = MCQQuestion(
                            question=q_data["question"],
                            options=q_data["options"],
                            correct_answer=q_data["correct_answer"],
                            difficulty=q_data["difficulty"],
                            explanation=q_data["explanation"]
                        )
                        questions.append(question)
                    
                    print(f"✅ Successfully generated {len(questions)} questions from Ollama")
                    return questions
                else:
                    print("❌ No valid questions in Ollama response")
                    return []
            else:
                print(f"❌ Ollama request failed with status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error generating questions with Ollama: {e}")
            return []

    def generate_complete_question_set(self, job_role: str, additional_skills: str = None, difficulty_mix: Dict[str, int] = None, experience_level: ExperienceLevel = None) -> QuestionSet:
        """Generate a complete set of 25 questions (10 easy, 10 medium, 5 hard) with experience-level complexity"""
        
        # Always use standard 25-question distribution (10 easy, 10 medium, 5 hard)
        # Experience level affects the complexity of questions within each difficulty, not the distribution
        difficulty_mix = {"easy": 10, "medium": 10, "hard": 5}
        
        all_questions = []
        used_questions = set()  # Track used questions to avoid duplicates
        existing_question_texts = []  # Track question texts for context
        
        print(f"🚀 Starting question generation for {job_role}")
        if experience_level:
            print(f"� Experience Level: {experience_level.value} (affects question complexity within each difficulty)")
        print(f"📊 Question Distribution: {difficulty_mix} (Total: 25 questions)")
        if additional_skills:
            print(f"🎯 Including additional skills from job description: {additional_skills}")
        
        # Generate easy questions
        easy_count = difficulty_mix.get("easy", 10)
        if easy_count > 0:
            print(f"📚 Generating {easy_count} easy questions...")
            easy_questions = []
            attempts = 0
            while len(easy_questions) < easy_count and attempts < 8:
                batch_questions = self.generate_questions(job_role, Difficulty.EASY, min(5, easy_count), existing_question_texts, additional_skills, experience_level)
                # Filter out duplicate questions
                for question in batch_questions:
                    question_text = question.question.lower().strip()
                    if question_text not in used_questions and len(easy_questions) < easy_count:
                        used_questions.add(question_text)
                        existing_question_texts.append(question.question)
                        easy_questions.append(question)
                attempts += 1
                print(f"   Easy questions so far: {len(easy_questions)}/{easy_count}")
            
            all_questions.extend(easy_questions[:easy_count])
        
        # Generate medium questions
        medium_count = difficulty_mix.get("medium", 10)
        if medium_count > 0:
            print(f"📖 Generating {medium_count} medium questions...")
            medium_questions = []
            attempts = 0
            while len(medium_questions) < medium_count and attempts < 8:
                batch_questions = self.generate_questions(job_role, Difficulty.MEDIUM, min(5, medium_count), existing_question_texts, additional_skills, experience_level)
                # Filter out duplicate questions
                for question in batch_questions:
                    question_text = question.question.lower().strip()
                    if question_text not in used_questions and len(medium_questions) < medium_count:
                        used_questions.add(question_text)
                        existing_question_texts.append(question.question)
                        medium_questions.append(question)
                attempts += 1
                print(f"   Medium questions so far: {len(medium_questions)}/{medium_count}")
            
            all_questions.extend(medium_questions[:medium_count])
        
        # Generate hard questions
        hard_count = difficulty_mix.get("hard", 5)
        if hard_count > 0:
            print(f"📘 Generating {hard_count} hard questions...")
            hard_questions = []
            attempts = 0
            while len(hard_questions) < hard_count and attempts < 6:
                batch_questions = self.generate_questions(job_role, Difficulty.HARD, min(5, hard_count), existing_question_texts, additional_skills, experience_level)
                # Filter out duplicate questions
                for question in batch_questions:
                    question_text = question.question.lower().strip()
                    if question_text not in used_questions and len(hard_questions) < hard_count:
                        used_questions.add(question_text)
                        existing_question_texts.append(question.question)
                        hard_questions.append(question)
                attempts += 1
                print(f"   Hard questions so far: {len(hard_questions)}/{hard_count}")
            
            all_questions.extend(hard_questions[:hard_count])
        
        print(f"📊 Total questions generated: {len(all_questions)}")
        print(f"   - Easy: {len([q for q in all_questions if q.difficulty == 'easy'])}")
        print(f"   - Medium: {len([q for q in all_questions if q.difficulty == 'medium'])}")
        print(f"   - Hard: {len([q for q in all_questions if q.difficulty == 'hard'])}")
        
        # Shuffle the questions to randomize order
        random.shuffle(all_questions)
        
        return QuestionSet(
            job_role=job_role,
            questions=all_questions,
            total_questions=len(all_questions)
        )
