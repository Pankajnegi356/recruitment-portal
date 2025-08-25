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
    Also update department_id for candidates who have job_id but missing department_id
    """
    connection = get_db_connection()
    if not connection:
        print("❌ Could not connect to database")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Find candidates with status 2 but no job_id OR candidates with job_id but no department_id
        cursor.execute("""
            SELECT id, name, email, job_id, department_id FROM candidates 
            WHERE status = 2 AND (
                (job_id IS NULL OR job_id = 0) OR 
                (job_id IS NOT NULL AND job_id > 0 AND (department_id IS NULL OR department_id = 0))
            )
        """)
        candidates_needing_updates = cursor.fetchall()
        
        if not candidates_needing_updates:
            print("✅ No candidates need job or department assignment")
            return True
        
        print(f"🔍 Found {len(candidates_needing_updates)} candidates needing job/department assignment")
        
        # Separate candidates into two groups
        candidates_without_jobs = []
        candidates_without_departments = []
        
        for candidate_id, name, email, job_id, department_id in candidates_needing_updates:
            if not job_id or job_id == 0:
                candidates_without_jobs.append((candidate_id, name, email))
            elif job_id and (not department_id or department_id == 0):
                candidates_without_departments.append((candidate_id, name, email, job_id))
        
        # Handle candidates without jobs (assign both job and department)
        if candidates_without_jobs:
            # Get the most recent active job
            cursor.execute("""
                SELECT id, title, department_id FROM jobs 
                WHERE status = 'Active' OR status = 'active'
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            available_job = cursor.fetchone()
            
            if not available_job:
                print("⚠️ No active jobs available for assignment")
            else:
                job_id, job_title, department_id = available_job
                print(f"🎯 Assigning job '{job_title}' (ID: {job_id}) with department (ID: {department_id}) to {len(candidates_without_jobs)} candidates")
                
                for candidate_id, name, email in candidates_without_jobs:
                    cursor.execute("""
                        UPDATE candidates 
                        SET job_id = %s, department_id = %s, updated_at = %s
                        WHERE id = %s
                    """, (job_id, department_id, datetime.now(), candidate_id))
                    
                    print(f"✅ Assigned job and department to: {name} ({email})")
        
        # Handle candidates with jobs but missing departments
        if candidates_without_departments:
            print(f"🔄 Updating departments for {len(candidates_without_departments)} candidates with existing jobs")
            
            for candidate_id, name, email, candidate_job_id in candidates_without_departments:
                # Get department for this candidate's job
                cursor.execute("""
                    SELECT department_id, title FROM jobs 
                    WHERE id = %s
                """, (candidate_job_id,))
                job_info = cursor.fetchone()
                
                if job_info and job_info[0]:
                    job_department_id, job_title = job_info
                    cursor.execute("""
                        UPDATE candidates 
                        SET department_id = %s, updated_at = %s
                        WHERE id = %s
                    """, (job_department_id, datetime.now(), candidate_id))
                    
                    print(f"✅ Updated department for: {name} ({email}) - Job: {job_title}")
                else:
                    print(f"⚠️ Could not find department for job ID {candidate_job_id} for candidate: {name}")
        
        connection.commit()
        total_updated = len(candidates_without_jobs) + len(candidates_without_departments)
        print(f"🎉 Successfully updated {total_updated} candidates")
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
                SELECT id, title, department_id FROM jobs 
                WHERE status = 'Active' OR status = 'active'
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            available_job = cursor.fetchone()
            
            if available_job:
                job_id, job_title, department_id = available_job
                print(f"🎯 Assigning job '{job_title}' (ID: {job_id}) with department (ID: {department_id}) to {name}")
                
                # Update with job assignment
                cursor.execute("""
                    UPDATE candidates 
                    SET status = %s, job_id = %s, department_id = %s, updated_at = %s
                    WHERE email = %s
                """, (new_status, job_id, department_id, datetime.now(), candidate_email))
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
    Get list of shortlisted candidates without job assignments or missing departments
    """
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, email, status, job_id, department_id, created_at 
            FROM candidates 
            WHERE status = 2 AND (
                (job_id IS NULL OR job_id = 0) OR 
                (job_id IS NOT NULL AND job_id > 0 AND (department_id IS NULL OR department_id = 0))
            )
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
            if not candidate['job_id'] or candidate['job_id'] == 0:
                print(f"   - {candidate['name']} ({candidate['email']}) - Status: {candidate['status']}")
            else:
                print(f"   - {candidate['name']} ({candidate['email']}) - Status: {candidate['status']} - Job: {candidate['job_id']} (Missing department)")
    
    # Run assignment
    success = assign_job_to_shortlisted_candidates()
    
    if success:
        print("\n✅ Job assignment process completed successfully")
    else:
        print("\n❌ Job assignment process failed")
