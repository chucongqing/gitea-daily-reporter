# /// script
# dependencies = [
#   "requests",
#   "python-dotenv",
#   "openai",
# ]
# ///

import unittest
import os
import sys
from dotenv import load_dotenv
import gitea_summary

class TestAIGeneration(unittest.TestCase):
    def setUp(self):
        # Explicitly load .env to ensure we are testing the file on disk
        load_dotenv()
        
    def test_01_configuration_check(self):
        """
        Verify that necessary environment variables are set.
        """
        print("\n" + "="*40)
        print("Test 1: Configuration Check")
        print("="*40)
        
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        print(f"OPENAI_BASE_URL: {base_url if base_url else 'Default (OpenAI Official)'}")
        print(f"OPENAI_MODEL:    {model}")
        print(f"OPENAI_API_KEY:  {'Present (Starts with ' + api_key[:3] + '...)' if api_key else 'MISSING'}")
        
        if not api_key:
            self.fail("❌ Error: OPENAI_API_KEY is not found in environment variables or .env file.")
        else:
            print("✅ Configuration format looks correct.")

    def test_02_ai_connectivity(self):
        """
        Send a test request to the AI provider to verify connectivity and API key validity.
        """
        print("\n" + "="*40)
        print("Test 2: AI Connectivity & Generation")
        print("="*40)
        
        # Mock commit data for the test
        dummy_commits = [
            {
                "repo": "infrastructure/test-suite", 
                "date": "2024-01-01", 
                "msg": "feat: verify ai connection settings"
            },
            {
                "repo": "infrastructure/test-suite", 
                "date": "2024-01-01", 
                "msg": "fix: resolve timeout issues in api client"
            }
        ]
        
        print("Sending request to AI provider... (This may take a few seconds)")
        
        # Call the actual function from the application
        result = gitea_summary.generate_ai_summary(
            commits_data=dummy_commits,
            report_type="Test Connection Report",
            manual_input="This is a connectivity test."
        )
        
        # Analyze the result
        if result is None:
             self.fail("❌ Error: Result is None. Check if OPENAI_API_KEY is set correctly.")
             
        if result.startswith("AI 生成失败"):
            print(f"\n❌ AI Generation Failed. Response from function:\n{result}")
            self.fail(f"AI Service Error: {result}")
            
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 20, "Response is too short to be valid.")
        
        print("\n✅ AI Response Received Successfully!")
        print("-" * 20 + " FULL RESPONSE " + "-" * 20)
        print(result)
        print("-" * 55)

if __name__ == '__main__':
    # Use a custom test runner or just basic main
    unittest.main()
