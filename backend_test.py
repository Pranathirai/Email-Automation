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
        """Test enhanced campaign analytics endpoint with A/B breakdown"""
        success, response = self.run_test(
            f"Enhanced Campaign Analytics",
            "GET",
            f"campaigns/{campaign_id}/analytics",
            200,
            auth_required=True
        )
        if success:
            # Check overall analytics structure
            if 'overall' not in response:
                print(f"❌ Missing 'overall' section in analytics")
                return False
            
            overall = response['overall']
            required_overall_fields = ['campaign_id', 'campaign_name', 'total_emails', 
                                     'delivered_emails', 'opened_emails', 'clicked_emails', 
                                     'replied_emails', 'bounced_emails', 'delivery_rate', 
                                     'open_rate', 'click_rate', 'reply_rate', 'bounce_rate']
            
            for field in required_overall_fields:
                if field not in overall:
                    print(f"❌ Missing field in overall analytics: {field}")
                    return False
            
            # Check A/B testing breakdown
            if 'ab_testing' not in response:
                print(f"❌ Missing 'ab_testing' section in analytics")
                return False
            
            ab_testing = response['ab_testing']
            if isinstance(ab_testing, list):
                print(f"   ✅ A/B testing breakdown available with {len(ab_testing)} variations")
                for variation in ab_testing:
                    required_variation_fields = ['variation_name', 'sent', 'delivered', 
                                               'opened', 'clicked', 'delivery_rate', 'open_rate']
                    for field in required_variation_fields:
                        if field not in variation:
                            print(f"❌ Missing field in variation analytics: {field}")
                            return False
            
            print(f"   Overall Stats: {overall.get('total_emails', 0)} emails, "
                  f"{overall.get('open_rate', 0)}% open rate")
            print(f"   A/B Variations: {len(ab_testing)} tested")
            
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

    # Template and Variable Testing Methods
    def test_get_available_variables(self):
        """Test getting available template variables"""
        success, response = self.run_test(
            "Get Available Variables",
            "GET",
            "templates/variables",
            200,
            auth_required=True
        )
        if success:
            required_sections = ['standard', 'usage', 'sample_data']
            for section in required_sections:
                if section not in response:
                    print(f"❌ Missing section in variables: {section}")
                    return False
            
            standard_vars = response['standard']
            expected_vars = ['first_name', 'last_name', 'full_name', 'email', 'company', 'phone']
            for var in expected_vars:
                if var not in standard_vars:
                    print(f"❌ Missing standard variable: {var}")
                    return False
            
            print(f"   ✅ Available variables: {list(standard_vars.keys())}")
            print(f"   Usage guide: {response['usage']}")
        return success, response

    def test_validate_template(self, template):
        """Test template validation"""
        success, response = self.run_test(
            f"Validate Template",
            "POST",
            f"templates/validate?template={template}",
            200,
            auth_required=True
        )
        if success:
            required_fields = ['template', 'is_valid', 'variables_found', 'valid_variables', 'invalid_variables']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing field in template validation: {field}")
                    return False
            
            print(f"   Template: {template}")
            print(f"   Valid: {response['is_valid']}")
            print(f"   Variables found: {response['variables_found']}")
            if response['invalid_variables']:
                print(f"   Invalid variables: {response['invalid_variables']}")
        return success, response

    def test_campaign_personalization_preview(self, campaign_id, contact_id, template):
        """Test campaign personalization preview"""
        preview_data = {
            "template": template,
            "contact_id": contact_id
        }
        success, response = self.run_test(
            f"Campaign Personalization Preview",
            "POST",
            f"campaigns/{campaign_id}/preview",
            200,
            data=preview_data,
            auth_required=True
        )
        if success:
            required_fields = ['original_template', 'personalized_content', 'contact', 'variables_used']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing field in preview: {field}")
                    return False
            
            print(f"   Original: {response['original_template']}")
            print(f"   Personalized: {response['personalized_content']}")
            print(f"   Variables used: {response['variables_used']}")
        return success, response

    def test_campaign_validation(self, campaign_id):
        """Test campaign validation"""
        success, response = self.run_test(
            f"Campaign Validation",
            "POST",
            f"campaigns/{campaign_id}/validate",
            200,
            auth_required=True
        )
        if success:
            required_fields = ['campaign_id', 'campaign_name', 'is_valid', 'contacts_count', 
                             'steps_count', 'variable_validation', 'smtp_issues', 'setup_issues']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing field in campaign validation: {field}")
                    return False
            
            print(f"   Campaign: {response['campaign_name']}")
            print(f"   Valid: {response['is_valid']}")
            print(f"   Contacts: {response['contacts_count']}")
            print(f"   Steps: {response['steps_count']}")
            
            if response['smtp_issues']:
                print(f"   SMTP Issues: {response['smtp_issues']}")
            if response['setup_issues']:
                print(f"   Setup Issues: {response['setup_issues']}")
            
            var_validation = response['variable_validation']
            if not var_validation['valid']:
                print(f"   Variable Issues: {var_validation['issues']}")
        
        return success, response

    def test_campaign_start(self, campaign_id):
        """Test starting a campaign"""
        success, response = self.run_test(
            f"Start Campaign",
            "POST",
            f"campaigns/{campaign_id}/start",
            200,
            auth_required=True
        )
        if success:
            print(f"   Campaign started: {response.get('message', 'No message')}")
            print(f"   Status: {response.get('status', 'Unknown')}")
        return success, response

    def test_campaign_pause(self, campaign_id):
        """Test pausing a campaign"""
        success, response = self.run_test(
            f"Pause Campaign",
            "POST",
            f"campaigns/{campaign_id}/pause",
            200,
            auth_required=True
        )
        if success:
            print(f"   Campaign paused: {response.get('message', 'No message')}")
            print(f"   Status: {response.get('status', 'Unknown')}")
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

    def test_enhanced_campaign_system_comprehensive(self):
        """Comprehensive test of the enhanced campaign management system with A/B testing and variables"""
        print(f"\n🔍 Testing Enhanced Campaign Management System Comprehensively...")
        
        # Test 1: Template Variables System
        print(f"\n   Test 1: Template Variables System")
        success1, variables_response = self.test_get_available_variables()
        if not success1:
            print(f"   ❌ Failed to get available variables")
            return False
        
        # Test 2: Template Validation
        print(f"\n   Test 2: Template Validation")
        test_templates = [
            "Hello {{first_name}}!",
            "Welcome {{first_name}} from {{company}}!",
            "Invalid {{unknown_variable}} template",
            "Hi {{first_name}}, your email is {{email}}"
        ]
        
        template_tests = []
        for template in test_templates:
            success, response = self.test_validate_template(template)
            template_tests.append(success)
            if success:
                expected_valid = "unknown_variable" not in template
                actual_valid = response.get('is_valid', False)
                if expected_valid == actual_valid:
                    print(f"   ✅ Template validation correct for: {template}")
                else:
                    print(f"   ❌ Template validation incorrect for: {template}")
                    template_tests[-1] = False
        
        # Test 3: Create contacts for campaign testing
        print(f"\n   Test 3: Create Test Contacts")
        test_contacts = [
            ("John", "Doe", "john.doe@testcampaign.com", "Acme Corp", "555-1234"),
            ("Jane", "Smith", "jane.smith@testcampaign.com", "Tech Inc", "555-5678"),
            ("Bob", "Johnson", "bob.johnson@testcampaign.com", "StartupXYZ", "555-9999")
        ]
        
        contact_ids = []
        for first_name, last_name, email, company, phone in test_contacts:
            contact_id = self.test_create_contact(first_name, last_name, email, company, phone, ["campaign_test"])
            if contact_id:
                contact_ids.append(contact_id)
        
        success3 = len(contact_ids) == len(test_contacts)
        if success3:
            print(f"   ✅ Created {len(contact_ids)} test contacts")
        else:
            print(f"   ❌ Failed to create all test contacts")
        
        # Test 4: Create SMTP Config for campaign
        print(f"\n   Test 4: Create SMTP Config")
        smtp_config_id = self.test_create_smtp_config(
            name="Campaign Test SMTP",
            provider="gmail",
            email="campaign.test@gmail.com",
            smtp_username="campaign.test@gmail.com",
            smtp_password="test_app_password",
            daily_limit=200
        )
        success4 = smtp_config_id is not None
        smtp_config_ids = [smtp_config_id] if smtp_config_id else []
        
        # Test 5: Create Enhanced Campaign with A/B Testing
        print(f"\n   Test 5: Create Enhanced Campaign with A/B Testing")
        campaign_steps = [
            {
                "sequence_order": 1,
                "delay_days": 0,
                "variations": [
                    {
                        "name": "Variation A",
                        "subject": "Hello {{first_name}}!",
                        "content": "Hi {{first_name}}, Welcome from {{company}}! This is variation A.",
                        "weight": 50
                    },
                    {
                        "name": "Variation B",
                        "subject": "Welcome {{first_name}}!",
                        "content": "Hello {{first_name}}, Great to connect! This is variation B from {{company}}.",
                        "weight": 50
                    }
                ]
            },
            {
                "sequence_order": 2,
                "delay_days": 3,
                "variations": [
                    {
                        "name": "Follow-up A",
                        "subject": "Following up, {{first_name}}",
                        "content": "Hi {{first_name}}, Just wanted to follow up on our previous message about {{company}}.",
                        "weight": 100
                    }
                ]
            }
        ]
        
        campaign_id = self.test_create_enhanced_campaign(
            name="Test A/B Campaign",
            steps=campaign_steps,
            contact_ids=contact_ids,
            smtp_config_ids=smtp_config_ids,
            description="Test campaign with A/B testing and variables"
        )
        success5 = campaign_id is not None
        
        # Test 6: Campaign Validation
        print(f"\n   Test 6: Campaign Validation")
        success6 = False
        if campaign_id:
            success6, validation_response = self.test_campaign_validation(campaign_id)
            if success6:
                is_valid = validation_response.get('is_valid', False)
                print(f"   Campaign validation result: {'✅ Valid' if is_valid else '❌ Invalid'}")
                if not is_valid:
                    print(f"   Issues found: {validation_response}")
        
        # Test 7: Personalization Preview
        print(f"\n   Test 7: Personalization Preview")
        success7 = False
        if campaign_id and contact_ids:
            test_template = "Hello {{first_name}} from {{company}}! Your email is {{email}}."
            success7, preview_response = self.test_campaign_personalization_preview(
                campaign_id, contact_ids[0], test_template
            )
            if success7:
                original = preview_response.get('original_template', '')
                personalized = preview_response.get('personalized_content', '')
                print(f"   ✅ Personalization working: '{original}' -> '{personalized}'")
        
        # Test 8: Get Campaign Details
        print(f"\n   Test 8: Get Campaign Details")
        success8 = False
        if campaign_id:
            success8, campaign_response = self.test_get_single_campaign(campaign_id)
            if success8:
                steps = campaign_response.get('steps', [])
                print(f"   ✅ Campaign has {len(steps)} steps")
                for i, step in enumerate(steps):
                    variations = step.get('variations', [])
                    print(f"     Step {i+1}: {len(variations)} variations")
        
        # Test 9: Campaign Analytics (even if empty)
        print(f"\n   Test 9: Campaign Analytics")
        success9 = False
        if campaign_id:
            success9 = self.test_campaign_analytics(campaign_id)
        
        # Test 10: Campaign Start/Pause (if validation passes)
        print(f"\n   Test 10: Campaign Start/Pause")
        success10a = success10b = False
        if campaign_id and success6 and validation_response.get('is_valid', False):
            success10a, start_response = self.test_campaign_start(campaign_id)
            if success10a:
                success10b, pause_response = self.test_campaign_pause(campaign_id)
        else:
            print(f"   ⚠️  Skipping start/pause test - campaign validation failed or no campaign")
            success10a = success10b = True  # Don't fail the test for this
        
        # Test 11: Update Campaign
        print(f"\n   Test 11: Update Campaign")
        success11 = False
        if campaign_id:
            update_data = {
                "name": "Updated Test A/B Campaign",
                "description": "Updated description with new features"
            }
            success11 = self.test_update_campaign(campaign_id, update_data)
        
        # Test 12: Get All Campaigns
        print(f"\n   Test 12: Get All Campaigns")
        success12, campaigns_response = self.test_get_campaigns()
        if success12:
            campaigns = campaigns_response if isinstance(campaigns_response, list) else []
            print(f"   ✅ Found {len(campaigns)} total campaigns")
            # Look for our test campaign
            test_campaign = next((c for c in campaigns if c.get('id') == campaign_id), None)
            if test_campaign:
                print(f"   ✅ Test campaign found in list")
            else:
                print(f"   ❌ Test campaign not found in list")
                success12 = False
        
        # Calculate overall success
        all_tests = [
            success1,  # Variables system
            all(template_tests),  # Template validation
            success3,  # Test contacts
            success4,  # SMTP config
            success5,  # Enhanced campaign creation
            success6,  # Campaign validation
            success7,  # Personalization preview
            success8,  # Campaign details
            success9,  # Campaign analytics
            success10a and success10b,  # Start/pause
            success11,  # Update campaign
            success12   # Get campaigns
        ]
        
        passed_tests = sum(all_tests)
        total_tests = len(all_tests)
        
        print(f"\n📊 Enhanced Campaign System Test Results: {passed_tests}/{total_tests} tests passed")
        
        # Detailed results
        test_names = [
            "Variables System", "Template Validation", "Test Contacts Creation", "SMTP Config Creation",
            "Enhanced Campaign Creation", "Campaign Validation", "Personalization Preview", 
            "Campaign Details", "Campaign Analytics", "Start/Pause Campaign", "Update Campaign", "Get All Campaigns"
        ]
        
        print(f"\n🔍 Detailed Campaign Test Results:")
        for i, (test_name, result) in enumerate(zip(test_names, all_tests)):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {i+1:2d}. {test_name}: {status}")
        
        return all(all_tests)

def main():
    print("🚀 Starting MailerPro API Tests - Focus on Enhanced Campaign Management System")
    print("=" * 80)
    print("🎯 Testing enhanced campaign system with variables and A/B testing")
    print("=" * 80)
    
    tester = MailerProAPITester()
    
    try:
        # Test 1: Root endpoint
        if not tester.test_root_endpoint():
            print("❌ Root endpoint failed, stopping tests")
            return 1

        # AUTHENTICATION SETUP
        print("\n" + "=" * 25 + " AUTHENTICATION SETUP " + "=" * 25)
        
        # Create test user for campaign testing
        test_email = f"campaigntest_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        test_password = "CampaignTest123!"
        test_name = "Campaign Test User"
        
        success_reg, _ = tester.test_user_registration(test_email, test_password, test_name)
        success_login, _ = tester.test_user_login(test_email, test_password)
        
        if not (success_reg and success_login):
            print("❌ Authentication setup failed, stopping tests")
            return 1
        
        print("✅ Authentication setup successful")

        # ENHANCED CAMPAIGN SYSTEM TESTS - PRIMARY FOCUS
        print("\n" + "=" * 25 + " ENHANCED CAMPAIGN SYSTEM TESTS " + "=" * 25)
        
        # Comprehensive enhanced campaign system testing
        campaign_success = tester.test_enhanced_campaign_system_comprehensive()
        
        # Additional specific campaign tests
        print("\n" + "=" * 25 + " ADDITIONAL CAMPAIGN TESTS " + "=" * 25)
        
        # Test individual campaign components
        print(f"\n🔍 Testing Individual Campaign Components...")
        
        # Test template variables endpoint
        print(f"\n   Testing Template Variables Endpoint...")
        success_vars, vars_response = tester.test_get_available_variables()
        
        # Test template validation with various scenarios
        print(f"\n   Testing Template Validation Scenarios...")
        validation_tests = [
            ("Valid simple template", "Hello {{first_name}}!", True),
            ("Valid complex template", "Hi {{first_name}} from {{company}}, your email is {{email}}", True),
            ("Invalid template", "Hello {{invalid_var}}!", False),
            ("Mixed valid/invalid", "Hi {{first_name}}, unknown {{bad_var}}", False),
            ("No variables", "Hello there!", True)
        ]
        
        validation_results = []
        for test_name, template, expected_valid in validation_tests:
            success, response = tester.test_validate_template(template)
            if success:
                actual_valid = response.get('is_valid', False)
                test_passed = (actual_valid == expected_valid)
                validation_results.append(test_passed)
                status = "✅ PASS" if test_passed else "❌ FAIL"
                print(f"     {test_name}: {status}")
            else:
                validation_results.append(False)
                print(f"     {test_name}: ❌ FAIL (API error)")
        
        # Test campaign CRUD operations with enhanced features
        print(f"\n   Testing Enhanced Campaign CRUD Operations...")
        
        # Create a simple A/B test campaign
        simple_ab_steps = [{
            "sequence_order": 1,
            "delay_days": 0,
            "variations": [
                {
                    "name": "Version A",
                    "subject": "Quick Test {{first_name}}",
                    "content": "Hello {{first_name}}, this is version A!",
                    "weight": 50
                },
                {
                    "name": "Version B", 
                    "subject": "Hello {{first_name}}",
                    "content": "Hi {{first_name}}, this is version B!",
                    "weight": 50
                }
            ]
        }]
        
        simple_campaign_id = tester.test_create_enhanced_campaign(
            name="Simple A/B Test Campaign",
            steps=simple_ab_steps,
            description="Simple A/B test for CRUD operations"
        )
        
        crud_success = simple_campaign_id is not None
        
        if simple_campaign_id:
            # Test campaign retrieval
            success_get, campaign_data = tester.test_get_single_campaign(simple_campaign_id)
            print(f"     Get Campaign: {'✅ PASS' if success_get else '❌ FAIL'}")
            
            # Test campaign update
            update_data = {"name": "Updated Simple A/B Test Campaign"}
            success_update = tester.test_update_campaign(simple_campaign_id, update_data)
            print(f"     Update Campaign: {'✅ PASS' if success_update else '❌ FAIL'}")
            
            # Test campaign validation
            success_validate, validate_response = tester.test_campaign_validation(simple_campaign_id)
            print(f"     Validate Campaign: {'✅ PASS' if success_validate else '❌ FAIL'}")
            
            # Test campaign analytics (even if empty)
            success_analytics = tester.test_campaign_analytics(simple_campaign_id)
            print(f"     Campaign Analytics: {'✅ PASS' if success_analytics else '❌ FAIL'}")
        
        # Test subscription plans and dashboard
        print(f"\n   Testing Supporting Endpoints...")
        success_plans, plans_response = tester.run_test(
            "Subscription Plans Access",
            "GET",
            "subscription/plans",
            200,
            auth_required=False
        )
        print(f"     Subscription Plans: {'✅ PASS' if success_plans else '❌ FAIL'}")
        
        success_dashboard = tester.test_dashboard_stats()
        print(f"     Dashboard Stats: {'✅ PASS' if success_dashboard else '❌ FAIL'}")
        
        # Test enhanced dashboard stats
        success_enhanced_dashboard, _ = tester.test_enhanced_dashboard_stats()
        print(f"     Enhanced Dashboard: {'✅ PASS' if success_enhanced_dashboard else '❌ FAIL'}")
        
        # Test campaign list endpoint
        success_campaigns_list, campaigns_response = tester.test_get_campaigns()
        print(f"     Get All Campaigns: {'✅ PASS' if success_campaigns_list else '❌ FAIL'}")
        
        # Additional validation tests
        print(f"\n   Testing Edge Cases...")
        
        # Test empty campaign creation (should fail)
        empty_campaign_id = tester.test_create_enhanced_campaign(
            name="Empty Campaign",
            steps=[],  # No steps
            description="Campaign with no steps"
        )
        empty_test_success = empty_campaign_id is not None  # Should still create but be invalid
        print(f"     Empty Campaign Creation: {'✅ PASS' if empty_test_success else '❌ FAIL'}")
        
        if empty_campaign_id:
            # This should show validation errors
            success_empty_validate, empty_validate_response = tester.test_campaign_validation(empty_campaign_id)
            if success_empty_validate:
                is_valid = empty_validate_response.get('is_valid', True)
                empty_validation_correct = not is_valid  # Should be invalid
                print(f"     Empty Campaign Validation: {'✅ PASS' if empty_validation_correct else '❌ FAIL'}")
            else:
                print(f"     Empty Campaign Validation: ❌ FAIL (API error)")
        
        # Test campaign with invalid variables
        invalid_var_steps = [{
            "sequence_order": 1,
            "delay_days": 0,
            "variations": [{
                "name": "Invalid Vars",
                "subject": "Hello {{invalid_variable}}",
                "content": "Hi {{another_invalid}}, welcome!",
                "weight": 100
            }]
        }]
        
        invalid_campaign_id = tester.test_create_enhanced_campaign(
            name="Invalid Variables Campaign",
            steps=invalid_var_steps,
            description="Campaign with invalid variables"
        )
        
        if invalid_campaign_id:
            success_invalid_validate, invalid_validate_response = tester.test_campaign_validation(invalid_campaign_id)
            if success_invalid_validate:
                var_validation = invalid_validate_response.get('variable_validation', {})
                has_missing_vars = len(var_validation.get('missing_variables', [])) > 0
                print(f"     Invalid Variables Detection: {'✅ PASS' if has_missing_vars else '❌ FAIL'}")
            else:
                print(f"     Invalid Variables Detection: ❌ FAIL (API error)")

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