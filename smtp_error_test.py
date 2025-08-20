import requests
import sys
import json
from datetime import datetime

class SMTPErrorHandlingTester:
    def __init__(self, base_url="https://email-outreach.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.auth_token = None
        self.current_user = None
        self.test_results = {}

    def authenticate(self):
        """Authenticate and get token"""
        print("🔐 Authenticating...")
        
        # Register a new user
        test_email = f"smtptest_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        test_password = "SecurePassword123!"
        test_name = "SMTP Error Test User"
        
        # Register
        register_data = {
            "email": test_email,
            "password": test_password,
            "full_name": test_name
        }
        
        response = requests.post(f"{self.api_url}/auth/register", json=register_data)
        if response.status_code != 200:
            print(f"❌ Registration failed: {response.text}")
            return False
        
        print(f"✅ User registered: {test_email}")
        
        # Login
        login_data = {
            "email": test_email,
            "password": test_password
        }
        
        response = requests.post(f"{self.api_url}/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.text}")
            return False
        
        login_response = response.json()
        self.auth_token = login_response['access_token']
        self.current_user = login_response.get('user', {})
        print(f"✅ Login successful, token obtained")
        return True

    def create_test_smtp_config(self, name, provider, email, smtp_host=None, smtp_port=None, 
                               smtp_username=None, smtp_password=None, use_tls=True):
        """Create an SMTP configuration for testing"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        
        smtp_data = {
            "name": name,
            "provider": provider,
            "email": email,
            "use_tls": use_tls,
            "daily_limit": 100
        }
        
        if smtp_host:
            smtp_data["smtp_host"] = smtp_host
        if smtp_port:
            smtp_data["smtp_port"] = smtp_port
        if smtp_username:
            smtp_data["smtp_username"] = smtp_username
        if smtp_password:
            smtp_data["smtp_password"] = smtp_password

        response = requests.post(f"{self.api_url}/smtp-configs", json=smtp_data, headers=headers)
        
        if response.status_code == 200:
            config_data = response.json()
            print(f"✅ SMTP Config created: {name} (ID: {config_data['id']})")
            return config_data['id']
        else:
            print(f"❌ Failed to create SMTP config: {response.text}")
            return None

    def test_smtp_connection(self, config_id, test_name):
        """Test SMTP connection and analyze error response"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        
        test_data = {
            "test_email": "test@example.com",
            "subject": f"SMTP Error Test - {test_name}",
            "content": f"Testing SMTP error handling for {test_name}"
        }
        
        print(f"\n🔍 Testing SMTP Connection: {test_name}")
        response = requests.post(f"{self.api_url}/smtp-configs/{config_id}/test", 
                               json=test_data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Status: {response.status_code}")
            print(f"   Success: {result.get('success')}")
            print(f"   Message: {result.get('message', 'No message')}")
            print(f"   Error Type: {result.get('error_type', 'No error type')}")
            
            # Analyze the response
            analysis = self.analyze_error_response(result, test_name)
            self.test_results[test_name] = analysis
            
            return result
        else:
            print(f"   ❌ Request failed with status {response.status_code}: {response.text}")
            return None

    def analyze_error_response(self, response, test_name):
        """Analyze error response for correctness"""
        analysis = {
            "test_name": test_name,
            "passed": False,
            "issues": [],
            "response": response
        }
        
        # Check required fields
        if 'success' not in response:
            analysis["issues"].append("Missing 'success' field")
        elif response.get('success') is not False:
            analysis["issues"].append("'success' should be False for error cases")
        
        if 'message' not in response:
            analysis["issues"].append("Missing 'message' field")
        elif not response.get('message') or len(response.get('message', '').strip()) == 0:
            analysis["issues"].append("'message' field is empty")
        
        # Check for error_type (optional but recommended)
        if 'error_type' not in response:
            analysis["issues"].append("Missing 'error_type' field (recommended)")
        
        # Specific checks based on test type
        message = response.get('message', '').lower()
        error_type = response.get('error_type', '')
        
        if test_name == "Gmail Authentication Error":
            # Should detect Gmail authentication issues
            if 'gmail' not in message and 'app password' not in message:
                analysis["issues"].append("Gmail-specific guidance not provided")
            if error_type not in ['authentication_failed', 'gmail_app_password_required']:
                analysis["issues"].append(f"Unexpected error type: {error_type}")
        
        elif test_name == "Connection Failed":
            if 'connect' not in message:
                analysis["issues"].append("Connection error not properly described")
            if error_type != 'connection_failed':
                analysis["issues"].append(f"Expected 'connection_failed', got '{error_type}'")
        
        elif test_name == "SSL/TLS Error":
            if 'ssl' not in message and 'tls' not in message:
                analysis["issues"].append("SSL/TLS error not properly described")
            if error_type != 'ssl_tls_error':
                analysis["issues"].append(f"Expected 'ssl_tls_error', got '{error_type}'")
        
        # If no issues found, test passed
        if len(analysis["issues"]) == 0:
            analysis["passed"] = True
            print(f"   ✅ {test_name}: All checks passed")
        else:
            print(f"   ❌ {test_name}: Issues found:")
            for issue in analysis["issues"]:
                print(f"      - {issue}")
        
        return analysis

    def cleanup_smtp_config(self, config_id):
        """Delete SMTP configuration"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        response = requests.delete(f"{self.api_url}/smtp-configs/{config_id}", headers=headers)
        
        if response.status_code == 200:
            print(f"✅ Cleaned up SMTP config {config_id}")
        else:
            print(f"❌ Failed to cleanup SMTP config {config_id}")

    def run_error_handling_tests(self):
        """Run comprehensive SMTP error handling tests"""
        print("🚀 Starting SMTP Error Handling Tests")
        print("=" * 60)
        
        if not self.authenticate():
            return False
        
        test_configs = []
        
        try:
            # Test 1: Gmail Authentication Error (535 error)
            print("\n📧 Test 1: Gmail Authentication Error")
            gmail_config_id = self.create_test_smtp_config(
                name="Gmail Auth Test",
                provider="gmail",
                email="testuser@gmail.com",
                smtp_username="testuser@gmail.com",
                smtp_password="wrong_password_not_app_password"
            )
            
            if gmail_config_id:
                test_configs.append(gmail_config_id)
                self.test_smtp_connection(gmail_config_id, "Gmail Authentication Error")
            
            # Test 2: Connection Failed Error
            print("\n🔌 Test 2: Connection Failed Error")
            # We can't create more configs due to free plan limits, so let's update the existing one
            if gmail_config_id:
                # Update the config to use a non-existent server
                headers = {'Authorization': f'Bearer {self.auth_token}'}
                update_data = {
                    "smtp_host": "nonexistent.smtp.server.com",
                    "smtp_port": 587
                }
                response = requests.put(f"{self.api_url}/smtp-configs/{gmail_config_id}", 
                                      json=update_data, headers=headers)
                
                if response.status_code == 200:
                    print("✅ Updated config for connection test")
                    self.test_smtp_connection(gmail_config_id, "Connection Failed")
                
                # Test 3: SSL/TLS Error
                print("\n🔒 Test 3: SSL/TLS Error")
                # Update config for SSL/TLS error (wrong port/protocol combination)
                update_data = {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 465,  # SSL port
                    "use_tls": True,   # But trying to use TLS instead of SSL
                    "use_ssl": False
                }
                response = requests.put(f"{self.api_url}/smtp-configs/{gmail_config_id}", 
                                      json=update_data, headers=headers)
                
                if response.status_code == 200:
                    print("✅ Updated config for SSL/TLS test")
                    self.test_smtp_connection(gmail_config_id, "SSL/TLS Error")
            
            # Print summary
            self.print_test_summary()
            
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup
            print("\n🧹 Cleaning up...")
            for config_id in test_configs:
                self.cleanup_smtp_config(config_id)
        
        return True

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📊 SMTP Error Handling Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["passed"])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        
        print("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"   {status} {test_name}")
            
            if not result["passed"]:
                for issue in result["issues"]:
                    print(f"      - {issue}")
        
        print("\n🎯 Key Findings:")
        
        # Check if error response format is consistent
        format_issues = []
        for result in self.test_results.values():
            response = result["response"]
            if 'success' not in response:
                format_issues.append("Missing 'success' field")
            if 'message' not in response:
                format_issues.append("Missing 'message' field")
            if 'error_type' not in response:
                format_issues.append("Missing 'error_type' field")
        
        if not format_issues:
            print("   ✅ All error responses have consistent format")
        else:
            print("   ❌ Error response format issues found")
        
        # Check if Gmail-specific guidance is provided
        gmail_tests = [r for r in self.test_results.values() if "Gmail" in r["test_name"]]
        if gmail_tests:
            gmail_guidance_provided = any("Gmail-specific guidance not provided" not in r["issues"] 
                                        for r in gmail_tests)
            if gmail_guidance_provided:
                print("   ✅ Gmail-specific error guidance is provided")
            else:
                print("   ❌ Gmail-specific error guidance needs improvement")
        
        print(f"\n🏆 Overall Success Rate: {passed_tests}/{total_tests} ({(passed_tests/total_tests*100):.1f}%)")

def main():
    tester = SMTPErrorHandlingTester()
    success = tester.run_error_handling_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())