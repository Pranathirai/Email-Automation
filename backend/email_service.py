import asyncio
import aiosmtplib
import logging
import json
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Any
import random
import uuid

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailProvider:
    """Base class for email providers"""
    
    def __init__(self, config: dict):
        self.config = config
        self.name = config.get('name', 'Unknown')
        self.provider = config.get('provider', 'custom')
        self.daily_limit = config.get('daily_limit', 100)
        self.is_active = config.get('is_active', True)
        
    async def send_email(self, to_email: str, subject: str, content: str, from_name: str = None) -> dict:
        """Send email - to be implemented by subclasses"""
        raise NotImplementedError
        
    def get_daily_sent_count(self) -> int:
        """Get today's sent email count for this provider"""
        # This would be implemented with database queries
        return 0
        
    def can_send_today(self) -> bool:
        """Check if provider can send more emails today"""
        return self.get_daily_sent_count() < self.daily_limit

class GmailProvider(EmailProvider):
    """Gmail OAuth provider"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.oauth_token = config.get('oauth_token')
        self.refresh_token = config.get('refresh_token')
        
    async def send_email(self, to_email: str, subject: str, content: str, from_name: str = None) -> dict:
        """Send email via Gmail OAuth"""
        try:
            # Gmail OAuth implementation would go here
            # For now, return success simulation
            logger.info(f"Gmail: Would send email to {to_email}")
            
            return {
                "success": True,
                "provider": "gmail",
                "message_id": f"gmail_{uuid.uuid4()}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Gmail send error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "provider": "gmail"
            }

class OutlookProvider(EmailProvider):
    """Outlook OAuth provider"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.oauth_token = config.get('oauth_token')
        self.refresh_token = config.get('refresh_token')
        
    async def send_email(self, to_email: str, subject: str, content: str, from_name: str = None) -> dict:
        """Send email via Outlook OAuth"""
        try:
            # Outlook OAuth implementation would go here
            # For now, return success simulation
            logger.info(f"Outlook: Would send email to {to_email}")
            
            return {
                "success": True,
                "provider": "outlook",
                "message_id": f"outlook_{uuid.uuid4()}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Outlook send error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "provider": "outlook"
            }

class CustomSMTPProvider(EmailProvider):
    """Custom SMTP provider"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.smtp_host = config.get('smtp_host')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.use_tls = config.get('use_tls', True)
        
    async def send_email(self, to_email: str, subject: str, content: str, from_name: str = None) -> dict:
        """Send email via custom SMTP"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{from_name or 'MailerPro'} <{self.username}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # Send via SMTP
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
            )
            
            logger.info(f"Custom SMTP: Sent email to {to_email}")
            
            return {
                "success": True,
                "provider": "custom_smtp",
                "message_id": f"smtp_{uuid.uuid4()}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Custom SMTP send error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "provider": "custom_smtp"
            }

class SMTPManager:
    """Manages multiple SMTP providers and email sending"""
    
    def __init__(self, db):
        self.db = db
        self.providers: List[EmailProvider] = []
        self._last_provider_index = 0
        
    async def load_providers(self) -> None:
        """Load SMTP configurations from database"""
        try:
            configs = await self.db.smtp_configs.find({"is_active": True}).to_list(length=None)
            self.providers = []
            
            for config in configs:
                provider_type = config.get('provider', 'custom')
                
                if provider_type == 'gmail':
                    provider = GmailProvider(config)
                elif provider_type == 'outlook':
                    provider = OutlookProvider(config)
                else:
                    provider = CustomSMTPProvider(config)
                    
                self.providers.append(provider)
                
            logger.info(f"Loaded {len(self.providers)} SMTP providers")
            
        except Exception as e:
            logger.error(f"Error loading SMTP providers: {str(e)}")
    
    def get_next_provider(self) -> Optional[EmailProvider]:
        """Get next available provider using round-robin"""
        if not self.providers:
            return None
            
        # Try each provider starting from the last used
        for i in range(len(self.providers)):
            index = (self._last_provider_index + i) % len(self.providers)
            provider = self.providers[index]
            
            if provider.is_active and provider.can_send_today():
                self._last_provider_index = (index + 1) % len(self.providers)
                return provider
                
        return None
    
    async def send_email(self, to_email: str, subject: str, content: str, from_name: str = None) -> dict:
        """Send email using next available provider"""
        provider = self.get_next_provider()
        
        if not provider:
            return {
                "success": False,
                "error": "No available email providers",
                "provider": None
            }
            
        return await provider.send_email(to_email, subject, content, from_name)

class EmailQueue:
    """Email queue management system"""
    
    def __init__(self, db, smtp_manager: SMTPManager):
        self.db = db
        self.smtp_manager = smtp_manager
        self.is_processing = False
        
    async def add_to_queue(self, campaign_id: str, contact_id: str, subject: str, content: str, scheduled_at: datetime = None) -> str:
        """Add email to sending queue"""
        email_id = str(uuid.uuid4())
        
        email_item = {
            "id": email_id,
            "campaign_id": campaign_id,
            "contact_id": contact_id,
            "subject": subject,
            "content": content,
            "status": "pending",
            "scheduled_at": (scheduled_at or datetime.now(timezone.utc)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "attempts": 0,
            "max_attempts": 3
        }
        
        await self.db.email_queue.insert_one(email_item)
        logger.info(f"Added email {email_id} to queue for campaign {campaign_id}")
        
        return email_id
    
    async def process_queue(self) -> None:
        """Process pending emails in queue"""
        if self.is_processing:
            return
            
        self.is_processing = True
        
        try:
            # Get pending emails that are scheduled for now or earlier
            current_time = datetime.now(timezone.utc).isoformat()
            
            pending_emails = await self.db.email_queue.find({
                "status": "pending",
                "scheduled_at": {"$lte": current_time},
                "attempts": {"$lt": 3}
            }).limit(10).to_list(length=None)
            
            for email_item in pending_emails:
                await self._send_queued_email(email_item)
                
                # Add delay between emails (5-15 seconds)
                delay = random.randint(5, 15)
                await asyncio.sleep(delay)
                
        except Exception as e:
            logger.error(f"Error processing email queue: {str(e)}")
        finally:
            self.is_processing = False
    
    async def _send_queued_email(self, email_item: dict) -> None:
        """Send a single queued email"""
        try:
            # Get contact details
            contact = await self.db.contacts.find_one({"id": email_item["contact_id"]})
            if not contact:
                await self._update_email_status(email_item["id"], "failed", "Contact not found")
                return
            
            # Send email
            result = await self.smtp_manager.send_email(
                to_email=contact["email"],
                subject=email_item["subject"],
                content=email_item["content"],
                from_name="MailerPro"
            )
            
            # Update status
            if result["success"]:
                await self._update_email_status(
                    email_item["id"], 
                    "sent", 
                    None, 
                    {
                        "message_id": result.get("message_id"),
                        "provider": result.get("provider"),
                        "sent_at": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                await self._retry_or_fail_email(email_item, result.get("error", "Unknown error"))
                
        except Exception as e:
            logger.error(f"Error sending queued email {email_item['id']}: {str(e)}")
            await self._retry_or_fail_email(email_item, str(e))
    
    async def _update_email_status(self, email_id: str, status: str, error: str = None, metadata: dict = None) -> None:
        """Update email status in database"""
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if error:
            update_data["error_message"] = error
            
        if metadata:
            update_data.update(metadata)
            
        await self.db.email_queue.update_one(
            {"id": email_id},
            {"$set": update_data}
        )
    
    async def _retry_or_fail_email(self, email_item: dict, error: str) -> None:
        """Retry email or mark as failed"""
        attempts = email_item.get("attempts", 0) + 1
        
        if attempts >= email_item.get("max_attempts", 3):
            await self._update_email_status(email_item["id"], "failed", error)
        else:
            # Schedule retry with exponential backoff
            retry_delay = min(300 * (2 ** attempts), 3600)  # Max 1 hour delay
            retry_time = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
            
            await self.db.email_queue.update_one(
                {"id": email_item["id"]},
                {
                    "$set": {
                        "attempts": attempts,
                        "scheduled_at": retry_time.isoformat(),
                        "error_message": error
                    }
                }
            )

class CampaignSender:
    """Handles campaign email sending logic"""
    
    def __init__(self, db, email_queue: EmailQueue):
        self.db = db
        self.email_queue = email_queue
    
    async def schedule_campaign(self, campaign_id: str) -> dict:
        """Schedule a campaign for sending"""
        try:
            # Get campaign
            campaign = await self.db.campaigns.find_one({"id": campaign_id})
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            # Get contacts
            contact_ids = campaign.get("contact_ids", [])
            if not contact_ids:
                return {"success": False, "error": "No contacts selected"}
            
            contacts = await self.db.contacts.find({"id": {"$in": contact_ids}}).to_list(length=None)
            
            # Schedule emails with delays
            daily_limit = campaign.get("daily_limit", 50)
            delay_between_emails = campaign.get("delay_between_emails", 300)
            
            scheduled_count = 0
            current_time = datetime.now(timezone.utc)
            
            for i, contact in enumerate(contacts):
                if scheduled_count >= daily_limit:
                    # Schedule for next day
                    current_time += timedelta(days=1)
                    current_time = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
                    scheduled_count = 0
                
                # Calculate send time
                send_time = current_time + timedelta(seconds=delay_between_emails * scheduled_count)
                
                # Personalize content
                personalized_subject = self._personalize_content(campaign["subject"], contact)
                personalized_content = self._personalize_content(campaign["content"], contact)
                
                # Add to queue
                await self.email_queue.add_to_queue(
                    campaign_id=campaign_id,
                    contact_id=contact["id"],
                    subject=personalized_subject,
                    content=personalized_content,
                    scheduled_at=send_time
                )
                
                scheduled_count += 1
            
            # Update campaign status
            await self.db.campaigns.update_one(
                {"id": campaign_id},
                {
                    "$set": {
                        "status": "scheduled",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            return {
                "success": True,
                "emails_scheduled": len(contacts),
                "start_time": current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scheduling campaign {campaign_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _personalize_content(self, content: str, contact: dict) -> str:
        """Apply personalization to content"""
        if not content:
            return content
        
        replacements = {
            '{{first_name}}': contact.get('first_name', ''),
            '{{last_name}}': contact.get('last_name', ''),
            '{{full_name}}': f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
            '{{email}}': contact.get('email', ''),
            '{{company}}': contact.get('company', ''),
            '{{phone}}': contact.get('phone', '')
        }
        
        personalized = content
        for tag, value in replacements.items():
            personalized = personalized.replace(tag, value)
        
        return personalized

# Background task runner
async def run_email_processor():
    """Background task to process email queue"""
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    
    # Connect to database
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    # Initialize services
    smtp_manager = SMTPManager(db)
    email_queue = EmailQueue(db, smtp_manager)
    
    # Load SMTP providers
    await smtp_manager.load_providers()
    
    logger.info("Email processor started")
    
    while True:
        try:
            await email_queue.process_queue()
            await asyncio.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            logger.info("Email processor stopped")
            break
        except Exception as e:
            logger.error(f"Email processor error: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    asyncio.run(run_email_processor())