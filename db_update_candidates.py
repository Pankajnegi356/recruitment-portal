import mysql.connector
import json
from datetime import datetime
from typing import List, Dict, Any

# Database configuration - UPDATE THESE VALUES
DB_CONFIG = {
    'host': '48.216.217.84',        # Update with your MySQL host
    'user': 'appuser',             # Update with your MySQL username
    'password': 'strongpassword', # Update with your MySQL password
    'database': 'recruitment_portal'   # Update with your database name
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        print(f"❌ Database connection error: {e}")
        return None

def ensure_summary_column():
    """Add summary column to candidates table if it doesn't exist"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        # Check if summary column exists
        cursor.execute("DESCRIBE candidates")
        columns = [column[0] for column in cursor.fetchall()]
        
        if 'summary' not in columns:
            cursor.execute("ALTER TABLE candidates ADD COLUMN summary TEXT AFTER phone")
            connection.commit()
            print("✅ Added summary column to candidates table")
        
        return True
    except mysql.connector.Error as e:
        print(f"❌ Error adding summary column: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def extract_experience_years(summary: str) -> int:
    """Extract years of experience from summary text"""
    import re
    
    # Look for patterns like "8 years", "over 5 years", "5+ years", etc.
    patterns = [
        r'(\d+)\+?\s*years?\s*of\s*experience',
        r'over\s*(\d+)\s*years?',
        r'(\d+)\+?\s*years?\s*experience',
        r'experience\s*of\s*(\d+)\+?\s*years?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, summary.lower())
        if match:
            return int(match.group(1))
    
    return None  # Return None if no experience found

def update_candidates_from_skill_matching(output: List[Dict], threshold: float = 0.3):
    """
    Update candidates table with skill matching results
    Only candidates above threshold are marked as shortlisted (status = 2)
    
    Args:
        output: List of candidate dictionaries from skill matching
        threshold: Minimum score required for shortlisting (default: 0.3)
    """
    if not output:
        print("⚠️ No candidates to update in database")
        return False
    
    # Ensure summary column exists
    if not ensure_summary_column():
        print("❌ Failed to ensure database schema is ready")
        return False
    
    connection = get_db_connection()
    if not connection:
        print("❌ Failed to connect to database")
        return False
    
    try:
        cursor = connection.cursor()
        
        shortlisted_count = 0
        rejected_count = 0
        updated_count = 0
        
        print(f"🔄 Processing {len(output)} candidates with threshold: {threshold}")
        
        for candidate in output:
            name = candidate.get('Name', 'Unknown')
            email = candidate.get('Email', '')
            phone = candidate.get('Phone', '')
            summary = candidate.get('Summary', '')
            score = candidate.get('Score', 0.0)
            
            if not email:
                print(f"⚠️ Skipping candidate {name} - no email provided")
                continue
            
            # Determine status based on threshold
            if score >= threshold:
                status = 2  # Shortlisted for prescreening
                shortlisted_count += 1
                status_text = "SHORTLISTED"
            else:
                status = 0  # Rejected based on skill match
                rejected_count += 1
                status_text = "REJECTED"
            
            # Check if candidate already exists
            cursor.execute("SELECT id, status FROM candidates WHERE email = %s", (email,))
            existing = cursor.fetchone()
            
            # Extract experience years from summary
            experience_years = extract_experience_years(summary)
            
            if existing:
                existing_id, existing_status = existing
                
                # Check if candidate needs job assignment when moving to status 2
                cursor.execute("SELECT job_id FROM candidates WHERE email = %s", (email,))
                current_job = cursor.fetchone()
                current_job_id = current_job[0] if current_job else None
                
                # If candidate is being shortlisted (status 2) and has no job_id, assign one
                if status == 2 and not current_job_id:
                    # Get an available active job
                    cursor.execute("""
                        SELECT id, title FROM jobs 
                        WHERE status = 'Active' OR status = 'active'
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """)
                    available_job = cursor.fetchone()
                    
                    if available_job:
                        job_id, job_title = available_job
                        print(f"🎯 Assigning job '{job_title}' (ID: {job_id}) to {name}")
                        
                        # Update with job assignment
                        if experience_years is not None:
                            update_query = """
                            UPDATE candidates 
                            SET name = %s, phone = %s, summary = %s, skill_match_score = %s, status = %s, experience_years = %s, job_id = %s, updated_at = %s
                            WHERE email = %s
                            """
                            cursor.execute(update_query, (name, phone, summary, score, status, experience_years, job_id, datetime.now(), email))
                        else:
                            update_query = """
                            UPDATE candidates 
                            SET name = %s, phone = %s, summary = %s, skill_match_score = %s, status = %s, job_id = %s, updated_at = %s
                            WHERE email = %s
                            """
                            cursor.execute(update_query, (name, phone, summary, score, status, job_id, datetime.now(), email))
                    else:
                        print(f"⚠️ No active jobs available to assign to {name}")
                        # Update without job assignment
                        if experience_years is not None:
                            update_query = """
                            UPDATE candidates 
                            SET name = %s, phone = %s, summary = %s, skill_match_score = %s, status = %s, experience_years = %s, updated_at = %s
                            WHERE email = %s
                            """
                            cursor.execute(update_query, (name, phone, summary, score, status, experience_years, datetime.now(), email))
                        else:
                            update_query = """
                            UPDATE candidates 
                            SET name = %s, phone = %s, summary = %s, skill_match_score = %s, status = %s, updated_at = %s
                            WHERE email = %s
                            """
                            cursor.execute(update_query, (name, phone, summary, score, status, datetime.now(), email))
                else:
                    # Regular update (preserve existing job_id)
                    if experience_years is not None:
                        update_query = """
                        UPDATE candidates 
                        SET name = %s, phone = %s, summary = %s, skill_match_score = %s, status = %s, experience_years = %s, updated_at = %s
                        WHERE email = %s
                        """
                        cursor.execute(update_query, (name, phone, summary, score, status, experience_years, datetime.now(), email))
                    else:
                        update_query = """
                        UPDATE candidates 
                        SET name = %s, phone = %s, summary = %s, skill_match_score = %s, status = %s, updated_at = %s
                        WHERE email = %s
                        """
                        cursor.execute(update_query, (name, phone, summary, score, status, datetime.now(), email))
                
                if existing_status == 1:
                    print(f"🔄 Updated Applied Candidate: {name} ({email}) - Score: {score:.3f} - {status_text}")
                else:
                    print(f"🔄 Updated Existing: {name} ({email}) - Score: {score:.3f} - {status_text}")
            else:
                # Insert new candidate (AI-sourced, no job application)
                if experience_years is not None:
                    insert_query = """
                    INSERT INTO candidates (name, email, phone, summary, skill_match_score, status, source, experience_years, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (name, email, phone, summary, score, status, 'ai_screening', experience_years, datetime.now()))
                else:
                    insert_query = """
                    INSERT INTO candidates (name, email, phone, summary, skill_match_score, status, source, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (name, email, phone, summary, score, status, 'ai_screening', datetime.now()))
                
                exp_text = f" - {experience_years} years exp" if experience_years else ""
                print(f"➕ Added AI Candidate: {name} ({email}) - Score: {score:.3f} - {status_text}{exp_text}")
            
            updated_count += 1
        
        # Commit all changes
        connection.commit()
        
        # Print summary
        print(f"\n🎉 DATABASE UPDATE SUMMARY")
        print("=" * 50)
        print(f"📊 Total candidates processed: {updated_count}")
        print(f"✅ Shortlisted (Score >= {threshold}): {shortlisted_count}")
        print(f"❌ Rejected (Score < {threshold}): {rejected_count}")
        print(f"🎯 Threshold used: {threshold}")
        print("=" * 50)
        
        # Show shortlisted candidates
        if shortlisted_count > 0:
            print(f"\n📋 SHORTLISTED CANDIDATES:")
            cursor.execute("""
                SELECT name, email, skill_match_score 
                FROM candidates 
                WHERE status = 2 
                ORDER BY skill_match_score DESC
            """)
            shortlisted = cursor.fetchall()
            for i, (name, email, score) in enumerate(shortlisted, 1):
                print(f"  {i}. {name} ({email}) - Score: {score:.3f}")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        connection.rollback()
        return False
    
    finally:
        cursor.close()
        connection.close()

def get_shortlisted_candidates():
    """Get all shortlisted candidates (status = 2) for scheduling assessments"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, email, phone, summary, skill_match_score 
            FROM candidates 
            WHERE status = 2 
            ORDER BY skill_match_score DESC
        """)
        candidates = cursor.fetchall()
        return candidates
    
    except mysql.connector.Error as e:
        print(f"❌ Error fetching shortlisted candidates: {e}")
        return []
    
    finally:
        cursor.close()
        connection.close()

def update_candidate_assessment_status(email: str, status: int):
    """
    Update candidate status after assessment scheduling
    Args:
        email: Candidate email
        status: New status (3 = assessment sent, 4 = assessment completed, etc.)
    """
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE candidates 
            SET status = %s 
            WHERE email = %s
        """, (status, email))
        connection.commit()
        return cursor.rowcount > 0
    
    except mysql.connector.Error as e:
        print(f"❌ Error updating candidate status: {e}")
        return False
    
    finally:
        cursor.close()
        connection.close()

def show_database_stats():
    """Show current database statistics"""
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        # Count by status
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                CASE 
                    WHEN status = 0 THEN 'Rejected'
                    WHEN status = 1 THEN 'Applied'
                    WHEN status = 2 THEN 'Shortlisted'
                    WHEN status = 3 THEN 'Assessment Sent'
                    WHEN status = 4 THEN 'Assessment Completed'
                    ELSE 'Unknown'
                END as status_name
            FROM candidates 
            GROUP BY status 
            ORDER BY status
        """)
        
        stats = cursor.fetchall()
        
        print(f"\n📊 CANDIDATES DATABASE STATS")
        print("=" * 40)
        total_candidates = 0
        for status, count, status_name in stats:
            print(f"{status_name}: {count}")
            total_candidates += count
        print(f"Total: {total_candidates}")
        
        # Show recent additions
        cursor.execute("""
            SELECT name, email, skill_match_score, created_at
            FROM candidates 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        recent = cursor.fetchall()
        if recent:
            print(f"\n🕐 RECENT CANDIDATES:")
            for name, email, score, created in recent:
                score_text = f"Score: {score:.3f}" if score else "No Score"
                print(f"  • {name} ({email}) - {score_text} - {created}")
    
    except mysql.connector.Error as e:
        print(f"❌ Error fetching stats: {e}")
    
    finally:
        cursor.close()
        connection.close()

# Test function
if __name__ == "__main__":
    print("🧪 Testing database connection and schema...")
    
    # Test database connection
    connection = get_db_connection()
    if connection:
        print("✅ Database connection successful")
        connection.close()
    else:
        print("❌ Database connection failed")
        print("Please update DB_CONFIG with your database credentials")
        exit(1)
    
    # Test with sample data
    test_output = [
        {
            'Name': 'John Doe',
            'Email': 'john@example.com',
            'Phone': '+91-1234567890',
            'Summary': 'Experienced developer with 5 years in Python and machine learning',
            'Score': 0.45
        },
        {
            'Name': 'Jane Smith',
            'Email': 'jane@example.com', 
            'Phone': '+91-0987654321',
            'Summary': 'Junior developer with 2 years experience in web development',
            'Score': 0.25
        }
    ]
    
    print("\n🧪 Testing with sample data...")
    success = update_candidates_from_skill_matching(test_output, threshold=0.3)
    
    if success:
        print("\n✅ Test completed successfully!")
        show_database_stats()
    else:
        print("\n❌ Test failed!")
