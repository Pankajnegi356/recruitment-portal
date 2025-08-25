#!/usr/bin/env python3
"""
MySQL Database Updater for Assessment Results
Fetches data from /results-summary API and updates recruitment_portal database
Now uses email column for direct mapping to interview_tests table
"""

import requests
import mysql.connector
import json
import sys
from datetime import datetime
from typing import List, Dict, Any

# Database Configuration - Your VM details
DB_CONFIG = {
    'host': '48.216.217.84',
    'port': 3306,
    'user': 'appuser',
    'password': 'strongpassword',
    'database': 'recruitment_portal',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# API Configuration
API_BASE_URL = "http://48.216.217.84:5174"
RESULTS_API_URL = f"{API_BASE_URL}/results-summary"

# This is how result summary shows answer 
# {
#   "total_assessments": 2,
#   "results": [
#     {
#       "session_id": "db303880-b9d9-45c9-870d-5b5fc386515b",
#       "candidate_name": "Pankaj Negi",
#       "candidate_email": "negipankaj1712@gmail.com",
#       "job_role": "data_science",
#       "total_questions": 25,
#       "correct_answers": 2,
#       "passed": "fail"
#     },
#     {
#       "session_id": "fcd3da1b-6bea-4d96-bf21-34e9c411c4be",
#       "candidate_name": "Shikha Chhabra",
#       "candidate_email": "shikha04c@gmail.com",
#       "job_role": "machine_learning",
#       "total_questions": 25,
#       "correct_answers": 8,
#       "passed": "fail"
#     }
#   ]
# }




# Directory for candidate responses backup - VM Follow_up folder for direct integration
RESPONSES_DIR = "/home/azureuser/Follow_up"
CANDIDATES_FILE = f"{RESPONSES_DIR}/candidates.json"

def get_db_connection():
    """Establish MySQL database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        print("✅ Database connection established")
        return connection
    except mysql.connector.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None

def cleanup_old_candidates_file():
    """Remove old candidates.json file before creating new one"""
    import os
    
    # Create directory if it doesn't exist
    os.makedirs(RESPONSES_DIR, exist_ok=True)
    
    # Remove old candidates.json if it exists
    if os.path.exists(CANDIDATES_FILE):
        try:
            os.remove(CANDIDATES_FILE)
            print(f"🗑️ Removed old candidates.json file")
        except Exception as e:
            print(f"⚠️ Could not remove old candidates.json: {e}")

def save_candidates_backup(full_api_response):
    """Save the full API response to candidates.json for backup"""
    try:
        with open(CANDIDATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(full_api_response, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved assessment results to {CANDIDATES_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving candidates.json: {e}")
        return False

def fetch_assessment_results():
    """Fetch assessment results from the API and save backup"""
    try:
        print("📊 Fetching assessment results from API...")
        response = requests.get(RESULTS_API_URL, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved {data['total_assessments']} assessment results")
            
            # Clean up old candidates.json file
            cleanup_old_candidates_file()
            
            # Save full API response to candidates.json
            save_candidates_backup(data)
            
            # Return just the results for processing
            return data['results']
        else:
            print(f"❌ API request failed: {response.status_code}")
            return []
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API - make sure backend is running")
        return []
    except Exception as e:
        print(f"❌ Error fetching results: {e}")
        return []

def get_or_create_candidate(cursor, candidate_data):
    """Get existing candidate or create new one, returns candidate_id"""
    email = candidate_data['candidate_email'].strip().lower()
    name = candidate_data['candidate_name'].strip()
    
    # First check exact email match
    cursor.execute("SELECT id, name, email FROM candidates WHERE email = %s", (email,))
    result = cursor.fetchone()
    
    if result:
        candidate_id, existing_name, existing_email = result
        print(f"   👤 Found existing candidate: {existing_name} (ID: {candidate_id})")
        print(f"       Email: {existing_email}")
        return candidate_id
    
    # Check for similar email (fuzzy match) to prevent typos
    cursor.execute("SELECT id, name, email FROM candidates WHERE LOWER(email) LIKE %s OR LOWER(name) LIKE %s", 
                   (f"%{email.split('@')[0][:8]}%", f"%{name.split()[0][:5]}%"))
    similar_results = cursor.fetchall()
    
    if similar_results:
        print(f"   ⚠️ Found {len(similar_results)} similar candidate(s):")
        for sid, sname, semail in similar_results:
            print(f"       ID {sid}: {sname} ({semail})")
        
        # Use the first similar candidate to prevent duplicates
        candidate_id = similar_results[0][0]
        print(f"   🔄 Using existing similar candidate ID: {candidate_id} to prevent duplicate")
        
        # Update the email to the correct one if it's slightly different
        cursor.execute("UPDATE candidates SET email = %s WHERE id = %s", (email, candidate_id))
        print(f"   ✏️ Updated email to: {email}")
        return candidate_id
    
    # Only create if no similar candidates found
    insert_query = """
    INSERT INTO candidates (name, email, status, created_at) 
    VALUES (%s, %s, %s, NOW())
    """
    # Status 2 = qualified for assessment (default from your DB schema)
    cursor.execute(insert_query, (name, email, 2))
    candidate_id = cursor.lastrowid
    print(f"   ➕ Created new candidate: {name} (ID: {candidate_id})")
    print(f"       Email: {email}")
    return candidate_id

def check_test_exists_by_email(cursor, email):
    """Check if test result already exists for this email (direct mapping)"""
    cursor.execute("""
        SELECT id, test_score, status, created_at 
        FROM interview_tests 
        WHERE email = %s 
        ORDER BY created_at DESC 
        LIMIT 1
    """, (email,))
    
    result = cursor.fetchone()
    if result:
        test_id, score, status, created_at = result
        status_text = "PASS" if status == 1 else "FAIL"
        print(f"   ⚠️ Test result already exists for {email}")
        print(f"       Previous: Score {score}/25 ({status_text}) on {created_at}")
        return True
    return False

def insert_test_result_with_email(cursor, candidate_id, result_data):
    """Insert test result into interview_tests table with email column"""
    
    # Use raw score (correct_answers) as requested
    test_score = float(result_data['correct_answers'])  # Score out of 25
    
    # Determine status: 3 = pass, 0 = fail (aligned with AI workflow)
    status = 3 if result_data['passed'] == 'pass' else 0
    
    # Insert with email column for direct mapping
    insert_query = """
    INSERT INTO interview_tests (candidate_id, candidate_name, email, test_score, status, created_at) 
    VALUES (%s, %s, %s, %s, %s, NOW())
    """
    
    cursor.execute(insert_query, (
        candidate_id,
        result_data['candidate_name'],
        result_data['candidate_email'],  # New email column
        test_score,
        status
    ))
    
    test_id = cursor.lastrowid
    print(f"   📝 Inserted test result (ID: {test_id}) - Score: {test_score}/25 ({result_data['passed'].upper()})")
    print(f"       Email mapping: {result_data['candidate_email']}")
    return test_id

def update_candidate_status_if_passed(cursor, candidate_id, result_data):
    """Update candidate status based on test result"""
    if result_data['passed'] == 'pass':
        # Status 3 = passed pre-screening test (aligned with AI workflow)
        cursor.execute("""
            UPDATE candidates 
            SET status = 3
            WHERE id = %s
        """, (candidate_id,))
        print(f"   ✅ Updated candidate status to 3 (passed pre-screening)")
    else:
        # Status 0 = rejected (failed assessment)
        cursor.execute("""
            UPDATE candidates 
            SET status = 0
            WHERE id = %s
        """, (candidate_id,))
        print(f"   ❌ Updated candidate status to 0 (rejected)")

def process_assessment_results(results: List[Dict[str, Any]]):
    """Process all assessment results and update database using email mapping"""
    if not results:
        print("ℹ️ No assessment results to process")
        return
    
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        processed_count = 0
        skipped_count = 0
        
        print(f"\n🔄 Processing {len(results)} assessment results...")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Processing: {result['candidate_name']} ({result['candidate_email']})")
            print(f"   📊 Session: {result['session_id'][:8]}...")
            print(f"   💼 Job Role: {result['job_role']}")
            print(f"   🎯 Score: {result['correct_answers']}/{result['total_questions']}")
            
            # Check if test already exists by email (direct mapping)
            if check_test_exists_by_email(cursor, result['candidate_email']):
                print(f"   ⏭️ Skipping duplicate test result...")
                skipped_count += 1
                continue
            
            # Get or create candidate (still need candidate_id for FK)
            candidate_id = get_or_create_candidate(cursor, result)
            
            # Insert test result with email mapping
            insert_test_result_with_email(cursor, candidate_id, result)
            
            # Update candidate status based on result
            update_candidate_status_if_passed(cursor, candidate_id, result)
            
            processed_count += 1
        
        # Commit all changes
        connection.commit()
        
        print("\n" + "=" * 80)
        print(f"🎉 Database update completed!")
        print(f"✅ Processed: {processed_count}")
        print(f"⚠️ Skipped (duplicates): {skipped_count}")
        print(f"📊 Total: {len(results)}")
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        connection.rollback()
    except Exception as e:
        print(f"❌ Processing error: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

def show_database_summary():
    """Show summary of database contents with email mapping"""
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        # Candidates summary
        cursor.execute("SELECT COUNT(*) FROM candidates")
        total_candidates = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM candidates WHERE status = 3")
        passed_candidates = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM candidates WHERE status = 4")
        failed_candidates = cursor.fetchone()[0]
        
        # Tests summary
        cursor.execute("SELECT COUNT(*) FROM interview_tests")
        total_tests = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM interview_tests WHERE status = 1")
        passed_tests = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(test_score) FROM interview_tests")
        avg_score = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT MAX(test_score) FROM interview_tests")
        max_score = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT MIN(test_score) FROM interview_tests")
        min_score = cursor.fetchone()[0] or 0
        
        print(f"\n📊 Database Summary:")
        print("=" * 60)
        print(f"👥 Total Candidates: {total_candidates}")
        print(f"✅ Passed Candidates (Status 3): {passed_candidates}")
        print(f"❌ Failed Candidates (Status 4): {failed_candidates}")
        print(f"📝 Total Tests Completed: {total_tests}")
        print(f"🎯 Tests Passed: {passed_tests}")
        print(f"📈 Average Score: {avg_score:.1f}/25")
        print(f"🏆 Highest Score: {max_score}/25")
        print(f"📉 Lowest Score: {min_score}/25")
        print("=" * 60)
        
        # Show recent test results with email mapping
        cursor.execute("""
            SELECT candidate_name, email, test_score, status, created_at
            FROM interview_tests
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        recent_tests = cursor.fetchall()
        if recent_tests:
            print(f"\n🔍 Recent Test Results (Email Mapping):")
            print("-" * 60)
            for test in recent_tests:
                name, email, score, status, created_at = test
                status_text = "PASS" if status == 1 else "FAIL"
                print(f"   {name}: {score}/25 - {status_text}")
                print(f"   📧 {email} | 📅 {created_at}")
                print()
            print("-" * 60)
        
        # Verify email mapping integrity
        cursor.execute("""
            SELECT COUNT(*) FROM interview_tests it
            LEFT JOIN candidates c ON it.email = c.email
            WHERE c.email IS NULL
        """)
        orphaned_tests = cursor.fetchone()[0]
        
        if orphaned_tests > 0:
            print(f"⚠️ Warning: {orphaned_tests} test results have no matching candidates")
        else:
            print(f"✅ All test results properly mapped via email")
        
    except mysql.connector.Error as e:
        print(f"❌ Database summary error: {e}")
    finally:
        cursor.close()
        connection.close()

def test_database_connection():
    """Test database connection and verify email column exists"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Test candidates table
        cursor.execute("DESCRIBE candidates")
        candidates_schema = cursor.fetchall()
        
        # Test interview_tests table and verify email column
        cursor.execute("DESCRIBE interview_tests")
        tests_schema = cursor.fetchall()
        
        # Check if email column exists in interview_tests
        email_column_exists = any(field[0] == 'email' for field in tests_schema)
        
        if not email_column_exists:
            print("❌ Email column not found in interview_tests table!")
            print("   Please run: ALTER TABLE interview_tests ADD COLUMN email VARCHAR(100) NOT NULL AFTER candidate_name;")
            return False
        
        print("✅ Database connection successful!")
        print("✅ Both tables accessible")
        print("✅ Email column found in interview_tests table")
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Database test failed: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def show_email_mapping_stats():
    """Show statistics about email mapping"""
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        # Count unique emails in each table
        cursor.execute("SELECT COUNT(DISTINCT email) FROM candidates")
        unique_candidates = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT email) FROM interview_tests")
        unique_test_emails = cursor.fetchone()[0]
        
        # Check mapping integrity
        cursor.execute("""
            SELECT 
                c.email, 
                c.name as candidate_name,
                c.status as candidate_status,
                it.test_score,
                it.status as test_status
            FROM candidates c
            LEFT JOIN interview_tests it ON c.email = it.email
            WHERE it.email IS NOT NULL
            ORDER BY it.created_at DESC
        """)
        
        mapped_results = cursor.fetchall()
        
        print(f"\n📧 Email Mapping Statistics:")
        print("=" * 50)
        print(f"👥 Unique candidate emails: {unique_candidates}")
        print(f"📝 Unique test emails: {unique_test_emails}")
        print(f"🔗 Successfully mapped: {len(mapped_results)}")
        print("=" * 50)
        
    except mysql.connector.Error as e:
        print(f"❌ Email mapping stats error: {e}")
    finally:
        cursor.close()
        connection.close()

def cleanup_duplicate_candidates():
    """Clean up duplicate candidate entries"""
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("🧹 Cleaning up duplicate candidates...")
        
        # Find duplicates by similar names or emails
        cursor.execute("""
            SELECT id, name, email, status, created_at
            FROM candidates
            ORDER BY name, email, created_at
        """)
        
        all_candidates = cursor.fetchall()
        duplicates_to_remove = []
        
        for i in range(len(all_candidates)):
            for j in range(i + 1, len(all_candidates)):
                id1, name1, email1, status1, created1 = all_candidates[i]
                id2, name2, email2, status2, created2 = all_candidates[j]
                
                # Check for similar names (ignoring case and spaces)
                name1_clean = name1.lower().replace(' ', '')
                name2_clean = name2.lower().replace(' ', '')
                
                # Check for similar emails or names
                if (name1_clean == name2_clean or 
                    (email1 and email2 and email1.lower() == email2.lower()) or
                    (email1 and email2 and abs(len(email1) - len(email2)) <= 2 and 
                     email1.split('@')[0][:6] == email2.split('@')[0][:6])):
                    
                    # Keep the one with the better status or the older one
                    if status1 >= status2 or created1 < created2:
                        duplicates_to_remove.append(id2)
                        print(f"   🔍 Found duplicate: {name2} (ID: {id2}) -> removing")
                        print(f"       Keeping: {name1} (ID: {id1})")
                    else:
                        duplicates_to_remove.append(id1)
                        print(f"   🔍 Found duplicate: {name1} (ID: {id1}) -> removing")
                        print(f"       Keeping: {name2} (ID: {id2})")
        
        # Remove duplicates
        if duplicates_to_remove:
            unique_duplicates = list(set(duplicates_to_remove))
            print(f"\n🗑️ Removing {len(unique_duplicates)} duplicate candidates...")
            
            for duplicate_id in unique_duplicates:
                cursor.execute("DELETE FROM candidates WHERE id = %s", (duplicate_id,))
                print(f"   ❌ Removed candidate ID: {duplicate_id}")
            
            connection.commit()
            print(f"✅ Cleanup completed! Removed {len(unique_duplicates)} duplicates.")
        else:
            print("✅ No duplicates found!")
        
    except mysql.connector.Error as e:
        print(f"❌ Cleanup error: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

def main():
    """Main function"""
    print("🚀 MySQL Database Updater for Assessment Results")
    print("📧 Using Email Column for Direct Mapping")
    print("=" * 70)
    print(f"🔗 Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"🔗 API: {RESULTS_API_URL}")
    print("=" * 70)
    
    # Test database connection first
    if not test_database_connection():
        print("\n❌ Database connection failed. Please check:")
        print("   - MySQL server is running on 48.216.217.84:3306")
        print("   - Username/password are correct")
        print("   - Database 'recruitment_portal' exists")
        print("   - Tables 'candidates' and 'interview_tests' exist")
        print("   - Email column exists in interview_tests table")
        return
    
    # Fetch results from API
    results = fetch_assessment_results()
    
    if not results:
        print("ℹ️ No results to process. Make sure:")
        print("   1. Backend API is running on http://48.216.217.84:5174")
        print("   2. Some assessments have been completed")
        print("   3. Call /results-summary endpoint to see if data exists")
        return
    
    # Process and update database
    process_assessment_results(results)
    
    print(f"\n💡 Updated Status Codes (AI Workflow):")
    print(f"   - Candidate status: 0=rejected, 2=shortlisted, 3=pre-screening passed")
    print(f"   - Interview_tests status: 0=failed, 3=passed")
    print(f"   - Test scores stored as raw numbers (X/25)")

if __name__ == "__main__":
    main()
