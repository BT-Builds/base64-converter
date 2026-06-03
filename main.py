import base64
import re
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import hashlib
import time

app = FastAPI(
    title="Base64 Converter API",
    description="Encode and decode Base64 strings with validation",
    version="1.0.0"
)

# Simple in-memory rate limiting
rate_limit_store = {}

def rate_limit(api_key: str = ""):
    if not api_key:
        api_key = "anonymous"
    key = f"{api_key}:{int(time.time() / 60)}"
    rate_limit_store[key] = rate_limit_store.get(key, 0) + 1
    if rate_limit_store[key] > 100:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return api_key

def verify_api_key(api_key: str = ""):
    if rate_limit(api_key):
        return api_key

@app.get("/health")
def health():
    return {"status": "ok"}

class EncodeRequest(BaseModel):
    text: str = Field(..., description="Text to encode")
    encoding: Optional[str] = Field("utf-8", description="Text encoding (default: utf-8)")

class DecodeRequest(BaseModel):
    base64_string: str = Field(..., description="Base64 string to decode")
    encoding: Optional[str] = Field("utf-8", description="Output encoding (default: utf-8)")

class EncodeResponse(BaseModel):
    original: str
    encoded: str
    encoding: str

class DecodeResponse(BaseModel):
    original: str
    decoded: str
    encoding: str

@app.post("/encode")
def encode(req: EncodeRequest, api_key: str = Depends(verify_api_key)):
    try:
        encoded = base64.b64encode(req.text.encode(req.encoding)).decode('utf-8')
        return EncodeResponse(original=req.text, encoded=encoded, encoding=req.encoding)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Encoding failed: {str(e)}")

@app.post("/decode")
def decode(req: DecodeRequest, api_key: str = Depends(verify_api_key)):
    try:
        # Remove any whitespace/newlines
        clean_b64 = req.base64_string.strip().replace('\n', '').replace('\r', '')
        decoded = base64.b64decode(clean_b64).decode(req.encoding)
        return DecodeResponse(original=req.base64_string, decoded=decoded, encoding=req.encoding)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Decoding failed: {str(e)}")

@app.post("/validate")
def validate(req: DecodeRequest, api_key: str = Depends(verify_api_key)):
    try:
        clean_b64 = req.base64_string.strip().replace('\n', '').replace('\r', '')
        # Check if valid base64
        base64.b64decode(clean_b64)
        return {"valid": True, "message": "Valid Base64 string"}
    except Exception as e:
        return {"valid": False, "message": f"Invalid Base64: {str(e)}"}

@app.post("/info")
def info(req: DecodeRequest, api_key: str = Depends(verify_api_key)):
    """Get info about a Base64 string without decoding"""
    clean_b64 = req.base64_string.strip().replace('\n', '').replace('\r', '')
    info = {
        "length": len(clean_b64),
        "padding_chars": clean_b64.count('='),
        "alphanumeric_ratio": len(re.findall(r'[A-Za-z0-9]', clean_b64)) / len(clean_b64) if clean_b64 else 0
    }
    try:
        decoded_bytes = base64.b64decode(clean_b64)
        info["decoded_length"] = len(decoded_bytes)
        info["valid"] = True
    except:
        info["valid"] = False
    return info

@app.get("/encode/{text:path}")
def encode_get(text: str, api_key: str = Depends(verify_api_key)):
    encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    return {"original": text, "encoded": encoded}

try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    pass
