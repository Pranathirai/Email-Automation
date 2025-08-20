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

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'} if not files else {}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files)
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
    print("🚀 Starting MailerPro API Tests")
    print("=" * 50)
    
    tester = MailerProAPITester()
    
    try:
        # Test 1: Root endpoint
        if not tester.test_root_endpoint():
            print("❌ Root endpoint failed, stopping tests")
            return 1

        # Test 2: Dashboard stats
        if not tester.test_dashboard_stats():
            print("❌ Dashboard stats failed")

        # Test 3: Create contacts
        contact1_id = tester.test_create_contact(
            "Alice", "Johnson", "alice.johnson@test.com", 
            "Test Corp", "555-0001", ["lead", "priority"]
        )
        
        contact2_id = tester.test_create_contact(
            "Bob", "Wilson", "bob.wilson@test.com",
            "Demo Inc", "555-0002", ["demo"]
        )

        contact3_id = tester.test_create_contact(
            "Charlie", "Brown", "charlie.brown@test.com"
        )

        # Test 4: Duplicate contact (should fail)
        if contact1_id:
            tester.test_create_duplicate_contact("alice.johnson@test.com")

        # Test 5: Get all contacts
        success, contacts = tester.test_get_contacts()
        if not success:
            print("❌ Get contacts failed")

        # Test 6: Search contacts
        tester.test_get_contacts_with_search("Alice")
        tester.test_get_contacts_with_search("Test Corp")

        # Test 7: Get single contact
        if contact1_id:
            tester.test_get_single_contact(contact1_id)

        # Test 8: Update contact
        if contact1_id:
            tester.test_update_contact(contact1_id, {
                "company": "Updated Corp",
                "tags": ["updated", "priority"]
            })

        # Test 9: CSV upload
        tester.test_csv_upload()

        # Test 10: Invalid CSV upload
        tester.test_invalid_csv_upload()

        # Test 11: Delete contact
        if contact3_id:
            tester.test_delete_contact(contact3_id)
            # Remove from cleanup list since we deleted it
            if contact3_id in tester.created_contact_ids:
                tester.created_contact_ids.remove(contact3_id)

        # Campaign Tests
        print("\n" + "=" * 30 + " CAMPAIGN TESTS " + "=" * 30)
        
        # Test 12: Enhanced dashboard stats (with new fields)
        tester.test_enhanced_dashboard_stats()

        # Test 13: Create campaigns
        campaign1_id = tester.test_create_campaign(
            "Product Launch Campaign",
            "Exciting news about {{company}} - {{first_name}}!",
            "Hi {{first_name}},\n\nI hope this email finds you well at {{company}}.\n\nBest regards,\nTeam",
            contact_ids=[contact1_id, contact2_id] if contact1_id and contact2_id else [],
            description="Test campaign for product launch"
        )

        campaign2_id = tester.test_create_campaign(
            "Follow-up Campaign",
            "Quick follow-up for {{full_name}}",
            "Hello {{full_name}},\n\nJust following up on our previous conversation.\n\nThanks!"
        )

        # Test 14: Get all campaigns
        success, campaigns = tester.test_get_campaigns()
        if not success:
            print("❌ Get campaigns failed")

        # Test 15: Get single campaign
        if campaign1_id:
            tester.test_get_single_campaign(campaign1_id)

        # Test 16: Update campaign
        if campaign1_id:
            tester.test_update_campaign(campaign1_id, {
                "name": "Updated Product Launch Campaign",
                "description": "Updated description for the campaign",
                "daily_limit": 100
            })

        # Test 17: Campaign preview with personalization
        if campaign1_id and contact1_id:
            tester.test_campaign_preview(campaign1_id, contact1_id)

        # Test 18: Campaign analytics
        if campaign1_id:
            tester.test_campaign_analytics(campaign1_id)

        # Test 19: Delete campaign
        if campaign2_id:
            tester.test_delete_campaign(campaign2_id)
            # Remove from cleanup list since we deleted it
            if campaign2_id in tester.created_campaign_ids:
                tester.created_campaign_ids.remove(campaign2_id)

        # Print final results
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
        
        if tester.tests_passed == tester.tests_run:
            print("🎉 All tests passed!")
            result = 0
        else:
            print("❌ Some tests failed")
            result = 1

    except Exception as e:
        print(f"❌ Unexpected error during testing: {str(e)}")
        result = 1
    
    finally:
        # Cleanup
        tester.cleanup_created_campaigns()
        tester.cleanup_created_contacts()
    
    return result

if __name__ == "__main__":
    sys.exit(main())