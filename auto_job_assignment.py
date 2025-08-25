import mysql.connector
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Create database connection"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'recruitment_portal'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        return connection
    except mysql.connector.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None

def assign_job_to_shortlisted_candidates():
    """
    Automatically assign job_id to candidates who have status 2 (shortlisted) but no job_id
    """
    connection = get_db_connection()
    if not connection:
        print("❌ Could not connect to database")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Find candidates with status 2 but no job_id
        cursor.execute("""
            SELECT id, name, email FROM candidates 
            WHERE status = 2 AND (job_id IS NULL OR job_id = 0)
        """)
        candidates_without_jobs = cursor.fetchall()
        
        if not candidates_without_jobs:
            print("✅ No candidates need job assignment")
            return True
        
        print(f"🔍 Found {len(candidates_without_jobs)} candidates needing job assignment")
        
        # Get the most recent active job
        cursor.execute("""
            SELECT id, title FROM jobs 
            WHERE status = 'Active' OR status = 'active'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        available_job = cursor.fetchone()
        
        if not available_job:
            print("⚠️ No active jobs available for assignment")
            return False
        
        job_id, job_title = available_job
        print(f"🎯 Assigning job '{job_title}' (ID: {job_id}) to {len(candidates_without_jobs)} candidates")
        
        # Update candidates with job assignment
        assigned_count = 0
        for candidate_id, name, email in candidates_without_jobs:
            cursor.execute("""
                UPDATE candidates 
                SET job_id = %s, updated_at = %s
                WHERE id = %s
            """, (job_id, datetime.now(), candidate_id))
            
            print(f"✅ Assigned job to: {name} ({email})")
            assigned_count += 1
        
        connection.commit()
        print(f"🎉 Successfully assigned jobs to {assigned_count} candidates")
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

def update_candidate_status_with_job_assignment(candidate_email, new_status):
    """
    Update candidate status and assign job if moving to status 2
    """
    connection = get_db_connection()
    if not connection:
        print("❌ Could not connect to database")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Get current candidate info
        cursor.execute("""
            SELECT id, name, job_id, status FROM candidates 
            WHERE email = %s
        """, (candidate_email,))
        candidate = cursor.fetchone()
        
        if not candidate:
            print(f"❌ Candidate not found: {candidate_email}")
            return False
        
        candidate_id, name, current_job_id, current_status = candidate
        
        # If moving to status 2 and no job assigned, assign one
        if new_status == 2 and not current_job_id:
            # Get available active job
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
                cursor.execute("""
                    UPDATE candidates 
                    SET status = %s, job_id = %s, updated_at = %s
                    WHERE email = %s
                """, (new_status, job_id, datetime.now(), candidate_email))
            else:
                print(f"⚠️ No active jobs available to assign to {name}")
                # Update status without job assignment
                cursor.execute("""
                    UPDATE candidates 
                    SET status = %s, updated_at = %s
                    WHERE email = %s
                """, (new_status, datetime.now(), candidate_email))
        else:
            # Regular status update
            cursor.execute("""
                UPDATE candidates 
                SET status = %s, updated_at = %s
                WHERE email = %s
            """, (new_status, datetime.now(), candidate_email))
        
        connection.commit()
        print(f"✅ Updated {name} status to {new_status}")
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

def get_candidates_without_jobs():
    """
    Get list of shortlisted candidates without job assignments
    """
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, email, status, created_at 
            FROM candidates 
            WHERE status = 2 AND (job_id IS NULL OR job_id = 0)
            ORDER BY created_at DESC
        """)
        candidates = cursor.fetchall()
        return candidates
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("🚀 Starting automatic job assignment process...")
    
    # Show candidates without jobs
    candidates_without_jobs = get_candidates_without_jobs()
    if candidates_without_jobs:
        print(f"\n📋 Candidates without job assignments:")
        for candidate in candidates_without_jobs:
            print(f"   - {candidate['name']} ({candidate['email']}) - Status: {candidate['status']}")
    
    # Run assignment
    success = assign_job_to_shortlisted_candidates()
    
    if success:
        print("\n✅ Job assignment process completed successfully")
    else:
        print("\n❌ Job assignment process failed")
