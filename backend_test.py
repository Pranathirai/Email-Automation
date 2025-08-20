import requests
import sys
import json
import io
from datetime import datetime

class MailerProAPITester:
    def __init__(self, base_url="https://email-outreach.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_contact_ids = []
        self.created_campaign_ids = []
        self.created_smtp_config_ids = []
        self.auth_token = None
        self.current_user = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, auth_required=False):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'} if not files else {}
        
        # Add auth header if required and available
        if auth_required and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=headers if auth_required else {})
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and 'id' in response_data:
                        print(f"   Response ID: {response_data['id']}")
                    elif isinstance(response_data, list) and len(response_data) > 0:
                        print(f"   Response count: {len(response_data)}")
                    else:
                        print(f"   Response: {str(response_data)[:100]}...")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text}")

            return success, response.json() if response.text and response.status_code != 204 else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    # Authentication Methods
    def test_user_registration(self, email, password, full_name):
        """Test user registration"""
        user_data = {
            "email": email,
            "password": password,
            "full_name": full_name
        }
        success, response = self.run_test(
            f"User Registration - {email}",
            "POST",
            "auth/register",
            200,
            data=user_data
        )
        if success:
            self.current_user = response
            print(f"   Registered user: {response.get('email')} (ID: {response.get('id')})")
        return success, response

    def test_user_login(self, email, password):
        """Test user login and store auth token"""
        login_data = {
            "email": email,
            "password": password
        }
        success, response = self.run_test(
            f"User Login - {email}",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        if success and 'access_token' in response:
            self.auth_token = response['access_token']
            self.current_user = response.get('user', {})
            print(f"   Login successful, token stored")
            print(f"   User: {self.current_user.get('email')} (Plan: {self.current_user.get('subscription_plan')})")
        return success, response

    def test_get_current_user(self):
        """Test getting current user info"""
        success, response = self.run_test(
            "Get Current User Info",
            "GET",
            "auth/me",
            200,
            auth_required=True
        )
        return success, response

    # SMTP Configuration Methods
    def test_create_smtp_config(self, name, provider, email, smtp_host=None, smtp_port=None, 
                               smtp_username=None, smtp_password=None, use_tls=True, daily_limit=300):
        """Create an SMTP configuration"""
        smtp_data = {
            "name": name,
            "provider": provider,
            "email": email,
            "use_tls": use_tls,
            "daily_limit": daily_limit
        }
        
        if smtp_host:
            smtp_data["smtp_host"] = smtp_host
        if smtp_port:
            smtp_data["smtp_port"] = smtp_port
        if smtp_username:
            smtp_data["smtp_username"] = smtp_username
        if smtp_password:
            smtp_data["smtp_password"] = smtp_password

        success, response = self.run_test(
            f"Create SMTP Config - {name} ({provider})",
            "POST",
            "smtp-configs",
            200,
            data=smtp_data,
            auth_required=True
        )
        if success and 'id' in response:
            self.created_smtp_config_ids.append(response['id'])
            print(f"   SMTP Config created: {response.get('name')} (Provider: {response.get('provider')})")
            return response['id']
        return None

    def test_get_smtp_configs(self):
        """Get all SMTP configurations for current user"""
        success, response = self.run_test(
            "Get All SMTP Configs",
            "GET",
            "smtp-configs",
            200,
            auth_required=True
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} SMTP configurations")
            for config in response:
                print(f"     - {config.get('name')} ({config.get('provider')}) - Active: {config.get('is_active')}")
        return success, response

    def test_get_single_smtp_config(self, config_id):
        """Get a specific SMTP configuration"""
        success, response = self.run_test(
            f"Get Single SMTP Config",
            "GET",
            f"smtp-configs/{config_id}",
            200,
            auth_required=True
        )
        if success:
            print(f"   Config: {response.get('name')} - {response.get('email')}")
            print(f"   Host: {response.get('smtp_host')}:{response.get('smtp_port')}")
            print(f"   Verified: {response.get('is_verified')}")
        return success, response

    def test_update_smtp_config(self, config_id, update_data):
        """Update an SMTP configuration"""
        success, response = self.run_test(
            f"Update SMTP Config",
            "PUT",
            f"smtp-configs/{config_id}",
            200,
            data=update_data,
            auth_required=True
        )
        if success:
            print(f"   Updated config: {response.get('name')}")
        return success, response

    def test_delete_smtp_config(self, config_id):
        """Delete an SMTP configuration"""
        success, response = self.run_test(
            f"Delete SMTP Config",
            "DELETE",
            f"smtp-configs/{config_id}",
            200,
            auth_required=True
        )
        return success

    def test_smtp_connection_test(self, config_id, test_email="test@example.com", 
                                 subject="Test Email", content="This is a test email"):
        """Test SMTP connection by sending test email"""
        test_data = {
            "test_email": test_email,
            "subject": subject,
            "content": content
        }
        success, response = self.run_test(
            f"Test SMTP Connection",
            "POST",
            f"smtp-configs/{config_id}/test",
            200,
            data=test_data,
            auth_required=True
        )
        if success:
            print(f"   Test result: {response.get('message')}")
            print(f"   Success: {response.get('success')}")
        return success, response

    def test_smtp_config_stats(self, config_id):
        """Get SMTP configuration statistics"""
        success, response = self.run_test(
            f"Get SMTP Config Stats",
            "GET",
            f"smtp-configs/{config_id}/stats",
            200,
            auth_required=True
        )
        if success:
            print(f"   Daily sent: {response.get('daily_sent_count')}/{response.get('daily_limit')}")
            print(f"   Remaining today: {response.get('remaining_today')}")
            print(f"   Status: {response.get('status')}")
            print(f"   Verified: {response.get('is_verified')}")
        return success, response

    def test_unauthorized_smtp_access(self, config_id):
        """Test accessing SMTP config without authentication (should fail)"""
        success, response = self.run_test(
            "Unauthorized SMTP Access (should fail)",
            "GET",
            f"smtp-configs/{config_id}",
            401,
            auth_required=False
        )
        return success

    def cleanup_created_smtp_configs(self):
        """Clean up SMTP configs created during testing"""
        print(f"\n🧹 Cleaning up {len(self.created_smtp_config_ids)} created SMTP configs...")
        for config_id in self.created_smtp_config_ids:
            try:
                headers = {'Authorization': f'Bearer {self.auth_token}'} if self.auth_token else {}
                response = requests.delete(f"{self.api_url}/smtp-configs/{config_id}", headers=headers)
                if response.status_code == 200:
                    print(f"   ✅ Deleted SMTP config {config_id}")
                else:
                    print(f"   ❌ Failed to delete SMTP config {config_id}")
            except Exception as e:
                print(f"   ❌ Error deleting SMTP config {config_id}: {str(e)}")

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        success, response = self.run_test(
            "Dashboard Stats",
            "GET",
            "stats/dashboard",
            200
        )
        if success:
            required_fields = ['total_contacts', 'total_campaigns', 'recent_contacts', 'active_campaigns']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing field in stats: {field}")
                    return False
            print(f"   Stats: {response}")
        return success

    def test_create_contact(self, first_name, last_name, email, company=None, phone=None, tags=None):
        """Create a contact"""
        contact_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email
        }
        if company:
            contact_data["company"] = company
        if phone:
            contact_data["phone"] = phone
        if tags:
            contact_data["tags"] = tags

        success, response = self.run_test(
            f"Create Contact - {first_name} {last_name}",
            "POST",
            "contacts",
            200,
            data=contact_data
        )
        if success and 'id' in response:
            self.created_contact_ids.append(response['id'])
            return response['id']
        return None

    def test_create_duplicate_contact(self, email):
        """Test creating duplicate contact (should fail)"""
        contact_data = {
            "first_name": "Duplicate",
            "last_name": "Test",
            "email": email
        }
        success, response = self.run_test(
            "Create Duplicate Contact (should fail)",
            "POST",
            "contacts",
            400,
            data=contact_data
        )
        return success

    def test_get_contacts(self):
        """Get all contacts"""
        success, response = self.run_test(
            "Get All Contacts",
            "GET",
            "contacts",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} contacts")
        return success, response

    def test_get_contacts_with_search(self, search_term):
        """Get contacts with search"""
        success, response = self.run_test(
            f"Search Contacts - '{search_term}'",
            "GET",
            f"contacts?search={search_term}",
            200
        )
        return success, response

    def test_get_single_contact(self, contact_id):
        """Get a single contact by ID"""
        success, response = self.run_test(
            f"Get Single Contact",
            "GET",
            f"contacts/{contact_id}",
            200
        )
        return success

    def test_update_contact(self, contact_id, update_data):
        """Update a contact"""
        success, response = self.run_test(
            f"Update Contact",
            "PUT",
            f"contacts/{contact_id}",
            200,
            data=update_data
        )
        return success

    def test_delete_contact(self, contact_id):
        """Delete a contact"""
        success, response = self.run_test(
            f"Delete Contact",
            "DELETE",
            f"contacts/{contact_id}",
            200
        )
        return success

    def test_csv_upload(self):
        """Test CSV upload functionality"""
        # Create a sample CSV content
        csv_content = """first_name,last_name,email,company,phone,tags
John,Doe,john.doe@example.com,Acme Corp,555-1234,lead,prospect
Jane,Smith,jane.smith@example.com,Tech Inc,555-5678,customer
Bob,Johnson,bob.johnson@example.com,,,demo,trial"""

        # Create a file-like object
        csv_file = io.StringIO(csv_content)
        files = {'file': ('test_contacts.csv', csv_file.getvalue(), 'text/csv')}

        success, response = self.run_test(
            "CSV Upload",
            "POST",
            "contacts/upload-csv",
            200,
            files=files
        )
        
        if success:
            print(f"   Contacts created: {response.get('contacts_created', 0)}")
            print(f"   Contacts skipped: {response.get('contacts_skipped', 0)}")
            if response.get('errors'):
                print(f"   Errors: {response['errors']}")
        
        return success

    def test_invalid_csv_upload(self):
        """Test invalid CSV upload (should fail)"""
        # Create a non-CSV file
        files = {'file': ('test.txt', 'This is not a CSV file', 'text/plain')}

        success, response = self.run_test(
            "Invalid CSV Upload (should fail)",
            "POST",
            "contacts/upload-csv",
            400,
            files=files
        )
        return success

    # Campaign Testing Methods
    def test_create_campaign(self, name, subject, content, contact_ids=None, description=None):
        """Create a campaign"""
        campaign_data = {
            "name": name,
            "subject": subject,
            "content": content,
            "contact_ids": contact_ids or [],
            "daily_limit": 50,
            "delay_between_emails": 300,
            "personalization_enabled": True
        }
        if description:
            campaign_data["description"] = description

        success, response = self.run_test(
            f"Create Campaign - {name}",
            "POST",
            "campaigns",
            200,
            data=campaign_data
        )
        if success and 'id' in response:
            self.created_campaign_ids.append(response['id'])
            return response['id']
        return None

    def test_get_campaigns(self):
        """Get all campaigns"""
        success, response = self.run_test(
            "Get All Campaigns",
            "GET",
            "campaigns",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} campaigns")
        return success, response

    def test_get_single_campaign(self, campaign_id):
        """Get a single campaign by ID"""
        success, response = self.run_test(
            f"Get Single Campaign",
            "GET",
            f"campaigns/{campaign_id}",
            200
        )
        return success, response

    def test_update_campaign(self, campaign_id, update_data):
        """Update a campaign"""
        success, response = self.run_test(
            f"Update Campaign",
            "PUT",
            f"campaigns/{campaign_id}",
            200,
            data=update_data
        )
        return success

    def test_delete_campaign(self, campaign_id):
        """Delete a campaign"""
        success, response = self.run_test(
            f"Delete Campaign",
            "DELETE",
            f"campaigns/{campaign_id}",
            200
        )
        return success

    def test_campaign_preview(self, campaign_id, contact_id):
        """Test campaign preview with personalization"""
        success, response = self.run_test(
            f"Campaign Preview",
            "POST",
            f"campaigns/{campaign_id}/preview?contact_id={contact_id}",
            200
        )
        if success:
            required_fields = ['subject', 'content', 'contact']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing field in preview: {field}")
                    return False
            print(f"   Preview subject: {response.get('subject', '')[:50]}...")
            print(f"   Preview content: {response.get('content', '')[:50]}...")
        return success

    def test_campaign_analytics(self, campaign_id):
        """Test campaign analytics endpoint"""
        success, response = self.run_test(
            f"Campaign Analytics",
            "GET",
            f"campaigns/{campaign_id}/analytics",
            200
        )
        if success:
            required_fields = ['campaign_id', 'campaign_name', 'total_emails', 'sent_emails', 
                             'delivered_emails', 'opened_emails', 'clicked_emails', 'bounced_emails', 
                             'failed_emails', 'open_rate', 'click_rate', 'bounce_rate']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing field in analytics: {field}")
                    return False
            print(f"   Analytics: {response}")
        return success

    def test_enhanced_dashboard_stats(self):
        """Test enhanced dashboard stats with new fields"""
        success, response = self.run_test(
            "Enhanced Dashboard Stats",
            "GET",
            "stats/dashboard",
            200
        )
        if success:
            required_fields = ['total_contacts', 'total_campaigns', 'recent_contacts', 
                             'active_campaigns', 'total_emails_sent', 'overall_open_rate']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing field in enhanced stats: {field}")
                    return False
            print(f"   Enhanced Stats: {response}")
        return success

    def cleanup_created_campaigns(self):
        """Clean up campaigns created during testing"""
        print(f"\n🧹 Cleaning up {len(self.created_campaign_ids)} created campaigns...")
        for campaign_id in self.created_campaign_ids:
            try:
                response = requests.delete(f"{self.api_url}/campaigns/{campaign_id}")
                if response.status_code == 200:
                    print(f"   ✅ Deleted campaign {campaign_id}")
                else:
                    print(f"   ❌ Failed to delete campaign {campaign_id}")
            except Exception as e:
                print(f"   ❌ Error deleting campaign {campaign_id}: {str(e)}")

    def cleanup_created_contacts(self):
        """Clean up contacts created during testing"""
        print(f"\n🧹 Cleaning up {len(self.created_contact_ids)} created contacts...")
        for contact_id in self.created_contact_ids:
            try:
                response = requests.delete(f"{self.api_url}/contacts/{contact_id}")
                if response.status_code == 200:
                    print(f"   ✅ Deleted contact {contact_id}")
                else:
                    print(f"   ❌ Failed to delete contact {contact_id}")
            except Exception as e:
                print(f"   ❌ Error deleting contact {contact_id}: {str(e)}")

def main():
    print("🚀 Starting MailerPro API Tests - Focus on SMTP Configuration System")
    print("=" * 70)
    
    tester = MailerProAPITester()
    
    try:
        # Test 1: Root endpoint
        if not tester.test_root_endpoint():
            print("❌ Root endpoint failed, stopping tests")
            return 1

        # Authentication Tests
        print("\n" + "=" * 25 + " AUTHENTICATION TESTS " + "=" * 25)
        
        # Test 2: User Registration
        test_email = f"testuser_{datetime.now().strftime('%Y%m%d_%H%M%S')}@mailerpro.test"
        test_password = "SecurePassword123!"
        test_name = "Test User"
        
        success, user_data = tester.test_user_registration(test_email, test_password, test_name)
        if not success:
            print("❌ User registration failed, stopping tests")
            return 1

        # Test 3: User Login
        success, login_data = tester.test_user_login(test_email, test_password)
        if not success:
            print("❌ User login failed, stopping tests")
            return 1

        # Test 4: Get current user info
        tester.test_get_current_user()

        # SMTP Configuration Tests
        print("\n" + "=" * 25 + " SMTP CONFIGURATION TESTS " + "=" * 25)
        
        # Test 5: Create Gmail SMTP Config
        gmail_config_id = tester.test_create_smtp_config(
            name="My Gmail Account",
            provider="gmail",
            email="user@gmail.com",
            smtp_username="user@gmail.com",
            smtp_password="app_password_123",
            daily_limit=500
        )

        # Test 6: Create Outlook SMTP Config
        outlook_config_id = tester.test_create_smtp_config(
            name="Corporate Outlook",
            provider="outlook",
            email="user@company.com",
            smtp_username="user@company.com",
            smtp_password="outlook_password",
            daily_limit=300
        )

        # Test 7: Create Custom SMTP Config
        custom_config_id = tester.test_create_smtp_config(
            name="Custom SMTP Server",
            provider="custom",
            email="user@customdomain.com",
            smtp_host="mail.customdomain.com",
            smtp_port=587,
            smtp_username="user@customdomain.com",
            smtp_password="custom_password",
            use_tls=True,
            daily_limit=200
        )

        # Test 8: Get all SMTP configs
        success, smtp_configs = tester.test_get_smtp_configs()
        if not success:
            print("❌ Get SMTP configs failed")

        # Test 9: Get single SMTP config
        if gmail_config_id:
            tester.test_get_single_smtp_config(gmail_config_id)

        # Test 10: Update SMTP config
        if outlook_config_id:
            tester.test_update_smtp_config(outlook_config_id, {
                "name": "Updated Corporate Outlook",
                "daily_limit": 400,
                "is_active": True
            })

        # Test 11: Test SMTP connection (will fail with dummy credentials, but should handle gracefully)
        if gmail_config_id:
            tester.test_smtp_connection_test(
                gmail_config_id,
                test_email="test@example.com",
                subject="MailerPro SMTP Test",
                content="This is a test email from MailerPro SMTP configuration system."
            )

        # Test 12: Get SMTP config stats
        if gmail_config_id:
            tester.test_smtp_config_stats(gmail_config_id)

        # Test 13: Test unauthorized access (should fail)
        if gmail_config_id:
            # Temporarily remove auth token
            temp_token = tester.auth_token
            tester.auth_token = None
            tester.test_unauthorized_smtp_access(gmail_config_id)
            tester.auth_token = temp_token

        # Test 14: Delete SMTP config
        if custom_config_id:
            tester.test_delete_smtp_config(custom_config_id)
            # Remove from cleanup list since we deleted it
            if custom_config_id in tester.created_smtp_config_ids:
                tester.created_smtp_config_ids.remove(custom_config_id)

        # Subscription Limits Test
        print("\n" + "=" * 25 + " SUBSCRIPTION LIMITS TEST " + "=" * 25)
        
        # Test 15: Try to create more SMTP configs than allowed (free plan allows 1 inbox)
        # First, let's check current plan limits
        success, user_info = tester.test_get_current_user()
        if success:
            plan = user_info.get('subscription_plan', 'free')
            print(f"   Current plan: {plan}")
            
            # Try to create additional SMTP configs to test limits
            for i in range(3):  # Try to create 3 more (should hit limit)
                extra_config_id = tester.test_create_smtp_config(
                    name=f"Extra SMTP Config {i+1}",
                    provider="custom",
                    email=f"extra{i+1}@test.com",
                    smtp_host="smtp.test.com",
                    smtp_port=587,
                    smtp_username=f"extra{i+1}@test.com",
                    smtp_password="password123"
                )
                if not extra_config_id:
                    print(f"   ✅ Subscription limit enforced at config {i+1}")
                    break

        # Dashboard Stats Test
        print("\n" + "=" * 25 + " DASHBOARD STATS TEST " + "=" * 25)
        
        # Test 16: Enhanced dashboard stats
        tester.test_enhanced_dashboard_stats()

        # Print final results
        print("\n" + "=" * 70)
        print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
        
        if tester.tests_passed == tester.tests_run:
            print("🎉 All SMTP Configuration tests passed!")
            result = 0
        else:
            print("❌ Some tests failed")
            result = 1

    except Exception as e:
        print(f"❌ Unexpected error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        result = 1
    
    finally:
        # Cleanup
        tester.cleanup_created_smtp_configs()
        tester.cleanup_created_campaigns()
        tester.cleanup_created_contacts()
    
    return result

if __name__ == "__main__":
    sys.exit(main())