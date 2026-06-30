"""
Test client for Job Search Agent API.

Simple script to test the API endpoints.
"""

import requests
import json
from pathlib import Path

# API Configuration
API_URL = "http://localhost:8000"
RESUME_PATH = r"E:\\Genai_Projects\\Job_search_Agent\\Resume.pdf"

def test_health_check():
    """Test the health check endpoint."""
    print("\n" + "="*80)
    print("Testing Health Check Endpoint")
    print("="*80)
    
    response = requests.get(f"{API_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    

def test_job_search():
    """Test the job search endpoint."""
    print("\n" + "="*80)
    print("Testing Job Search Endpoint")
    print("="*80)
    
    # Prepare request data
    user_input = "Find me 1 Software Engineer jobs in India with 3 years of experience"
    
    # Check if resume file exists
    if not Path(RESUME_PATH).exists():
        print(f"❌ Resume file not found at: {RESUME_PATH}")
        return
    
    # Send request
    with open(RESUME_PATH, 'rb') as resume_file:
        files = {'resume': ('resume.pdf', resume_file, 'application/pdf')}
        data = {'user_input': user_input}
        
        print(f"\nSending request with:")
        print(f"  User Input: {user_input}")
        print(f"  Resume: {RESUME_PATH}")
        print("\nWaiting for response (this may take 30-60 seconds)...\n")
        
        response = requests.post(
            f"{API_URL}/process-job-search",
            files=files,
            data=data,
            timeout=120  # 2 minutes timeout
        )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ SUCCESS!")
        print(f"\nMessage: {result['message']}")
        print(f"\nJobs Found: {len(result['job_summaries'])}")
        
        # Display job summaries
        for i, job in enumerate(result['job_summaries'], 1):
            print(f"\n--- Job {i} ---")
            print(f"ID: {job['id']}")
            print(f"Info: {job['job_info'][:100]}...")
            print(f"Skills: {', '.join(job['job_skills'][:5])}...")
        
        # Display feedback
        print("\n--- Feedback & Similarity Scores ---")
        for feedback in result['job_feedbacks']:
            print(f"\nJob ID {feedback['id']}: Similarity Score = {feedback['similarity']}/100")
            print(f"Feedback: {feedback['feedback'][:150]}...")
        
        # Display resume summary
        print("\n--- Resume Summary ---")
        resume = result['resume_fields']
        print(f"Skills: {', '.join(resume['skills'][:5])}...")
        print(f"Profile: {resume['profile'][:100]}...")
        
    else:
        print(f"\n❌ ERROR!")
        print(f"Response: {response.text}")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("Job Search Agent API Test Client")
    print("="*80)
    
    try:
        # Test health check
        test_health_check()
        
        # Test job search
        test_job_search()
        
        print("\n" + "="*80)
        print("Tests Completed!")
        print("="*80 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to API server!")
        print("Make sure the server is running: python run_api.py")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
