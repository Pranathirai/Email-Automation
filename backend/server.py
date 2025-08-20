from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import csv
import io
import re
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from enum import Enum

# Import email service
from email_service import SMTPManager, EmailQueue, CampaignSender

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize email services
smtp_manager = SMTPManager(db)
email_queue = EmailQueue(db, smtp_manager)
campaign_sender = CampaignSender(db, email_queue)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled" 
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"

class EmailStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"

class SMTPProvider(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    CUSTOM = "custom"

# Models
class Contact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    first_name: str
    last_name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[List[str]] = None

class Campaign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    subject: str
    content: str
    contact_ids: List[str] = Field(default_factory=list)
    status: CampaignStatus = CampaignStatus.DRAFT
    daily_limit: int = 50
    delay_between_emails: int = 300  # seconds
    personalization_enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: Optional[datetime] = None

class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject: str
    content: str
    contact_ids: List[str] = Field(default_factory=list)
    daily_limit: int = 50
    delay_between_emails: int = 300
    personalization_enabled: bool = True

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    contact_ids: Optional[List[str]] = None
    daily_limit: Optional[int] = None
    delay_between_emails: Optional[int] = None
    personalization_enabled: Optional[bool] = None

class SMTPConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    provider: SMTPProvider
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    username: str
    password: Optional[str] = None  # Will be encrypted in production
    oauth_token: Optional[str] = None  # For Gmail/Outlook OAuth
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    is_active: bool = True
    daily_limit: int = 100
    use_tls: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SMTPConfigCreate(BaseModel):
    name: str
    provider: SMTPProvider
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    username: str
    password: Optional[str] = None
    oauth_token: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    daily_limit: int = 100
    use_tls: bool = True

class EmailQueue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    contact_id: str
    subject: str
    content: str
    status: EmailStatus = EmailStatus.PENDING
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    error_message: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    provider_used: Optional[str] = None
    message_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Helper functions
def prepare_for_mongo(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item.get('created_at'), str):
        item['created_at'] = datetime.fromisoformat(item['created_at'])
    if isinstance(item.get('updated_at'), str):
        item['updated_at'] = datetime.fromisoformat(item['updated_at'])
    if isinstance(item.get('scheduled_at'), str):
        item['scheduled_at'] = datetime.fromisoformat(item['scheduled_at'])
    if isinstance(item.get('sent_at'), str):
        item['sent_at'] = datetime.fromisoformat(item['sent_at'])
    return item

def personalize_content(content: str, contact: dict) -> str:
    """Replace personalization tags in content with contact data"""
    if not content:
        return content
    
    # Replace common personalization tags
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

# Contact Routes (existing)
@api_router.post("/contacts", response_model=Contact)
async def create_contact(contact_data: ContactCreate):
    contact_dict = contact_data.dict()
    contact = Contact(**contact_dict)
    contact_mongo = prepare_for_mongo(contact.dict())
    
    # Check if email already exists
    existing_contact = await db.contacts.find_one({"email": contact.email})
    if existing_contact:
        raise HTTPException(status_code=400, detail="Contact with this email already exists")
    
    await db.contacts.insert_one(contact_mongo)
    return contact

@api_router.get("/contacts", response_model=List[Contact])
async def get_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    tags: Optional[str] = Query(None)
):
    # Build query
    query = {}
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}}
        ]
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        query["tags"] = {"$in": tag_list}
    
    contacts = await db.contacts.find(query).skip(skip).limit(limit).to_list(length=None)
    return [Contact(**parse_from_mongo(contact)) for contact in contacts]

@api_router.get("/contacts/{contact_id}", response_model=Contact)
async def get_contact(contact_id: str):
    contact = await db.contacts.find_one({"id": contact_id})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return Contact(**parse_from_mongo(contact))

@api_router.put("/contacts/{contact_id}", response_model=Contact)
async def update_contact(contact_id: str, contact_data: ContactUpdate):
    contact = await db.contacts.find_one({"id": contact_id})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    update_data = {k: v for k, v in contact_data.dict(exclude_unset=True).items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.contacts.update_one({"id": contact_id}, {"$set": update_data})
    
    updated_contact = await db.contacts.find_one({"id": contact_id})
    return Contact(**parse_from_mongo(updated_contact))

@api_router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: str):
    result = await db.contacts.delete_one({"id": contact_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"message": "Contact deleted successfully"}

@api_router.post("/contacts/upload-csv")
async def upload_contacts_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        content = await file.read()
        csv_data = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        contacts_created = 0
        contacts_skipped = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Map CSV columns to contact fields
                contact_data = {
                    "first_name": row.get("first_name", "").strip(),
                    "last_name": row.get("last_name", "").strip(),
                    "email": row.get("email", "").strip(),
                    "company": row.get("company", "").strip() if row.get("company") else None,
                    "phone": row.get("phone", "").strip() if row.get("phone") else None,
                    "tags": [tag.strip() for tag in row.get("tags", "").split(",") if tag.strip()]
                }
                
                if not contact_data["email"]:
                    errors.append(f"Row {row_num}: Email is required")
                    continue
                
                if not contact_data["first_name"]:
                    errors.append(f"Row {row_num}: First name is required")
                    continue
                
                # Check if email already exists
                existing_contact = await db.contacts.find_one({"email": contact_data["email"]})
                if existing_contact:
                    contacts_skipped += 1
                    continue
                
                contact = Contact(**contact_data)
                contact_mongo = prepare_for_mongo(contact.dict())
                await db.contacts.insert_one(contact_mongo)
                contacts_created += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        return JSONResponse({
            "message": f"CSV processed successfully",
            "contacts_created": contacts_created,
            "contacts_skipped": contacts_skipped,
            "errors": errors[:10]  # Limit to first 10 errors
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

# Campaign Routes (Enhanced)
@api_router.post("/campaigns", response_model=Campaign)
async def create_campaign(campaign_data: CampaignCreate):
    campaign_dict = campaign_data.dict()
    campaign = Campaign(**campaign_dict)
    campaign_mongo = prepare_for_mongo(campaign.dict())
    await db.campaigns.insert_one(campaign_mongo)
    return campaign

@api_router.get("/campaigns", response_model=List[Campaign])
async def get_campaigns():
    campaigns = await db.campaigns.find().sort("created_at", -1).to_list(length=None)
    return [Campaign(**parse_from_mongo(campaign)) for campaign in campaigns]

@api_router.get("/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str):
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return Campaign(**parse_from_mongo(campaign))

@api_router.put("/campaigns/{campaign_id}", response_model=Campaign)
async def update_campaign(campaign_id: str, campaign_data: CampaignUpdate):
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_data = {k: v for k, v in campaign_data.dict(exclude_unset=True).items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.campaigns.update_one({"id": campaign_id}, {"$set": update_data})
    
    updated_campaign = await db.campaigns.find_one({"id": campaign_id})
    return Campaign(**parse_from_mongo(updated_campaign))

@api_router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    result = await db.campaigns.delete_one({"id": campaign_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"message": "Campaign deleted successfully"}

# Campaign Preview
@api_router.post("/campaigns/{campaign_id}/preview")
async def preview_campaign(campaign_id: str, contact_id: str = Query(...)):
    # Get campaign
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get contact
    contact = await db.contacts.find_one({"id": contact_id})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Personalize content
    personalized_subject = personalize_content(campaign["subject"], contact)
    personalized_content = personalize_content(campaign["content"], contact)
    
    return {
        "subject": personalized_subject,
        "content": personalized_content,
        "contact": {
            "name": f"{contact['first_name']} {contact['last_name']}",
            "email": contact["email"],
            "company": contact.get("company")
        }
    }

# Campaign Sending
@api_router.post("/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: str):
    """Schedule campaign for sending"""
    try:
        result = await campaign_sender.schedule_campaign(campaign_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling campaign: {str(e)}")

@api_router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    """Pause an active campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": "paused", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Campaign paused successfully"}

@api_router.post("/campaigns/{campaign_id}/resume")
async def resume_campaign(campaign_id: str):
    """Resume a paused campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": "scheduled", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Campaign resumed successfully"}

# Campaign Analytics
@api_router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: str):
    # Get campaign
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get email queue stats
    total_emails = await db.email_queue.count_documents({"campaign_id": campaign_id})
    sent_emails = await db.email_queue.count_documents({"campaign_id": campaign_id, "status": "sent"})
    pending_emails = await db.email_queue.count_documents({"campaign_id": campaign_id, "status": "pending"})
    failed_emails = await db.email_queue.count_documents({"campaign_id": campaign_id, "status": "failed"})
    
    # Advanced metrics (placeholder for future implementation)
    opened_emails = await db.email_queue.count_documents({"campaign_id": campaign_id, "status": "opened"})
    clicked_emails = await db.email_queue.count_documents({"campaign_id": campaign_id, "status": "clicked"})
    bounced_emails = await db.email_queue.count_documents({"campaign_id": campaign_id, "status": "bounced"})
    
    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign["name"],
        "total_emails": total_emails,
        "sent_emails": sent_emails,
        "pending_emails": pending_emails,
        "delivered_emails": sent_emails - bounced_emails,
        "opened_emails": opened_emails,
        "clicked_emails": clicked_emails,
        "bounced_emails": bounced_emails,
        "failed_emails": failed_emails,
        "open_rate": round((opened_emails / sent_emails * 100) if sent_emails > 0 else 0, 2),
        "click_rate": round((clicked_emails / sent_emails * 100) if sent_emails > 0 else 0, 2),
        "bounce_rate": round((bounced_emails / sent_emails * 100) if sent_emails > 0 else 0, 2),
        "delivery_rate": round(((sent_emails - bounced_emails) / sent_emails * 100) if sent_emails > 0 else 0, 2)
    }

# SMTP Configuration Routes
@api_router.post("/smtp-configs", response_model=SMTPConfig)
async def create_smtp_config(smtp_data: SMTPConfigCreate):
    smtp_dict = smtp_data.dict()
    smtp_config = SMTPConfig(**smtp_dict)
    smtp_mongo = prepare_for_mongo(smtp_config.dict())
    await db.smtp_configs.insert_one(smtp_mongo)
    
    # Reload SMTP providers
    await smtp_manager.load_providers()
    
    return smtp_config

@api_router.get("/smtp-configs", response_model=List[SMTPConfig])
async def get_smtp_configs():
    configs = await db.smtp_configs.find().to_list(length=None)
    return [SMTPConfig(**parse_from_mongo(config)) for config in configs]

@api_router.get("/smtp-configs/{config_id}", response_model=SMTPConfig)
async def get_smtp_config(config_id: str):
    config = await db.smtp_configs.find_one({"id": config_id})
    if not config:
        raise HTTPException(status_code=404, detail="SMTP config not found")
    return SMTPConfig(**parse_from_mongo(config))

@api_router.put("/smtp-configs/{config_id}", response_model=SMTPConfig)
async def update_smtp_config(config_id: str, smtp_data: SMTPConfigCreate):
    config = await db.smtp_configs.find_one({"id": config_id})
    if not config:
        raise HTTPException(status_code=404, detail="SMTP config not found")
    
    update_data = smtp_data.dict()
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.smtp_configs.update_one({"id": config_id}, {"$set": update_data})
    
    # Reload SMTP providers
    await smtp_manager.load_providers()
    
    updated_config = await db.smtp_configs.find_one({"id": config_id})
    return SMTPConfig(**parse_from_mongo(updated_config))

@api_router.delete("/smtp-configs/{config_id}")
async def delete_smtp_config(config_id: str):
    result = await db.smtp_configs.delete_one({"id": config_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="SMTP config not found")
    
    # Reload SMTP providers
    await smtp_manager.load_providers()
    
    return {"message": "SMTP config deleted successfully"}

@api_router.post("/smtp-configs/{config_id}/test")
async def test_smtp_config(config_id: str, test_email: str = Query(...)):
    """Test an SMTP configuration by sending a test email"""
    config = await db.smtp_configs.find_one({"id": config_id})
    if not config:
        raise HTTPException(status_code=404, detail="SMTP config not found")
    
    # Send test email using the email service
    result = await smtp_manager.send_email(
        to_email=test_email,
        subject="Test Email from MailerPro",
        content="This is a test email to verify your SMTP configuration is working correctly.",
        from_name="MailerPro Test"
    )
    
    return result

# Email Queue Routes
@api_router.get("/email-queue")
async def get_email_queue(
    campaign_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get email queue with optional filtering"""
    query = {}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if status:
        query["status"] = status
    
    emails = await db.email_queue.find(query).limit(limit).sort("created_at", -1).to_list(length=None)
    return [parse_from_mongo(email) for email in emails]

@api_router.post("/email-queue/process")
async def process_email_queue():
    """Manually trigger email queue processing"""
    await email_queue.process_queue()
    return {"message": "Email queue processing triggered"}

# Stats Routes (Enhanced)
@api_router.get("/stats/dashboard")
async def get_dashboard_stats():
    total_contacts = await db.contacts.count_documents({})
    total_campaigns = await db.campaigns.count_documents({})
    
    # Get recent contacts (last 7 days)
    seven_days_ago = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = seven_days_ago.replace(day=max(1, seven_days_ago.day - 7))
    
    recent_contacts = await db.contacts.count_documents({
        "created_at": {"$gte": seven_days_ago.isoformat()}
    })
    
    # Get active campaigns
    active_campaigns = await db.campaigns.count_documents({
        "status": {"$in": ["sending", "scheduled"]}
    })
    
    # Get total emails sent
    total_emails_sent = await db.email_queue.count_documents({"status": "sent"})
    
    # Calculate overall open rate
    total_opens = await db.email_queue.count_documents({"status": "opened"})
    overall_open_rate = round((total_opens / total_emails_sent * 100) if total_emails_sent > 0 else 0, 2)
    
    # Get pending emails
    pending_emails = await db.email_queue.count_documents({"status": "pending"})
    
    return {
        "total_contacts": total_contacts,
        "total_campaigns": total_campaigns,
        "recent_contacts": recent_contacts,
        "active_campaigns": active_campaigns,
        "total_emails_sent": total_emails_sent,
        "pending_emails": pending_emails,
        "overall_open_rate": overall_open_rate
    }

# Root route
@api_router.get("/")
async def root():
    return {"message": "MailerPro API - Email Outreach Platform"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize email services on startup"""
    await smtp_manager.load_providers()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()