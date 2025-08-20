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
            if 'error_type' in response:
                print(f"   Error type: {response.get('error_type')}")
        return success, response

    def test_smtp_error_handling_gmail_app_password(self):
        """Test Gmail App Password error handling"""
        # Create Gmail config with regular password (should trigger App Password error)
        gmail_config_id = self.test_create_smtp_config(
            name="Gmail Test - Regular Password",
            provider="gmail",
            email="testuser@gmail.com",
            smtp_username="testuser@gmail.com",
            smtp_password="regular_password_not_app_password",
            daily_limit=100
        )
        
        if gmail_config_id:
            success, response = self.test_smtp_connection_test(
                gmail_config_id,
                test_email="test@example.com",
                subject="Gmail App Password Test",
                content="Testing Gmail App Password error handling"
            )
            
            # Verify error response format
            if success and not response.get('success', True):
                print(f"   ✅ Gmail error handling test - Expected failure received")
                print(f"   Message: {response.get('message', 'No message')}")
                print(f"   Error type: {response.get('error_type', 'No error type')}")
                
                # Check for Gmail-specific guidance
                message = response.get('message', '').lower()
                if 'app password' in message and 'gmail' in message:
                    print(f"   ✅ Gmail-specific App Password guidance provided")
                    return True, response
                else:
                    print(f"   ❌ Gmail-specific guidance not found in message")
                    return False, response
            else:
                print(f"   ❌ Expected error response not received")
                return False, response
        
        return False, {}

    def test_smtp_error_handling_authentication_failed(self):
        """Test authentication failed error handling"""
        # Create config with wrong credentials
        auth_config_id = self.test_create_smtp_config(
            name="Auth Test - Wrong Credentials",
            provider="custom",
            email="testuser@example.com",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username="wrong_username@gmail.com",
            smtp_password="wrong_password",
            daily_limit=100
        )
        
        if auth_config_id:
            success, response = self.test_smtp_connection_test(
                auth_config_id,
                test_email="test@example.com",
                subject="Authentication Test",
                content="Testing authentication error handling"
            )
            
            # Verify error response format
            if success and not response.get('success', True):
                print(f"   ✅ Authentication error handling test - Expected failure received")
                print(f"   Message: {response.get('message', 'No message')}")
                print(f"   Error type: {response.get('error_type', 'No error type')}")
                
                # Check for authentication error guidance
                message = response.get('message', '').lower()
                error_type = response.get('error_type', '')
                if 'authentication' in message and error_type == 'authentication_failed':
                    print(f"   ✅ Authentication error properly categorized")
                    return True, response
                else:
                    print(f"   ❌ Authentication error not properly categorized")
                    return False, response
            else:
                print(f"   ❌ Expected error response not received")
                return False, response
        
        return False, {}

    def test_smtp_error_handling_connection_failed(self):
        """Test connection failed error handling"""
        # Create config with wrong server settings
        conn_config_id = self.test_create_smtp_config(
            name="Connection Test - Wrong Server",
            provider="custom",
            email="testuser@example.com",
            smtp_host="nonexistent.smtp.server.com",
            smtp_port=587,
            smtp_username="testuser@example.com",
            smtp_password="password123",
            daily_limit=100
        )
        
        if conn_config_id:
            success, response = self.test_smtp_connection_test(
                conn_config_id,
                test_email="test@example.com",
                subject="Connection Test",
                content="Testing connection error handling"
            )
            
            # Verify error response format
            if success and not response.get('success', True):
                print(f"   ✅ Connection error handling test - Expected failure received")
                print(f"   Message: {response.get('message', 'No message')}")
                print(f"   Error type: {response.get('error_type', 'No error type')}")
                
                # Check for connection error guidance
                message = response.get('message', '').lower()
                error_type = response.get('error_type', '')
                if 'connect' in message and error_type == 'connection_failed':
                    print(f"   ✅ Connection error properly categorized")
                    return True, response
                else:
                    print(f"   ❌ Connection error not properly categorized")
                    return False, response
            else:
                print(f"   ❌ Expected error response not received")
                return False, response
        
        return False, {}

    def test_smtp_error_handling_ssl_tls_error(self):
        """Test SSL/TLS error handling"""
        # Create config with wrong SSL/TLS settings
        ssl_config_id = self.test_create_smtp_config(
            name="SSL Test - Wrong Settings",
            provider="custom",
            email="testuser@example.com",
            smtp_host="smtp.gmail.com",
            smtp_port=465,  # SSL port
            smtp_username="testuser@gmail.com",
            smtp_password="password123",
            use_tls=True,  # Wrong - should use SSL for port 465
            daily_limit=100
        )
        
        if ssl_config_id:
            success, response = self.test_smtp_connection_test(
                ssl_config_id,
                test_email="test@example.com",
                subject="SSL/TLS Test",
                content="Testing SSL/TLS error handling"
            )
            
            # Verify error response format
            if success and not response.get('success', True):
                print(f"   ✅ SSL/TLS error handling test - Expected failure received")
                print(f"   Message: {response.get('message', 'No message')}")
                print(f"   Error type: {response.get('error_type', 'No error type')}")
                
                # Check for SSL/TLS error guidance
                message = response.get('message', '').lower()
                error_type = response.get('error_type', '')
                if ('ssl' in message or 'tls' in message) and error_type == 'ssl_tls_error':
                    print(f"   ✅ SSL/TLS error properly categorized")
                    return True, response
                else:
                    print(f"   ❌ SSL/TLS error not properly categorized")
                    return False, response
            else:
                print(f"   ❌ Expected error response not received")
                return False, response
        
        return False, {}

    def test_smtp_error_response_format(self):
        """Test that all SMTP error responses have the correct format"""
        print(f"\n🔍 Testing SMTP Error Response Format...")
        
        # Create a config that will definitely fail
        error_config_id = self.test_create_smtp_config(
            name="Format Test - Invalid Config",
            provider="custom",
            email="invalid@example.com",
            smtp_host="invalid.server.com",
            smtp_port=999,
            smtp_username="invalid@example.com",
            smtp_password="invalid_password",
            daily_limit=100
        )
        
        if error_config_id:
            success, response = self.test_smtp_connection_test(
                error_config_id,
                test_email="test@example.com",
                subject="Format Test",
                content="Testing error response format"
            )
            
            if success:
                # Check required fields in error response
                required_fields = ['success', 'message']
                optional_fields = ['error_type']
                
                all_fields_present = True
                for field in required_fields:
                    if field not in response:
                        print(f"   ❌ Missing required field: {field}")
                        all_fields_present = False
                    else:
                        print(f"   ✅ Required field present: {field}")
                
                for field in optional_fields:
                    if field in response:
                        print(f"   ✅ Optional field present: {field}")
                    else:
                        print(f"   ⚠️  Optional field missing: {field}")
                
                # Check that success is false for error cases
                if response.get('success') == False:
                    print(f"   ✅ Success field correctly set to false")
                else:
                    print(f"   ❌ Success field not set to false for error case")
                    all_fields_present = False
                
                # Check that message is not empty
                if response.get('message') and len(response.get('message', '').strip()) > 0:
                    print(f"   ✅ Error message is not empty")
                else:
                    print(f"   ❌ Error message is empty or missing")
                    all_fields_present = False
                
                return all_fields_present, response
            else:
                print(f"   ❌ Failed to get response for format test")
                return False, {}
        
        return False, {}

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
            200,
            auth_required=True
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
            data=contact_data,
            auth_required=True
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
            200,
            auth_required=True
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
            200,
            auth_required=True
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

    def test_csv_upload_comprehensive(self):
        """Comprehensive CSV upload functionality testing"""
        print(f"\n🔍 Testing CSV Upload Functionality Comprehensively...")
        
        # Test 1: Valid CSV with all fields
        print(f"\n   Test 1: Valid CSV with all fields")
        csv_content = """first_name,last_name,email,company,phone,tags
John,Doe,john.doe@example.com,Acme Corp,555-1234,lead,prospect
Jane,Smith,jane.smith@example.com,Tech Inc,555-5678,customer
Bob,Johnson,bob.johnson@example.com,StartupXYZ,555-9999,demo,trial"""

        files = {'file': ('test_contacts.csv', csv_content, 'text/csv')}
        success, response = self.run_test(
            "CSV Upload - Valid with all fields",
            "POST",
            "contacts/upload-csv",
            200,
            files=files,
            auth_required=True
        )
        
        if success:
            print(f"   ✅ Contacts created: {response.get('contacts_created', 0)}")
            print(f"   ✅ Contacts skipped: {response.get('contacts_skipped', 0)}")
            if response.get('errors'):
                print(f"   ⚠️  Errors: {response['errors']}")
        
        # Test 2: CSV with missing optional fields
        print(f"\n   Test 2: CSV with missing optional fields")
        csv_content2 = """first_name,last_name,email,company,phone,tags
Alice,Wonder,alice.wonder@example.com,,,
Charlie,Brown,charlie.brown@example.com,Peanuts Inc,,customer"""

        files2 = {'file': ('test_contacts2.csv', csv_content2, 'text/csv')}
        success2, response2 = self.run_test(
            "CSV Upload - Missing optional fields",
            "POST",
            "contacts/upload-csv",
            200,
            files=files2,
            auth_required=True
        )
        
        if success2:
            print(f"   ✅ Contacts created: {response2.get('contacts_created', 0)}")
            print(f"   ✅ Contacts skipped: {response2.get('contacts_skipped', 0)}")
        
        # Test 3: Empty CSV
        print(f"\n   Test 3: Empty CSV")
        csv_content3 = """first_name,last_name,email,company,phone,tags"""
        files3 = {'file': ('empty_contacts.csv', csv_content3, 'text/csv')}
        success3, response3 = self.run_test(
            "CSV Upload - Empty CSV",
            "POST",
            "contacts/upload-csv",
            200,
            files=files3,
            auth_required=True
        )
        
        if success3:
            print(f"   ✅ Contacts created: {response3.get('contacts_created', 0)}")
            print(f"   ✅ Contacts skipped: {response3.get('contacts_skipped', 0)}")
        
        # Test 4: CSV with invalid email formats
        print(f"\n   Test 4: CSV with invalid email formats")
        csv_content4 = """first_name,last_name,email,company,phone,tags
Valid,User,valid.user@example.com,Company A,,lead
Invalid,Email1,invalid-email,Company B,,prospect
Invalid,Email2,@invalid.com,Company C,,customer
Invalid,Email3,invalid@,Company D,,demo"""

        files4 = {'file': ('invalid_emails.csv', csv_content4, 'text/csv')}
        success4, response4 = self.run_test(
            "CSV Upload - Invalid email formats",
            "POST",
            "contacts/upload-csv",
            200,
            files=files4,
            auth_required=True
        )
        
        if success4:
            print(f"   ✅ Contacts created: {response4.get('contacts_created', 0)}")
            print(f"   ✅ Contacts skipped: {response4.get('contacts_skipped', 0)}")
            if response4.get('errors'):
                print(f"   ⚠️  Errors: {response4['errors']}")
        
        # Test 5: CSV with missing required fields
        print(f"\n   Test 5: CSV with missing required fields")
        csv_content5 = """first_name,last_name,email,company,phone,tags
,Missing,missing.first@example.com,Company A,,lead
Missing,,missing.last@example.com,Company B,,prospect
Missing,Both,,Company C,,customer"""

        files5 = {'file': ('missing_required.csv', csv_content5, 'text/csv')}
        success5, response5 = self.run_test(
            "CSV Upload - Missing required fields",
            "POST",
            "contacts/upload-csv",
            200,
            files=files5,
            auth_required=True
        )
        
        if success5:
            print(f"   ✅ Contacts created: {response5.get('contacts_created', 0)}")
            print(f"   ✅ Contacts skipped: {response5.get('contacts_skipped', 0)}")
            if response5.get('errors'):
                print(f"   ⚠️  Errors: {response5['errors']}")
        
        # Test 6: CSV with duplicate emails
        print(f"\n   Test 6: CSV with duplicate emails")
        csv_content6 = """first_name,last_name,email,company,phone,tags
First,Duplicate,duplicate@example.com,Company A,,lead
Second,Duplicate,duplicate@example.com,Company B,,prospect"""

        files6 = {'file': ('duplicates.csv', csv_content6, 'text/csv')}
        success6, response6 = self.run_test(
            "CSV Upload - Duplicate emails",
            "POST",
            "contacts/upload-csv",
            200,
            files=files6,
            auth_required=True
        )
        
        if success6:
            print(f"   ✅ Contacts created: {response6.get('contacts_created', 0)}")
            print(f"   ✅ Contacts skipped: {response6.get('contacts_skipped', 0)}")
        
        # Test 7: Verify contacts were actually created in database
        print(f"\n   Test 7: Verify contacts in database")
        success7, contacts_list = self.test_get_contacts()
        if success7:
            print(f"   ✅ Total contacts in database: {len(contacts_list)}")
            # Check for specific contacts we created
            created_emails = ['john.doe@example.com', 'jane.smith@example.com', 'alice.wonder@example.com']
            found_contacts = [c for c in contacts_list if c.get('email') in created_emails]
            print(f"   ✅ Found {len(found_contacts)} expected contacts from CSV uploads")
            
            for contact in found_contacts:
                print(f"     - {contact.get('first_name')} {contact.get('last_name')} ({contact.get('email')})")
        
        # Calculate overall success
        all_tests = [success, success2, success3, success4, success5, success6, success7]
        passed_tests = sum(all_tests)
        total_tests = len(all_tests)
        
        print(f"\n📊 CSV Upload Test Results: {passed_tests}/{total_tests} tests passed")
        
        return all(all_tests)

    def test_csv_upload(self):
        """Test basic CSV upload functionality (legacy method)"""
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
            files=files,
            auth_required=True
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
            files=files,
            auth_required=True
        )
        return success, response

    # Enhanced Campaign Testing Methods with A/B Testing and Variables
    def test_create_enhanced_campaign(self, name, steps, contact_ids=None, smtp_config_ids=None, description=None):
        """Create an enhanced campaign with A/B testing and variables"""
        campaign_data = {
            "name": name,
            "steps": steps,
            "contact_ids": contact_ids or [],
            "smtp_config_ids": smtp_config_ids or [],
            "daily_limit_per_inbox": 200,
            "delay_min_seconds": 300,
            "delay_max_seconds": 1800,
            "personalization_enabled": True,
            "a_b_testing_enabled": True,
            "timezone": "UTC"
        }
        if description:
            campaign_data["description"] = description

        success, response = self.run_test(
            f"Create Enhanced Campaign - {name}",
            "POST",
            "campaigns",
            200,
            data=campaign_data,
            auth_required=True
        )
        if success and 'id' in response:
            self.created_campaign_ids.append(response['id'])
            print(f"   Campaign created with {len(steps)} steps")
            for i, step in enumerate(steps):
                print(f"     Step {i+1}: {len(step.get('variations', []))} variations")
            return response['id']
        return None

    def test_create_campaign(self, name, subject, content, contact_ids=None, description=None):
        """Create a legacy campaign (for backward compatibility)"""
        # Convert to new format with single step and variation
        steps = [{
            "sequence_order": 1,
            "delay_days": 0,
            "variations": [{
                "name": "Default",
                "subject": subject,
                "content": content,
                "weight": 100
            }]
        }]
        
        return self.test_create_enhanced_campaign(name, steps, contact_ids, description=description)

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
            200,
            auth_required=True
        )
        if success:
            required_fields = ['total_contacts', 'total_campaigns', 'recent_contacts', 
                             'active_campaigns', 'total_emails_sent', 'overall_open_rate']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing field in enhanced stats: {field}")
                    return False, response
            print(f"   Enhanced Stats: {response}")
        return success, response

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

    def test_jwt_authentication_comprehensive(self):
        """Comprehensive JWT authentication testing to identify invalid token errors"""
        print(f"\n🔍 Testing JWT Authentication System Comprehensively...")
        
        # Test 1: Basic Authentication Flow
        print(f"\n   Test 1: Basic Authentication Flow")
        test_email = f"jwttest_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        test_password = "SecureJWTTest123!"
        test_name = "JWT Test User"
        
        # Register user
        success1, user_data = self.test_user_registration(test_email, test_password, test_name)
        if not success1:
            print(f"   ❌ User registration failed")
            return False
        
        # Login and get token
        success2, login_data = self.test_user_login(test_email, test_password)
        if not success2:
            print(f"   ❌ User login failed")
            return False
        
        original_token = self.auth_token
        print(f"   ✅ JWT token obtained: {original_token[:20]}...")
        
        # Test 2: Token Format Validation
        print(f"\n   Test 2: Token Format Validation")
        if original_token and len(original_token.split('.')) == 3:
            print(f"   ✅ JWT token has correct format (3 parts)")
        else:
            print(f"   ❌ JWT token format is invalid")
            return False
        
        # Test 3: Valid Token Access to Protected Endpoints
        print(f"\n   Test 3: Valid Token Access to Protected Endpoints")
        protected_endpoints = [
            ("auth/me", "GET"),
            ("contacts", "GET"),
            ("smtp-configs", "GET"),
            ("stats/dashboard", "GET"),
            ("subscription/plans", "GET")
        ]
        
        valid_token_tests = []
        for endpoint, method in protected_endpoints:
            success, response = self.run_test(
                f"Protected Access - {endpoint}",
                method,
                endpoint,
                200,
                auth_required=True
            )
            valid_token_tests.append(success)
            if not success:
                print(f"   ❌ Failed to access {endpoint} with valid token")
        
        if all(valid_token_tests):
            print(f"   ✅ All protected endpoints accessible with valid token")
        else:
            print(f"   ❌ Some protected endpoints failed with valid token")
        
        # Test 4: Invalid Token Tests
        print(f"\n   Test 4: Invalid Token Tests")
        
        # Save original token
        original_token = self.auth_token
        
        # Test 4a: Malformed token
        print(f"\n     Test 4a: Malformed Token")
        self.auth_token = "invalid.malformed.token"
        success4a, response4a = self.run_test(
            "Malformed Token Test",
            "GET",
            "auth/me",
            401,
            auth_required=True
        )
        if success4a:
            print(f"   ✅ Malformed token correctly rejected (401)")
            print(f"   Response: {response4a.get('detail', 'No detail')}")
        else:
            print(f"   ❌ Malformed token not properly rejected")
        
        # Test 4b: Empty token
        print(f"\n     Test 4b: Empty Token")
        self.auth_token = ""
        success4b, response4b = self.run_test(
            "Empty Token Test",
            "GET",
            "auth/me",
            401,
            auth_required=True
        )
        if success4b:
            print(f"   ✅ Empty token correctly rejected (401)")
            print(f"   Response: {response4b.get('detail', 'No detail')}")
        else:
            print(f"   ❌ Empty token not properly rejected")
        
        # Test 4c: Missing Bearer prefix
        print(f"\n     Test 4c: Missing Bearer Prefix")
        headers = {'Authorization': original_token}  # Missing "Bearer " prefix
        url = f"{self.api_url}/auth/me"
        try:
            response = requests.get(url, headers=headers)
            success4c = response.status_code == 401
            if success4c:
                print(f"   ✅ Missing Bearer prefix correctly rejected (401)")
                print(f"   Response: {response.json().get('detail', 'No detail') if response.text else 'No response'}")
            else:
                print(f"   ❌ Missing Bearer prefix not properly rejected (got {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error testing missing Bearer prefix: {str(e)}")
            success4c = False
        
        # Test 4d: Expired token simulation (modify token)
        print(f"\n     Test 4d: Invalid Token Signature")
        # Modify the last character of the token to simulate invalid signature
        if original_token:
            modified_token = original_token[:-1] + ('x' if original_token[-1] != 'x' else 'y')
            self.auth_token = modified_token
            success4d, response4d = self.run_test(
                "Invalid Signature Token Test",
                "GET",
                "auth/me",
                401,
                auth_required=True
            )
            if success4d:
                print(f"   ✅ Invalid signature token correctly rejected (401)")
                print(f"   Response: {response4d.get('detail', 'No detail')}")
            else:
                print(f"   ❌ Invalid signature token not properly rejected")
        else:
            success4d = False
        
        # Test 5: Authorization Header Variations
        print(f"\n   Test 5: Authorization Header Variations")
        
        # Test 5a: Case sensitivity
        print(f"\n     Test 5a: Case Sensitivity")
        headers_case = {'authorization': f'Bearer {original_token}'}  # lowercase
        url = f"{self.api_url}/auth/me"
        try:
            response = requests.get(url, headers=headers_case)
            success5a = response.status_code == 200
            if success5a:
                print(f"   ✅ Lowercase authorization header accepted")
            else:
                print(f"   ❌ Lowercase authorization header rejected (got {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error testing case sensitivity: {str(e)}")
            success5a = False
        
        # Test 5b: Extra spaces
        print(f"\n     Test 5b: Extra Spaces in Header")
        headers_spaces = {'Authorization': f'Bearer  {original_token}'}  # Extra space
        try:
            response = requests.get(url, headers=headers_spaces)
            success5b = response.status_code == 401  # Should be rejected
            if success5b:
                print(f"   ✅ Extra spaces in Bearer token correctly rejected")
            else:
                print(f"   ❌ Extra spaces in Bearer token not properly handled (got {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error testing extra spaces: {str(e)}")
            success5b = False
        
        # Restore original token
        self.auth_token = original_token
        
        # Test 6: Token Reuse and Persistence
        print(f"\n   Test 6: Token Reuse and Persistence")
        success6, response6 = self.run_test(
            "Token Reuse Test",
            "GET",
            "auth/me",
            200,
            auth_required=True
        )
        if success6:
            print(f"   ✅ Token can be reused successfully")
            print(f"   User: {response6.get('email', 'Unknown')}")
        else:
            print(f"   ❌ Token reuse failed")
        
        # Test 7: Multiple Protected Endpoint Access
        print(f"\n   Test 7: Multiple Protected Endpoint Access with Same Token")
        multi_access_tests = []
        for i, (endpoint, method) in enumerate(protected_endpoints[:3]):  # Test first 3
            success, response = self.run_test(
                f"Multi-Access Test {i+1} - {endpoint}",
                method,
                endpoint,
                200,
                auth_required=True
            )
            multi_access_tests.append(success)
        
        if all(multi_access_tests):
            print(f"   ✅ Token works consistently across multiple endpoints")
        else:
            print(f"   ❌ Token inconsistent across multiple endpoints")
        
        # Test 8: CSV Upload with Authentication
        print(f"\n   Test 8: CSV Upload with Authentication")
        csv_content = """first_name,last_name,email,company,phone,tags
JWT,Test,jwt.test@example.com,JWT Corp,555-0000,test"""
        files = {'file': ('jwt_test.csv', csv_content, 'text/csv')}
        success8, response8 = self.run_test(
            "CSV Upload with JWT",
            "POST",
            "contacts/upload-csv",
            200,
            files=files,
            auth_required=True
        )
        if success8:
            print(f"   ✅ CSV upload works with JWT authentication")
            print(f"   Contacts created: {response8.get('contacts_created', 0)}")
        else:
            print(f"   ❌ CSV upload failed with JWT authentication")
        
        # Test 9: SMTP Config with Authentication
        print(f"\n   Test 9: SMTP Config with Authentication")
        smtp_config_id = self.test_create_smtp_config(
            name="JWT Test SMTP",
            provider="gmail",
            email="jwttest@gmail.com",
            smtp_username="jwttest@gmail.com",
            smtp_password="test_password",
            daily_limit=100
        )
        success9 = smtp_config_id is not None
        if success9:
            print(f"   ✅ SMTP config creation works with JWT authentication")
        else:
            print(f"   ❌ SMTP config creation failed with JWT authentication")
        
        # Calculate overall success
        all_tests = [
            success1, success2, all(valid_token_tests), success4a, success4b, 
            success4c, success4d, success5a, success5b, success6, 
            all(multi_access_tests), success8, success9
        ]
        passed_tests = sum(all_tests)
        total_tests = len(all_tests)
        
        print(f"\n📊 JWT Authentication Test Results: {passed_tests}/{total_tests} tests passed")
        
        # Detailed results
        test_names = [
            "User Registration", "User Login", "Valid Token Access", "Malformed Token Rejection",
            "Empty Token Rejection", "Missing Bearer Rejection", "Invalid Signature Rejection",
            "Case Sensitivity", "Extra Spaces Handling", "Token Reuse", "Multi-Endpoint Access",
            "CSV Upload Auth", "SMTP Config Auth"
        ]
        
        print(f"\n🔍 Detailed JWT Test Results:")
        for i, (test_name, result) in enumerate(zip(test_names, all_tests)):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {i+1:2d}. {test_name}: {status}")
        
        return all(all_tests)

def main():
    print("🚀 Starting MailerPro API Tests - Focus on JWT Authentication System")
    print("=" * 70)
    print("🎯 Testing JWT authentication to identify 'invalid token' errors")
    print("=" * 70)
    
    tester = MailerProAPITester()
    
    try:
        # Test 1: Root endpoint
        if not tester.test_root_endpoint():
            print("❌ Root endpoint failed, stopping tests")
            return 1

        # JWT AUTHENTICATION TESTS - PRIMARY FOCUS
        print("\n" + "=" * 25 + " JWT AUTHENTICATION TESTS " + "=" * 25)
        
        # Comprehensive JWT testing
        jwt_success = tester.test_jwt_authentication_comprehensive()
        
        # Additional specific tests for common issues
        print("\n" + "=" * 25 + " ADDITIONAL AUTH TESTS " + "=" * 25)
        
        # Test token with different endpoints that users commonly access
        print(f"\n🔍 Testing Common User Endpoints...")
        
        # Create a fresh user for endpoint testing
        test_email = f"endpointtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        test_password = "EndpointTest123!"
        test_name = "Endpoint Test User"
        
        success_reg, _ = tester.test_user_registration(test_email, test_password, test_name)
        success_login, _ = tester.test_user_login(test_email, test_password)
        
        if success_reg and success_login:
            # Test dashboard stats (commonly accessed)
            success_dashboard = tester.test_dashboard_stats()
            
            # Test subscription plans (commonly accessed)
            success_plans, plans_response = tester.run_test(
                "Subscription Plans Access",
                "GET",
                "subscription/plans",
                200,
                auth_required=False  # This endpoint might not require auth
            )
            
            # Test current user info (commonly accessed)
            success_me, me_response = tester.test_get_current_user()
            
            print(f"   Dashboard Stats: {'✅ PASS' if success_dashboard else '❌ FAIL'}")
            print(f"   Subscription Plans: {'✅ PASS' if success_plans else '❌ FAIL'}")
            print(f"   Current User Info: {'✅ PASS' if success_me else '❌ FAIL'}")
            
            # Test with a real CSV upload scenario
            print(f"\n🔍 Testing Real-World CSV Upload Scenario...")
            csv_content = """first_name,last_name,email,company,phone,tags
Sarah,Johnson,sarah.johnson@company.com,Tech Solutions,555-1111,lead
Mike,Davis,mike.davis@startup.com,Innovation Labs,555-2222,prospect
Lisa,Wilson,lisa.wilson@enterprise.com,Big Corp,555-3333,customer"""
            
            files = {'file': ('real_test.csv', csv_content, 'text/csv')}
            success_csv, csv_response = tester.run_test(
                "Real CSV Upload Test",
                "POST",
                "contacts/upload-csv",
                200,
                files=files,
                auth_required=True
            )
            
            if success_csv:
                print(f"   ✅ Real CSV upload successful")
                print(f"   Contacts created: {csv_response.get('contacts_created', 0)}")
            else:
                print(f"   ❌ Real CSV upload failed")
            
            # Test SMTP config creation (commonly used)
            print(f"\n🔍 Testing Real-World SMTP Config Creation...")
            smtp_id = tester.test_create_smtp_config(
                name="Production Gmail",
                provider="gmail",
                email="user@gmail.com",
                smtp_username="user@gmail.com",
                smtp_password="app_password_here",
                daily_limit=300
            )
            
            if smtp_id:
                print(f"   ✅ SMTP config creation successful")
                
                # Test SMTP config retrieval
                success_smtp_get, smtp_response = tester.test_get_single_smtp_config(smtp_id)
                print(f"   SMTP Config Retrieval: {'✅ PASS' if success_smtp_get else '❌ FAIL'}")
                
                # Test SMTP stats
                success_stats, stats_response = tester.test_smtp_config_stats(smtp_id)
                print(f"   SMTP Stats Access: {'✅ PASS' if success_stats else '❌ FAIL'}")
            else:
                print(f"   ❌ SMTP config creation failed")

        # Print final results
        print("\n" + "=" * 70)
        print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
        
        # JWT-specific results
        print("\n🎯 JWT Authentication Test Summary:")
        print(f"   Comprehensive JWT Tests: {'✅ PASS' if jwt_success else '❌ FAIL'}")
        
        if jwt_success:
            print("\n✅ JWT Authentication System Analysis:")
            print("   • User registration and login working correctly")
            print("   • JWT tokens are properly formatted and validated")
            print("   • Protected endpoints correctly require authentication")
            print("   • Invalid tokens are properly rejected with 401 status")
            print("   • Authorization header format is correctly enforced")
            print("   • Token reuse and persistence working correctly")
            print("   • CSV upload authentication working")
            print("   • SMTP configuration authentication working")
            print("\n🔍 No 'invalid token' errors found in the authentication system!")
            print("   The JWT implementation appears to be working correctly.")
        else:
            print("\n❌ JWT Authentication Issues Found:")
            print("   • Some authentication tests failed")
            print("   • This may be the source of 'invalid token' errors")
            print("   • Check the detailed test results above for specific failures")
        
        if tester.tests_passed == tester.tests_run and jwt_success:
            print("\n🎉 All tests passed! JWT authentication system is working correctly.")
            print("   If users are still getting 'invalid token' errors, the issue may be:")
            print("   • Frontend not sending tokens correctly")
            print("   • Token storage issues in browser")
            print("   • Network/proxy issues modifying headers")
            print("   • Race conditions in token usage")
            result = 0
        else:
            print("\n❌ Some tests failed - JWT authentication system needs attention")
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