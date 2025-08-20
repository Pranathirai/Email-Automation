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

def main():
    print("🚀 Starting MailerPro API Tests - Focus on CSV Contact Import Functionality")
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
        test_email = f"csvtester_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        test_password = "SecurePassword123!"
        test_name = "CSV Test User"
        
        success, user_data = tester.test_user_registration(test_email, test_password, test_name)
        if not success:
            print("❌ User registration failed, stopping tests")
            return 1

        # Test 3: User Login
        success, login_data = tester.test_user_login(test_email, test_password)
        if not success:
            print("❌ User login failed, stopping tests")
            return 1

        # Test 4: Get current user info and check subscription limits
        success, user_info = tester.test_get_current_user()
        if success:
            plan = user_info.get('subscription_plan', 'free')
            print(f"   Current subscription plan: {plan}")

        # Check initial contact count
        print("\n" + "=" * 25 + " INITIAL STATE CHECK " + "=" * 25)
        success, initial_contacts = tester.test_get_contacts()
        initial_count = len(initial_contacts) if success else 0
        print(f"   Initial contact count: {initial_count}")

        # CSV IMPORT TESTS - PRIMARY FOCUS
        print("\n" + "=" * 25 + " CSV CONTACT IMPORT TESTS " + "=" * 25)
        
        # Test 5: Comprehensive CSV Upload Testing
        csv_success = tester.test_csv_upload_comprehensive()
        
        # Test 6: Invalid CSV file format (should fail)
        print(f"\n🔍 Testing Invalid CSV File Format...")
        success6, response6 = tester.test_invalid_csv_upload()
        
        # Test 7: Verify final contact count after all CSV imports
        print(f"\n🔍 Verifying Final Contact Count...")
        success7, final_contacts = tester.test_get_contacts()
        final_count = len(final_contacts) if success7 else 0
        contacts_added = final_count - initial_count
        print(f"   Final contact count: {final_count}")
        print(f"   Contacts added via CSV: {contacts_added}")
        
        # Test 8: Search functionality with imported contacts
        print(f"\n🔍 Testing Search with Imported Contacts...")
        search_terms = ['john', 'jane', 'acme', 'tech']
        search_results = {}
        for term in search_terms:
            success_search, results = tester.test_get_contacts_with_search(term)
            if success_search:
                search_results[term] = len(results)
                print(f"   Search '{term}': {len(results)} results")
        
        # Test 9: Dashboard stats after CSV import
        print(f"\n🔍 Testing Dashboard Stats After CSV Import...")
        success9, stats = tester.test_enhanced_dashboard_stats()
        if success9:
            print(f"   Total contacts in stats: {stats.get('total_contacts', 0)}")
            print(f"   Recent contacts: {stats.get('recent_contacts', 0)}")

        # Test 10: Subscription limits check
        print(f"\n🔍 Testing Subscription Limits...")
        success10, user_info = tester.test_get_current_user()
        if success10:
            plan = user_info.get('subscription_plan', 'free')
            print(f"   Current plan: {plan}")
            
            # Check if we're approaching limits
            if success9:
                total_contacts = stats.get('total_contacts', 0)
                subscription_info = stats.get('subscription', {})
                limits = subscription_info.get('limits', {})
                contact_limit = limits.get('contacts', {}).get('limit', 100)
                print(f"   Contact usage: {total_contacts}/{contact_limit}")
                
                if total_contacts >= contact_limit * 0.8:  # 80% of limit
                    print(f"   ⚠️  Approaching contact limit!")

        # Print final results
        print("\n" + "=" * 70)
        print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
        
        # Specific results for CSV import tests
        print("\n🎯 CSV Import Test Results:")
        print(f"   Comprehensive CSV Upload: {'✅ PASS' if csv_success else '❌ FAIL'}")
        print(f"   Invalid CSV Rejection: {'✅ PASS' if success6 else '❌ FAIL'}")
        print(f"   Contact Count Verification: {'✅ PASS' if success7 else '❌ FAIL'}")
        print(f"   Search Functionality: {'✅ PASS' if all(search_results.values()) else '❌ FAIL'}")
        print(f"   Dashboard Stats Update: {'✅ PASS' if success9 else '❌ FAIL'}")
        
        csv_tests_passed = sum([csv_success, success6, success7, bool(search_results), success9])
        print(f"\n📊 CSV Import Tests: {csv_tests_passed}/5 passed")
        
        # Summary of contacts imported
        if contacts_added > 0:
            print(f"\n✅ Successfully imported {contacts_added} contacts via CSV")
            print(f"   Final database contains {final_count} total contacts")
        else:
            print(f"\n❌ No contacts were imported via CSV - this indicates an issue!")
        
        if tester.tests_passed == tester.tests_run and csv_success:
            print("🎉 All tests passed! CSV import functionality is working correctly.")
            result = 0
        else:
            print("❌ Some tests failed - CSV import functionality needs attention")
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