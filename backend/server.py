from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query, Depends, Request
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import csv
import io
import re
import hashlib
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
import bcrypt
import jwt
from passlib.context import CryptContext

# Import Stripe integration
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe configuration
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', 'sk_test_default_key')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Subscription Plans
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free Trial",
        "price": 0.0,
        "contacts_limit": 100,
        "campaigns_limit": 2,
        "emails_per_day": 50,
        "inboxes_limit": 999999  # Unlimited inboxes for free tier
    },
    "pro": {
        "name": "Pro Plan",
        "price": 49.0,
        "contacts_limit": 5000,
        "campaigns_limit": 20,
        "emails_per_day": 1000,
        "inboxes_limit": 999999  # Unlimited inboxes for pro tier
    },
    "agency": {
        "name": "Agency Plan", 
        "price": 149.0,
        "contacts_limit": 50000,
        "campaigns_limit": 100,
        "emails_per_day": 10000,
        "inboxes_limit": 999999  # Unlimited inboxes for agency tier
    }
}

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

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    hashed_password: str
    full_name: str
    is_active: bool = True
    subscription_plan: str = "free"
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    stripe_customer_id: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    subscription_plan: str
    subscription_status: str
    subscription_expires_at: Optional[datetime] = None
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class Contact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
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

class CampaignVariation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # e.g., "Variation A", "Variation B"
    subject: str
    content: str
    weight: int = 50  # Distribution percentage (50% = equal split)

class CampaignStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_order: int  # 1 for first email, 2 for follow-up, etc.
    delay_days: int = 0  # Days to wait before sending (0 = immediate)
    variations: List[CampaignVariation] = Field(default_factory=list)
    conditions: Dict[str, Any] = Field(default_factory=dict)  # Conditional logic

class Campaign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: Optional[str] = None
    # Multi-step campaign support
    steps: List[CampaignStep] = Field(default_factory=list)
    # Contact and targeting
    contact_ids: List[str] = Field(default_factory=list)
    contact_list_ids: List[str] = Field(default_factory=list)  # Future: contact lists
    # Sending configuration
    smtp_config_ids: List[str] = Field(default_factory=list)  # Inbox rotation
    daily_limit_per_inbox: int = 200
    delay_min_seconds: int = 300  # 5 minutes minimum gap
    delay_max_seconds: int = 1800  # 30 minutes maximum gap
    # Campaign settings
    status: CampaignStatus = CampaignStatus.DRAFT
    personalization_enabled: bool = True
    a_b_testing_enabled: bool = True
    # Template and variables
    available_variables: List[str] = Field(default_factory=lambda: [
        "first_name", "last_name", "email", "company", "phone"
    ])
    custom_variables: Dict[str, str] = Field(default_factory=dict)
    # Scheduling
    scheduled_at: Optional[datetime] = None
    timezone: str = "UTC"
    # Analytics
    total_sent: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_replied: int = 0
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[CampaignStep] = Field(default_factory=list)
    contact_ids: List[str] = Field(default_factory=list)
    smtp_config_ids: List[str] = Field(default_factory=list)
    daily_limit_per_inbox: int = 200
    delay_min_seconds: int = 300
    delay_max_seconds: int = 1800
    personalization_enabled: bool = True
    a_b_testing_enabled: bool = True
    timezone: str = "UTC"

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[CampaignStep]] = None
    contact_ids: Optional[List[str]] = None
    smtp_config_ids: Optional[List[str]] = None
    daily_limit_per_inbox: Optional[int] = None
    delay_min_seconds: Optional[int] = None
    delay_max_seconds: Optional[int] = None
    status: Optional[CampaignStatus] = None

class VariablePreviewRequest(BaseModel):
    template: str  # Template with {{variables}}
    contact_id: str  # Contact to preview with

class EmailTracking(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    campaign_step_id: str
    variation_id: str
    contact_id: str
    smtp_config_id: str
    email: str
    subject: str  # Personalized subject
    content: str  # Personalized content
    status: EmailStatus = EmailStatus.PENDING
    # Tracking timestamps
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    # Tracking data
    tracking_pixel_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    click_links: List[str] = Field(default_factory=list)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    # A/B testing
    variation_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    email: str
    status: EmailStatus = EmailStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    tracking_pixel_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    click_links: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: str
    amount: float
    currency: str = "usd"
    plan: str
    status: PaymentStatus = PaymentStatus.PENDING
    payment_status: str = "pending"
    metadata: Dict[str, str] = Field(default_factory=dict)
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SMTPConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str  # User-friendly name like "My Gmail Account"
    provider: SMTPProvider
    email: EmailStr  # Email address for this SMTP config
    # SMTP Settings
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None  # Encrypted
    use_tls: bool = True
    use_ssl: bool = False
    # OAuth Settings (for Gmail/Outlook)
    access_token: Optional[str] = None  # Encrypted
    refresh_token: Optional[str] = None  # Encrypted
    token_expires_at: Optional[datetime] = None
    # Status
    is_active: bool = True
    is_verified: bool = False
    last_test_at: Optional[datetime] = None
    daily_sent_count: int = 0
    daily_limit: int = 300  # Daily sending limit for this account
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SMTPConfigCreate(BaseModel):
    name: str
    provider: SMTPProvider
    email: EmailStr
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    daily_limit: int = 300

class SMTPConfigUpdate(BaseModel):
    name: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    daily_limit: Optional[int] = None
    is_active: Optional[bool] = None

class SMTPTestRequest(BaseModel):
    test_email: EmailStr
    subject: str = "Test Email from MailerPro"
    content: str = "This is a test email to verify your SMTP configuration."

class SubscriptionRequest(BaseModel):
    plan: str
    origin_url: str

# Helper functions
def prepare_for_mongo(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    datetime_fields = ['created_at', 'updated_at', 'scheduled_at', 'sent_at', 'delivered_at', 
                      'opened_at', 'clicked_at', 'bounced_at', 'replied_at', 'subscription_expires_at',
                      'token_expires_at', 'last_test_at']
    for field in datetime_fields:
        if isinstance(item.get(field), str):
            try:
                item[field] = datetime.fromisoformat(item[field])
            except:
                pass
    return item

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None

async def get_current_user(request: Request) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return User(**parse_from_mongo(user))

async def check_subscription_limits(user: User, resource_type: str, current_count: int = 0):
    """Check if user has reached subscription limits"""
    plan = SUBSCRIPTION_PLANS.get(user.subscription_plan, SUBSCRIPTION_PLANS["free"])
    
    if resource_type == "contacts" and current_count >= plan["contacts_limit"]:
        raise HTTPException(status_code=403, detail=f"Contact limit reached. Upgrade to add more contacts.")
    elif resource_type == "campaigns" and current_count >= plan["campaigns_limit"]:
        raise HTTPException(status_code=403, detail=f"Campaign limit reached. Upgrade to create more campaigns.")
    elif resource_type == "inboxes" and current_count >= plan["inboxes_limit"]:
        raise HTTPException(status_code=403, detail=f"Inbox limit reached. Upgrade to add more inboxes.")

# SMTP Helper Functions
def encrypt_sensitive_data(data: str) -> str:
    """Simple base64 encoding for sensitive SMTP data - should use proper encryption in production"""
    import base64
    return base64.b64encode(data.encode()).decode()

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Simple base64 decoding for sensitive SMTP data - should use proper decryption in production"""
    import base64
    return base64.b64decode(encrypted_data.encode()).decode()

async def get_default_smtp_settings(provider: SMTPProvider) -> dict:
    """Get default SMTP settings for common providers"""
    defaults = {
        SMTPProvider.GMAIL: {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "use_tls": True,
            "use_ssl": False
        },
        SMTPProvider.OUTLOOK: {
            "smtp_host": "smtp-mail.outlook.com", 
            "smtp_port": 587,
            "use_tls": True,
            "use_ssl": False
        },
        SMTPProvider.CUSTOM: {
            "smtp_host": None,
            "smtp_port": 587,
            "use_tls": True,
            "use_ssl": False
        }
    }
    return defaults.get(provider, defaults[SMTPProvider.CUSTOM])

async def test_smtp_connection(smtp_config: SMTPConfig, test_email: str, subject: str, content: str) -> dict:
    """Test SMTP connection by sending a test email"""
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create message
        message = MIMEMultipart()
        message["From"] = smtp_config.email
        message["To"] = test_email
        message["Subject"] = subject
        message.attach(MIMEText(content, "plain"))
        
        # Decrypt credentials if needed
        password = decrypt_sensitive_data(smtp_config.smtp_password) if smtp_config.smtp_password else None
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=smtp_config.smtp_host,
            port=smtp_config.smtp_port,
            start_tls=smtp_config.use_tls,
            use_tls=smtp_config.use_ssl,
            username=smtp_config.smtp_username or smtp_config.email,
            password=password,
        )
        
        return {"success": True, "message": "Test email sent successfully"}
        
    except Exception as e:
        error_message = str(e)
        
        # Provide more helpful error messages for common issues
        if "534" in error_message and "Application-specific password" in error_message:
            return {
                "success": False, 
                "message": "Gmail requires an App Password. Please: 1) Enable 2FA on your Google account, 2) Generate an App Password at myaccount.google.com/apppasswords, 3) Use that App Password instead of your regular password.",
                "error_type": "gmail_app_password_required"
            }
        elif "535" in error_message and ("Username and Password not accepted" in error_message or "authentication" in error_message.lower()):
            # Special handling for Gmail 535 errors
            if "gmail.com" in smtp_config.smtp_host.lower():
                return {
                    "success": False,
                    "message": "Gmail requires an App Password. Please: 1) Enable 2FA on your Google account, 2) Generate an App Password at myaccount.google.com/apppasswords, 3) Use that App Password instead of your regular password.",
                    "error_type": "gmail_app_password_required"
                }
            else:
                return {
                    "success": False,
                    "message": "Authentication failed. Please check your username and password. For Gmail, use an App Password instead of your regular password.",
                    "error_type": "authentication_failed"
                }
        elif "Error connecting" in error_message and ("Name or service not known" in error_message or "Connection refused" in error_message or "Connection timed out" in error_message):
            return {
                "success": False,
                "message": "Cannot connect to SMTP server. Please check your host and port settings.",
                "error_type": "connection_failed"
            }
        elif "SSL" in error_message or "TLS" in error_message or "Unexpected EOF received" in error_message:
            return {
                "success": False,
                "message": "SSL/TLS connection error. Try toggling TLS/SSL settings or use port 465 for SSL.",
                "error_type": "ssl_tls_error"
            }
        else:
            return {"success": False, "message": f"SMTP test failed: {error_message}", "error_type": "unknown_error"}

async def send_email_via_smtp(smtp_config: SMTPConfig, to_email: str, subject: str, content: str, content_type: str = "html") -> dict:
    """Send email using SMTP configuration"""
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create message
        message = MIMEMultipart()
        message["From"] = smtp_config.email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(content, content_type))
        
        # Decrypt credentials if needed
        password = decrypt_sensitive_data(smtp_config.smtp_password) if smtp_config.smtp_password else None
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=smtp_config.smtp_host,
            port=smtp_config.smtp_port,
            start_tls=smtp_config.use_tls,
            use_tls=smtp_config.use_ssl,
            username=smtp_config.smtp_username or smtp_config.email,
            password=password,
        )
        
        # Update daily sent count
        await db.smtp_configs.update_one(
            {"id": smtp_config.id},
            {"$inc": {"daily_sent_count": 1}}
        )
        
        return {"success": True, "message": "Email sent successfully"}
        
    except Exception as e:
        return {"success": False, "message": f"Email sending failed: {str(e)}"}

# Campaign Helper Functions
def personalize_template(template: str, contact: dict, custom_variables: dict = None) -> str:
    """Replace variables in template with contact data"""
    import re
    
    # Default available variables
    variables = {
        "first_name": contact.get("first_name", ""),
        "last_name": contact.get("last_name", ""),
        "full_name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
        "email": contact.get("email", ""),
        "company": contact.get("company", ""),
        "phone": contact.get("phone", ""),
    }
    
    # Add custom variables if provided
    if custom_variables:
        variables.update(custom_variables)
    
    # Replace variables in template
    def replace_variable(match):
        var_name = match.group(1).lower()
        return variables.get(var_name, f"{{{{{var_name}}}}}")  # Keep original if not found
    
    # Find all {{variable}} patterns and replace them
    personalized = re.sub(r'\{\{([^}]+)\}\}', replace_variable, template)
    
    # Clean up empty variables (optional)
    personalized = re.sub(r'\s+', ' ', personalized)  # Remove extra spaces
    
    return personalized

def extract_variables_from_template(template: str) -> List[str]:
    """Extract all variable names from a template"""
    import re
    variables = re.findall(r'\{\{([^}]+)\}\}', template)
    return list(set([var.strip().lower() for var in variables]))

def validate_campaign_variables(campaign: Campaign, contacts: List[dict]) -> dict:
    """Validate that all variables in campaign can be filled by contact data"""
    issues = []
    missing_variables = set()
    
    # Extract variables from all steps and variations
    all_templates = []
    for step in campaign.steps:
        for variation in step.variations:
            all_templates.extend([variation.subject, variation.content])
    
    # Get all required variables
    required_variables = set()
    for template in all_templates:
        required_variables.update(extract_variables_from_template(template))
    
    # Check each contact
    available_fields = ["first_name", "last_name", "email", "company", "phone"]
    for contact in contacts:
        for var in required_variables:
            if var not in available_fields and var not in campaign.custom_variables:
                missing_variables.add(var)
    
    if missing_variables:
        issues.append(f"Missing variables: {', '.join(missing_variables)}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "required_variables": list(required_variables),
        "missing_variables": list(missing_variables)
    }

async def select_campaign_variation(step: CampaignStep, contact_id: str) -> CampaignVariation:
    """Select which variation to send based on A/B testing weights"""
    import random
    
    if not step.variations:
        return None
    
    # Simple A/B testing: use contact_id hash for consistent assignment
    contact_hash = hash(f"{step.id}_{contact_id}")
    random.seed(contact_hash)
    
    # Calculate cumulative weights
    total_weight = sum(var.weight for var in step.variations)
    if total_weight == 0:
        return step.variations[0]  # Return first if no weights
    
    # Select variation based on weight
    rand_num = random.randint(1, total_weight)
    cumulative_weight = 0
    
    for variation in step.variations:
        cumulative_weight += variation.weight
        if rand_num <= cumulative_weight:
            return variation
    
    return step.variations[-1]  # Fallback to last variation

async def get_next_smtp_config(smtp_config_ids: List[str], user_id: str) -> SMTPConfig:
    """Get next SMTP config for rotation (round-robin with daily limits)"""
    
    if not smtp_config_ids:
        return None
    
    # Get all SMTP configs for user
    configs_cursor = db.smtp_configs.find({
        "id": {"$in": smtp_config_ids},
        "user_id": user_id,
        "is_active": True
    })
    configs = await configs_cursor.to_list(length=None)
    
    if not configs:
        return None
    
    # Filter configs that haven't reached daily limit
    available_configs = []
    for config in configs:
        daily_sent = config.get("daily_sent_count", 0)
        daily_limit = config.get("daily_limit", 300)
        if daily_sent < daily_limit:
            available_configs.append(config)
    
    if not available_configs:
        return None  # All configs reached daily limit
    
    # Simple round-robin: return config with lowest sent count
    selected_config = min(available_configs, key=lambda c: c.get("daily_sent_count", 0))
    return SMTPConfig(**parse_from_mongo(selected_config))

def calculate_random_delay(min_seconds: int, max_seconds: int) -> int:
    """Calculate random delay between min and max for human-like behavior"""
    import random
    return random.randint(min_seconds, max_seconds)

# Authentication Routes
@api_router.post("/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    
    user_mongo = prepare_for_mongo(user.dict())
    await db.users.insert_one(user_mongo)
    
    return UserResponse(**user.dict())

@api_router.post("/auth/login", response_model=Token)
async def login_user(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token = create_access_token(data={"sub": user["email"]})
    
    user_response = UserResponse(**parse_from_mongo(user))
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(**current_user.dict())

# SMTP Configuration Routes
@api_router.post("/smtp-configs", response_model=SMTPConfig)
async def create_smtp_config(smtp_data: SMTPConfigCreate, current_user: User = Depends(get_current_user)):
    """Create a new SMTP configuration"""
    # Check subscription limits
    current_count = await db.smtp_configs.count_documents({"user_id": current_user.id})
    await check_subscription_limits(current_user, "inboxes", current_count)
    
    # Get default settings for the provider
    defaults = await get_default_smtp_settings(smtp_data.provider)
    
    # Create SMTP config
    smtp_config = SMTPConfig(
        user_id=current_user.id,
        **smtp_data.dict(),
        **{k: v for k, v in defaults.items() if getattr(smtp_data, k) is None and k not in ['smtp_host', 'smtp_port']}
    )
    
    # Apply provider defaults if not specified
    if not smtp_config.smtp_host:
        smtp_config.smtp_host = defaults["smtp_host"]
    if not smtp_config.smtp_port:
        smtp_config.smtp_port = defaults["smtp_port"]
    
    # Encrypt sensitive data
    if smtp_config.smtp_password:
        smtp_config.smtp_password = encrypt_sensitive_data(smtp_config.smtp_password)
    
    smtp_mongo = prepare_for_mongo(smtp_config.dict())
    await db.smtp_configs.insert_one(smtp_mongo)
    
    return smtp_config

@api_router.get("/smtp-configs", response_model=List[SMTPConfig])
async def get_smtp_configs(current_user: User = Depends(get_current_user)):
    """Get all SMTP configurations for the current user"""
    configs = await db.smtp_configs.find({"user_id": current_user.id}).sort("created_at", -1).to_list(length=None)
    result = []
    for config in configs:
        config = parse_from_mongo(config)
        # Don't return sensitive data in list view
        if config.get("smtp_password"):
            config["smtp_password"] = "***encrypted***"
        if config.get("access_token"):
            config["access_token"] = "***encrypted***"
        if config.get("refresh_token"):
            config["refresh_token"] = "***encrypted***"
        result.append(SMTPConfig(**config))
    return result

@api_router.get("/smtp-configs/{config_id}", response_model=SMTPConfig)
async def get_smtp_config(config_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific SMTP configuration"""
    config = await db.smtp_configs.find_one({"id": config_id, "user_id": current_user.id})
    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")
    
    config = parse_from_mongo(config)
    # Don't return sensitive data
    if config.get("smtp_password"):
        config["smtp_password"] = "***encrypted***"
    if config.get("access_token"):
        config["access_token"] = "***encrypted***"
    if config.get("refresh_token"):
        config["refresh_token"] = "***encrypted***"
    
    return SMTPConfig(**config)

@api_router.put("/smtp-configs/{config_id}", response_model=SMTPConfig)
async def update_smtp_config(config_id: str, smtp_data: SMTPConfigUpdate, current_user: User = Depends(get_current_user)):
    """Update an SMTP configuration"""
    config = await db.smtp_configs.find_one({"id": config_id, "user_id": current_user.id})
    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")
    
    update_data = {k: v for k, v in smtp_data.dict(exclude_unset=True).items() if v is not None}
    
    # Encrypt password if provided
    if "smtp_password" in update_data:
        update_data["smtp_password"] = encrypt_sensitive_data(update_data["smtp_password"])
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.smtp_configs.update_one(
        {"id": config_id, "user_id": current_user.id},
        {"$set": prepare_for_mongo(update_data)}
    )
    
    # Get updated config
    updated_config = await db.smtp_configs.find_one({"id": config_id, "user_id": current_user.id})
    updated_config = parse_from_mongo(updated_config)
    
    # Don't return sensitive data
    if updated_config.get("smtp_password"):
        updated_config["smtp_password"] = "***encrypted***"
    
    return SMTPConfig(**updated_config)

@api_router.delete("/smtp-configs/{config_id}")
async def delete_smtp_config(config_id: str, current_user: User = Depends(get_current_user)):
    """Delete an SMTP configuration"""
    result = await db.smtp_configs.delete_one({"id": config_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")
    
    return {"message": "SMTP configuration deleted successfully"}

@api_router.post("/smtp-configs/{config_id}/test")
async def test_smtp_config(config_id: str, test_request: SMTPTestRequest, current_user: User = Depends(get_current_user)):
    """Test an SMTP configuration by sending a test email"""
    config = await db.smtp_configs.find_one({"id": config_id, "user_id": current_user.id})
    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")
    
    config = parse_from_mongo(config)
    smtp_config = SMTPConfig(**config)
    
    # Test the connection
    result = await test_smtp_connection(
        smtp_config,
        test_request.test_email,
        test_request.subject,
        test_request.content
    )
    
    # Update verification status and last test time
    update_data = {
        "last_test_at": datetime.now(timezone.utc).isoformat(),
        "is_verified": result["success"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.smtp_configs.update_one(
        {"id": config_id, "user_id": current_user.id},
        {"$set": prepare_for_mongo(update_data)}
    )
    
    return result

@api_router.get("/smtp-configs/{config_id}/stats")
async def get_smtp_config_stats(config_id: str, current_user: User = Depends(get_current_user)):
    """Get sending statistics for an SMTP configuration"""
    config = await db.smtp_configs.find_one({"id": config_id, "user_id": current_user.id})
    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")
    
    # Get stats from email tracking where this SMTP was used
    # For now, return basic stats from the config
    return {
        "daily_sent_count": config.get("daily_sent_count", 0),
        "daily_limit": config.get("daily_limit", 300),
        "remaining_today": max(0, config.get("daily_limit", 300) - config.get("daily_sent_count", 0)),
        "is_verified": config.get("is_verified", False),
        "last_test_at": config.get("last_test_at"),
        "status": "active" if config.get("is_active", False) else "inactive"
    }

# Contact Routes (with user context and limits)
@api_router.post("/contacts", response_model=Contact)
async def create_contact(contact_data: ContactCreate, current_user: User = Depends(get_current_user)):
    # Check subscription limits
    current_count = await db.contacts.count_documents({"user_id": current_user.id})
    await check_subscription_limits(current_user, "contacts", current_count)
    
    # Check if email already exists for this user
    existing_contact = await db.contacts.find_one({"email": contact_data.email, "user_id": current_user.id})
    if existing_contact:
        raise HTTPException(status_code=400, detail="Contact with this email already exists")
    
    contact = Contact(user_id=current_user.id, **contact_data.dict())
    contact_mongo = prepare_for_mongo(contact.dict())
    await db.contacts.insert_one(contact_mongo)
    
    return contact

@api_router.get("/contacts", response_model=List[Contact])
async def get_contacts(
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    tags: Optional[str] = Query(None)
):
    query = {"user_id": current_user.id}
    
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}}
        ]
        query["$and"] = [{"user_id": current_user.id}, {"$or": query.pop("$or")}]
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        if "$and" in query:
            query["$and"].append({"tags": {"$in": tag_list}})
        else:
            query["tags"] = {"$in": tag_list}
    
    contacts = await db.contacts.find(query).skip(skip).limit(limit).to_list(length=None)
    return [Contact(**parse_from_mongo(contact)) for contact in contacts]

@api_router.post("/contacts/upload-csv")
async def upload_contacts_csv(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
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
                # Check limits before creating
                current_count = await db.contacts.count_documents({"user_id": current_user.id})
                await check_subscription_limits(current_user, "contacts", current_count + contacts_created)
                
                contact_data = {
                    "first_name": row.get("first_name", "").strip(),
                    "last_name": row.get("last_name", "").strip(),
                    "email": row.get("email", "").strip(),
                    "company": row.get("company", "").strip() if row.get("company") else None,
                    "phone": row.get("phone", "").strip() if row.get("phone") else None,
                    "tags": [tag.strip() for tag in row.get("tags", "").split(",") if tag.strip()]
                }
                
                if not contact_data["email"] or not contact_data["first_name"]:
                    errors.append(f"Row {row_num}: Email and first name are required")
                    continue
                
                # Check if email already exists
                existing_contact = await db.contacts.find_one({
                    "email": contact_data["email"], 
                    "user_id": current_user.id
                })
                if existing_contact:
                    contacts_skipped += 1
                    continue
                
                contact = Contact(user_id=current_user.id, **contact_data)
                contact_mongo = prepare_for_mongo(contact.dict())
                await db.contacts.insert_one(contact_mongo)
                contacts_created += 1
                
            except HTTPException as e:
                if "limit reached" in str(e.detail):
                    errors.append(f"Row {row_num}: {e.detail}")
                    break
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        return JSONResponse({
            "message": f"CSV processed successfully",
            "contacts_created": contacts_created,
            "contacts_skipped": contacts_skipped,
            "errors": errors[:10]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

# Enhanced Campaign Routes
@api_router.post("/campaigns", response_model=Campaign)
async def create_campaign(campaign_data: CampaignCreate, current_user: User = Depends(get_current_user)):
    # Check subscription limits
    current_count = await db.campaigns.count_documents({"user_id": current_user.id})
    await check_subscription_limits(current_user, "campaigns", current_count)
    
    # Validate SMTP configs belong to user
    if campaign_data.smtp_config_ids:
        smtp_count = await db.smtp_configs.count_documents({
            "id": {"$in": campaign_data.smtp_config_ids},
            "user_id": current_user.id
        })
        if smtp_count != len(campaign_data.smtp_config_ids):
            raise HTTPException(status_code=400, detail="Some SMTP configurations not found")
    
    campaign = Campaign(user_id=current_user.id, **campaign_data.dict())
    campaign_mongo = prepare_for_mongo(campaign.dict())
    await db.campaigns.insert_one(campaign_mongo)
    
    return campaign

@api_router.get("/campaigns", response_model=List[Campaign])
async def get_campaigns(current_user: User = Depends(get_current_user)):
    campaigns = await db.campaigns.find({"user_id": current_user.id}).sort("created_at", -1).to_list(length=None)
    return [Campaign(**parse_from_mongo(campaign)) for campaign in campaigns]

@api_router.get("/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return Campaign(**parse_from_mongo(campaign))

@api_router.put("/campaigns/{campaign_id}", response_model=Campaign)
async def update_campaign(campaign_id: str, campaign_data: CampaignUpdate, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_data = {k: v for k, v in campaign_data.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.campaigns.update_one(
        {"id": campaign_id, "user_id": current_user.id},
        {"$set": prepare_for_mongo(update_data)}
    )
    
    updated_campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    return Campaign(**parse_from_mongo(updated_campaign))

@api_router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    result = await db.campaigns.delete_one({"id": campaign_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"message": "Campaign deleted successfully"}

@api_router.post("/campaigns/{campaign_id}/preview")
async def preview_campaign_personalization(
    campaign_id: str, 
    preview_request: VariablePreviewRequest, 
    current_user: User = Depends(get_current_user)
):
    """Preview how a template will look with personalized variables for a specific contact"""
    
    # Get contact
    contact = await db.contacts.find_one({
        "id": preview_request.contact_id, 
        "user_id": current_user.id
    })
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Get campaign for custom variables
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    custom_variables = campaign.get("custom_variables", {}) if campaign else {}
    
    # Personalize template
    personalized = personalize_template(
        preview_request.template, 
        parse_from_mongo(contact),
        custom_variables
    )
    
    # Extract variables used
    variables_found = extract_variables_from_template(preview_request.template)
    
    return {
        "original_template": preview_request.template,
        "personalized_content": personalized,
        "contact": {
            "name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
            "email": contact.get("email", ""),
            "company": contact.get("company", "")
        },
        "variables_used": variables_found
    }

@api_router.post("/campaigns/{campaign_id}/validate")
async def validate_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    """Validate campaign setup and variables"""
    
    # Get campaign
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_obj = Campaign(**parse_from_mongo(campaign))
    
    # Get contacts
    contacts = []
    if campaign_obj.contact_ids:
        contacts_cursor = db.contacts.find({
            "id": {"$in": campaign_obj.contact_ids},
            "user_id": current_user.id
        })
        contacts = await contacts_cursor.to_list(length=None)
        contacts = [parse_from_mongo(c) for c in contacts]
    
    # Validate variables
    validation_result = validate_campaign_variables(campaign_obj, contacts)
    
    # Check SMTP configurations
    smtp_issues = []
    if campaign_obj.smtp_config_ids:
        smtp_count = await db.smtp_configs.count_documents({
            "id": {"$in": campaign_obj.smtp_config_ids},
            "user_id": current_user.id,
            "is_active": True
        })
        if smtp_count == 0:
            smtp_issues.append("No active SMTP configurations found")
        elif smtp_count < len(campaign_obj.smtp_config_ids):
            smtp_issues.append("Some SMTP configurations are inactive or not found")
    else:
        smtp_issues.append("No SMTP configurations selected")
    
    # Check if campaign has steps
    setup_issues = []
    if not campaign_obj.steps:
        setup_issues.append("Campaign has no email steps configured")
    else:
        for i, step in enumerate(campaign_obj.steps):
            if not step.variations:
                setup_issues.append(f"Step {i+1} has no email variations")
            for j, variation in enumerate(step.variations):
                if not variation.subject.strip():
                    setup_issues.append(f"Step {i+1}, Variation {j+1} has no subject")
                if not variation.content.strip():
                    setup_issues.append(f"Step {i+1}, Variation {j+1} has no content")
    
    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign["name"],
        "is_valid": validation_result["valid"] and len(smtp_issues) == 0 and len(setup_issues) == 0,
        "contacts_count": len(contacts),
        "steps_count": len(campaign_obj.steps),
        "variable_validation": validation_result,
        "smtp_issues": smtp_issues,
        "setup_issues": setup_issues
    }

@api_router.post("/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    """Start campaign sending"""
    
    # Validate campaign first
    validation_response = await validate_campaign(campaign_id, current_user)
    if not validation_response["is_valid"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Campaign validation failed: {validation_response}"
        )
    
    # Update campaign status
    await db.campaigns.update_one(
        {"id": campaign_id, "user_id": current_user.id},
        {
            "$set": {
                "status": CampaignStatus.SENDING.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Campaign started successfully", "status": "sending"}

@api_router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    """Pause campaign sending"""
    
    await db.campaigns.update_one(
        {"id": campaign_id, "user_id": current_user.id},
        {
            "$set": {
                "status": CampaignStatus.PAUSED.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Campaign paused successfully", "status": "paused"}

@api_router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: str, current_user: User = Depends(get_current_user)):
    # Verify campaign belongs to user
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Enhanced analytics with A/B testing breakdown
    pipeline = [
        {"$match": {"campaign_id": campaign_id}},
        {"$group": {
            "_id": {
                "step_id": "$campaign_step_id",
                "variation_id": "$variation_id",
                "variation_name": "$variation_name"
            },
            "total_sent": {"$sum": 1},
            "delivered": {"$sum": {"$cond": [{"$ne": ["$delivered_at", None]}, 1, 0]}},
            "opened": {"$sum": {"$cond": [{"$ne": ["$opened_at", None]}, 1, 0]}},
            "clicked": {"$sum": {"$cond": [{"$ne": ["$clicked_at", None]}, 1, 0]}},
            "replied": {"$sum": {"$cond": [{"$ne": ["$replied_at", None]}, 1, 0]}},
            "bounced": {"$sum": {"$cond": [{"$ne": ["$bounced_at", None]}, 1, 0]}}
        }}
    ]
    
    variation_stats = await db.email_tracking.aggregate(pipeline).to_list(length=None)
    
    # Overall stats
    total_stats = {
        "campaign_id": campaign_id,
        "campaign_name": campaign["name"],
        "status": campaign.get("status", "draft"),
        "total_emails": 0,
        "delivered_emails": 0,
        "opened_emails": 0,
        "clicked_emails": 0,
        "replied_emails": 0,
        "bounced_emails": 0
    }
    
    # Aggregate totals
    for stat in variation_stats:
        total_stats["total_emails"] += stat["total_sent"]
        total_stats["delivered_emails"] += stat["delivered"]
        total_stats["opened_emails"] += stat["opened"]
        total_stats["clicked_emails"] += stat["clicked"]
        total_stats["replied_emails"] += stat["replied"]
        total_stats["bounced_emails"] += stat["bounced"]
    
    # Calculate rates
    sent = total_stats["total_emails"]
    if sent > 0:
        total_stats.update({
            "delivery_rate": round((total_stats["delivered_emails"] / sent * 100), 2),
            "open_rate": round((total_stats["opened_emails"] / sent * 100), 2),
            "click_rate": round((total_stats["clicked_emails"] / sent * 100), 2),
            "reply_rate": round((total_stats["replied_emails"] / sent * 100), 2),
            "bounce_rate": round((total_stats["bounced_emails"] / sent * 100), 2)
        })
    else:
        total_stats.update({
            "delivery_rate": 0, "open_rate": 0, "click_rate": 0, 
            "reply_rate": 0, "bounce_rate": 0
        })
    
    # A/B testing breakdown
    ab_breakdown = []
    for stat in variation_stats:
        variation_data = {
            "step_id": stat["_id"]["step_id"],
            "variation_id": stat["_id"]["variation_id"],
            "variation_name": stat["_id"]["variation_name"] or "Unknown",
            "sent": stat["total_sent"],
            "delivered": stat["delivered"],
            "opened": stat["opened"],
            "clicked": stat["clicked"],
            "replied": stat["replied"],
            "bounced": stat["bounced"]
        }
        
        # Calculate rates for this variation
        if stat["total_sent"] > 0:
            variation_data.update({
                "delivery_rate": round((stat["delivered"] / stat["total_sent"] * 100), 2),
                "open_rate": round((stat["opened"] / stat["total_sent"] * 100), 2),
                "click_rate": round((stat["clicked"] / stat["total_sent"] * 100), 2),
                "reply_rate": round((stat["replied"] / stat["total_sent"] * 100), 2),
                "bounce_rate": round((stat["bounced"] / stat["total_sent"] * 100), 2)
            })
        else:
            variation_data.update({
                "delivery_rate": 0, "open_rate": 0, "click_rate": 0,
                "reply_rate": 0, "bounce_rate": 0
            })
        
        ab_breakdown.append(variation_data)
    
    return {
        "overall": total_stats,
        "ab_testing": ab_breakdown,
        "steps_count": len(campaign.get("steps", [])),
        "variations_count": sum(len(step.get("variations", [])) for step in campaign.get("steps", []))
    }

# Template Management Routes
@api_router.get("/templates/variables")
async def get_available_variables(current_user: User = Depends(get_current_user)):
    """Get list of available variables for templates"""
    
    # Get sample contact to show available fields
    sample_contact = await db.contacts.find_one({"user_id": current_user.id})
    
    variables = {
        "standard": {
            "first_name": {"description": "Contact's first name", "example": "John"},
            "last_name": {"description": "Contact's last name", "example": "Doe"},
            "full_name": {"description": "Full name (first + last)", "example": "John Doe"},
            "email": {"description": "Contact's email address", "example": "john@example.com"},
            "company": {"description": "Contact's company", "example": "Acme Corp"},
            "phone": {"description": "Contact's phone number", "example": "555-1234"}
        },
        "usage": "Use variables in templates like: Hello {{first_name}}, Welcome to {{company}}!",
        "sample_data": {}
    }
    
    if sample_contact:
        variables["sample_data"] = {
            "first_name": sample_contact.get("first_name", "John"),
            "last_name": sample_contact.get("last_name", "Doe"),
            "full_name": f"{sample_contact.get('first_name', 'John')} {sample_contact.get('last_name', 'Doe')}",
            "email": sample_contact.get("email", "john@example.com"),
            "company": sample_contact.get("company", "Acme Corp"),
            "phone": sample_contact.get("phone", "555-1234")
        }
    
    return variables

@api_router.post("/templates/validate")
async def validate_template(template: str = "", current_user: User = Depends(get_current_user)):
    """Validate a template and show which variables are used"""
    
    variables_found = extract_variables_from_template(template)
    standard_variables = ["first_name", "last_name", "full_name", "email", "company", "phone"]
    
    valid_variables = [var for var in variables_found if var in standard_variables]
    invalid_variables = [var for var in variables_found if var not in standard_variables]
    
    return {
        "template": template,
        "is_valid": len(invalid_variables) == 0,
        "variables_found": variables_found,
        "valid_variables": valid_variables,
        "invalid_variables": invalid_variables,
        "suggestions": [f"Use {{{{{var}}}}} for {var.replace('_', ' ')}" for var in standard_variables if var not in variables_found]
    }

# Email Tracking Routes
@api_router.get("/track/pixel/{tracking_pixel_id}")
async def track_email_open(tracking_pixel_id: str):
    """Track email opens via 1x1 pixel"""
    # Update tracking record
    await db.email_tracking.update_one(
        {"tracking_pixel_id": tracking_pixel_id, "opened_at": {"$exists": False}},
        {"$set": {"opened_at": datetime.now(timezone.utc), "status": "opened"}}
    )
    
    # Return 1x1 transparent pixel
    pixel_data = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b'
    return Response(content=pixel_data, media_type="image/gif")

@api_router.get("/track/click/{tracking_pixel_id}")
async def track_email_click(tracking_pixel_id: str, url: str = Query(...)):
    """Track email clicks and redirect"""
    # Update tracking record
    await db.email_tracking.update_one(
        {"tracking_pixel_id": tracking_pixel_id},
        {
            "$set": {"clicked_at": datetime.now(timezone.utc), "status": "clicked"},
            "$push": {"click_links": url}
        }
    )
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url)

# Subscription Routes
@api_router.get("/subscription/plans")
async def get_subscription_plans():
    """Get available subscription plans"""
    return {"plans": SUBSCRIPTION_PLANS}

@api_router.post("/subscription/checkout")
async def create_subscription_checkout(
    subscription_request: SubscriptionRequest, 
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Create Stripe checkout session for subscription"""
    plan = subscription_request.plan
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")
    
    plan_details = SUBSCRIPTION_PLANS[plan]
    if plan == "free":
        raise HTTPException(status_code=400, detail="Free plan doesn't require payment")
    
    try:
        # Initialize Stripe
        host_url = subscription_request.origin_url
        webhook_url = f"{host_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        
        # Create checkout session
        success_url = f"{host_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{host_url}/subscription/cancel"
        
        checkout_request = CheckoutSessionRequest(
            amount=plan_details["price"],
            currency="usd",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": current_user.id,
                "plan": plan,
                "user_email": current_user.email
            }
        )
        
        session = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record
        payment_transaction = PaymentTransaction(
            user_id=current_user.id,
            session_id=session.session_id,
            amount=plan_details["price"],
            currency="usd",
            plan=plan,
            metadata=checkout_request.metadata
        )
        
        payment_mongo = prepare_for_mongo(payment_transaction.dict())
        await db.payment_transactions.insert_one(payment_mongo)
        
        return {"url": session.url, "session_id": session.session_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating checkout session: {str(e)}")

@api_router.get("/subscription/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, current_user: User = Depends(get_current_user)):
    """Get checkout session status"""
    try:
        # Initialize Stripe
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        
        # Get checkout status
        checkout_status = await stripe_checkout.get_checkout_status(session_id)
        
        # Update payment transaction
        payment_transaction = await db.payment_transactions.find_one({
            "session_id": session_id,
            "user_id": current_user.id
        })
        
        if payment_transaction and checkout_status.payment_status == "paid":
            # Update payment status
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": "paid",
                        "payment_status": "paid",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            # Update user subscription (only if not already processed)
            if payment_transaction["status"] != "paid":
                plan = payment_transaction["plan"]
                expires_at = datetime.now(timezone.utc) + timedelta(days=30)  # 30-day subscription
                
                await db.users.update_one(
                    {"id": current_user.id},
                    {
                        "$set": {
                            "subscription_plan": plan,
                            "subscription_status": "active",
                            "subscription_expires_at": expires_at.isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
        
        return {
            "status": checkout_status.status,
            "payment_status": checkout_status.payment_status,
            "amount_total": checkout_status.amount_total,
            "currency": checkout_status.currency
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking payment status: {str(e)}")

# Webhook Routes
@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature", "")
        
        # Initialize Stripe
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        
        # Handle webhook
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Process the webhook event
        if webhook_response.event_type == "checkout.session.completed":
            session_id = webhook_response.session_id
            payment_status = webhook_response.payment_status
            metadata = webhook_response.metadata
            
            if payment_status == "paid" and metadata:
                user_id = metadata.get("user_id")
                plan = metadata.get("plan")
                
                # Update payment transaction
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {
                        "$set": {
                            "status": "paid",
                            "payment_status": "paid",
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                
                # Update user subscription
                if user_id and plan:
                    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
                    await db.users.update_one(
                        {"id": user_id},
                        {
                            "$set": {
                                "subscription_plan": plan,
                                "subscription_status": "active",
                                "subscription_expires_at": expires_at.isoformat(),
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            }
                        }
                    )
        
        return {"status": "success"}
        
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

# Enhanced Dashboard Stats
@api_router.get("/stats/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    # Get user-specific stats
    total_contacts = await db.contacts.count_documents({"user_id": current_user.id})
    total_campaigns = await db.campaigns.count_documents({"user_id": current_user.id})
    
    # Recent contacts (last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_contacts = await db.contacts.count_documents({
        "user_id": current_user.id,
        "created_at": {"$gte": seven_days_ago.isoformat()}
    })
    
    # Active campaigns
    active_campaigns = await db.campaigns.count_documents({
        "user_id": current_user.id,
        "status": {"$in": ["sending", "scheduled"]}
    })
    
    # Email stats
    total_emails_sent = await db.email_tracking.count_documents({
        "campaign_id": {"$in": [c["id"] for c in await db.campaigns.find({"user_id": current_user.id}, {"id": 1}).to_list(length=None)]}
    })
    
    total_opens = await db.email_tracking.count_documents({
        "campaign_id": {"$in": [c["id"] for c in await db.campaigns.find({"user_id": current_user.id}, {"id": 1}).to_list(length=None)]},
        "opened_at": {"$exists": True}
    })
    
    overall_open_rate = round((total_opens / total_emails_sent * 100) if total_emails_sent > 0 else 0, 2)
    
    # Subscription info
    plan_details = SUBSCRIPTION_PLANS.get(current_user.subscription_plan, SUBSCRIPTION_PLANS["free"])
    
    return {
        "total_contacts": total_contacts,
        "total_campaigns": total_campaigns,
        "recent_contacts": recent_contacts,
        "active_campaigns": active_campaigns,
        "total_emails_sent": total_emails_sent,
        "overall_open_rate": overall_open_rate,
        "subscription": {
            "plan": current_user.subscription_plan,
            "plan_name": plan_details["name"],
            "status": current_user.subscription_status,
            "expires_at": current_user.subscription_expires_at,
            "limits": {
                "contacts": {
                    "used": total_contacts,
                    "limit": plan_details["contacts_limit"]
                },
                "campaigns": {
                    "used": total_campaigns,
                    "limit": plan_details["campaigns_limit"]
                },
                "emails_per_day": plan_details["emails_per_day"],
                "inboxes": plan_details["inboxes_limit"]
            }
        }
    }

# Root route
@api_router.get("/")
async def root():
    return {"message": "MailerPro API - Email Outreach Platform with Subscriptions"}

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