from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import csv
import io
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

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
    subject: str
    content: str
    contact_ids: List[str] = Field(default_factory=list)
    status: str = "draft"  # draft, scheduled, sending, sent, paused
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CampaignCreate(BaseModel):
    name: str
    subject: str
    content: str
    contact_ids: List[str] = Field(default_factory=list)

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
    return item

# Contact Routes
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

# Campaign Routes
@api_router.post("/campaigns", response_model=Campaign)
async def create_campaign(campaign_data: CampaignCreate):
    campaign_dict = campaign_data.dict()
    campaign = Campaign(**campaign_dict)
    campaign_mongo = prepare_for_mongo(campaign.dict())
    await db.campaigns.insert_one(campaign_mongo)
    return campaign

@api_router.get("/campaigns", response_model=List[Campaign])
async def get_campaigns():
    campaigns = await db.campaigns.find().to_list(length=None)
    return [Campaign(**parse_from_mongo(campaign)) for campaign in campaigns]

@api_router.get("/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str):
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return Campaign(**parse_from_mongo(campaign))

# Stats Routes
@api_router.get("/stats/dashboard")
async def get_dashboard_stats():
    total_contacts = await db.contacts.count_documents({})
    total_campaigns = await db.campaigns.count_documents({})
    
    # Get recent contacts (last 7 days)
    seven_days_ago = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = seven_days_ago.replace(day=seven_days_ago.day - 7)
    
    recent_contacts = await db.contacts.count_documents({
        "created_at": {"$gte": seven_days_ago.isoformat()}
    })
    
    return {
        "total_contacts": total_contacts,
        "total_campaigns": total_campaigns,
        "recent_contacts": recent_contacts,
        "active_campaigns": 0  # Placeholder
    }

# Root route
@api_router.get("/")
async def root():
    return {"message": "Email Outreach SaaS API"}

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()