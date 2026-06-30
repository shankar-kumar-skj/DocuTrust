from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from jose import jwt
import bcrypt
import os
import secrets  # <-- added
from backend.database.mongodb import get_db
from backend.models.user import UserCreate, UserRole

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- JWT Secret with fallback ---
SECRET = os.getenv("JWT_SECRET")
if not SECRET:
    SECRET = secrets.token_urlsafe(32)
    print("⚠️  WARNING: JWT_SECRET not set, using randomly generated one. Tokens will be invalid after restart.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        role = payload.get("role")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id, "tenant_id": tenant_id, "role": role}
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- Register, Login, Logout endpoints (unchanged, but using datetime.now(timezone.utc)) ---

@router.post("/register")
async def register(user_data: UserCreate):
    db = get_db()
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(user_data.password)
    user_dict = {
        "email": user_data.email,
        "password_hash": hashed,
        "full_name": user_data.full_name,
        "role": user_data.role.value,
        "tenant_id": user_data.tenant_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await db.users.insert_one(user_dict)
    return {"message": "User registered", "id": str(result.inserted_id)}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    user = await db.users.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({
        "sub": str(user["_id"]),
        "tenant_id": user["tenant_id"],
        "role": user["role"]
    })
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "tenant_id": user["tenant_id"]}

@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    return {"message": "Logged out"}