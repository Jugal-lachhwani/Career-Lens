"""
Main execution script for Job Search Agent.
"""

import logging
from pathlib import Path
from src.graph import Workflow
from src.state import GraphState

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

# Configure logging with both console and file handlers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('logs/app.log', encoding='utf-8')  # File output
    ]
)

logger = logging.getLogger(__name__)

def main():
    """
    Main function to execute the Job Search Agent workflow.
    """
    try:
        # Initialize the workflow
        logger.info("Starting Job Search Agent")
        workflow = Workflow()
        
        # Create initial state with all required fields
        initial_state = {
            'user_input': 'Give me the 1 Job with 3 years of experience in India in Software engineering',
            'visited_ids': set(),
            'visited_ids_feedback': set()
        }
        
        # Execute the workflow
        logger.info("Executing workflow...")
        final_state = workflow.app.invoke(initial_state)
        
        # Display results
        print("\n" + "="*80)
        print("WORKFLOW EXECUTION COMPLETE")
        print("="*80)
        
        print(f"\n📊 Jobs Found: {len(final_state['job_summaries'])}")
        print(f"📄 Resume Processed: {'Yes' if final_state['resume_text'] else 'No'}")
        
        if final_state.get('job_feedbacks'):
            print("\n📝 FEEDBACK:")
            print(final_state['job_feedbacks'])
        
        print("\n✅ Process completed successfully!")
        
        return final_state
        
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()