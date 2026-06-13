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
# === BT Builds Standard Middleware (auto-injected) ===
from fastapi.middleware.cors import CORSMiddleware as _BTCors
app.add_middleware(_BTCors, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], expose_headers=["X-RateLimit-Limit","X-RateLimit-Remaining","X-RateLimit-Reset"])

@app.middleware("http")
async def _bt_add_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Powered-By"] = "btbuilds"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


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

# === Helper functions for single-item processing (reused by bulk endpoints) ===
def _encode_single(text: str, encoding: str = "utf-8"):
    """Single encode logic - reused by bulk endpoint"""
    try:
        encoded = base64.b64encode(text.encode(encoding)).decode('utf-8')
        return {"output": {"original": text, "encoded": encoded, "encoding": encoding}, "error": None}
    except Exception as e:
        return {"output": None, "error": f"Encoding failed: {str(e)}"}

def _decode_single(base64_string: str, encoding: str = "utf-8"):
    """Single decode logic - reused by bulk endpoint"""
    try:
        clean_b64 = base64_string.strip().replace('\n', '').replace('\r', '')
        decoded = base64.b64decode(clean_b64).decode(encoding)
        return {"output": {"original": base64_string, "decoded": decoded, "encoding": encoding}, "error": None}
    except Exception as e:
        return {"output": None, "error": f"Decoding failed: {str(e)}"}

def _validate_single(base64_string: str):
    """Single validate logic - reused by bulk endpoint"""
    try:
        clean_b64 = base64_string.strip().replace('\n', '').replace('\r', '')
        base64.b64decode(clean_b64)
        return {"output": {"valid": True, "message": "Valid Base64 string"}, "error": None}
    except Exception as e:
        return {"output": {"valid": False, "message": f"Invalid Base64: {str(e)}"}, "error": None}

def _info_single(base64_string: str):
    """Single info logic - reused by bulk endpoint"""
    clean_b64 = base64_string.strip().replace('\n', '').replace('\r', '')
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
    return {"output": info, "error": None}


@app.post("/encode")
def encode(req: EncodeRequest, api_key: str = Depends(verify_api_key)):
    result = _encode_single(req.text, req.encoding)
    if result["error"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result["output"]

@app.post("/decode")
def decode(req: DecodeRequest, api_key: str = Depends(verify_api_key)):
    result = _decode_single(req.base64_string, req.encoding)
    if result["error"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result["output"]

@app.post("/validate")
def validate(req: DecodeRequest, api_key: str = Depends(verify_api_key)):
    result = _validate_single(req.base64_string)
    return result["output"]

@app.post("/info")
def info(req: DecodeRequest, api_key: str = Depends(verify_api_key)):
    """Get info about a Base64 string without decoding"""
    result = _info_single(req.base64_string)
    return result["output"]

# === Bulk Request Models ===
class BulkEncodeRequest(BaseModel):
    items: list[str] = Field(..., description="List of texts to encode")
    encoding: Optional[str] = Field("utf-8", description="Text encoding (default: utf-8)")

class BulkDecodeRequest(BaseModel):
    items: list[str] = Field(..., description="List of Base64 strings to decode")
    encoding: Optional[str] = Field("utf-8", description="Output encoding (default: utf-8)")

class BulkValidateRequest(BaseModel):
    items: list[str] = Field(..., description="List of Base64 strings to validate")

class BulkInfoRequest(BaseModel):
    items: list[str] = Field(..., description="List of Base64 strings to analyze")

class BulkResponse(BaseModel):
    results: list
    total: int
    successful: int


# === Bulk Endpoints ===
@app.post("/bulk/encode")
def bulk_encode(req: BulkEncodeRequest, api_key: str = Depends(verify_api_key)):
    """Encode multiple strings to Base64 (max 1000 items)"""
    if len(req.items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")
    
    results = []
    successful = 0
    for item in req.items:
        result = _encode_single(item, req.encoding)
        if result["error"]:
            results.append({"input": item, "output": None, "error": result["error"]})
        else:
            results.append({"input": item, "output": result["output"], "error": None})
            successful += 1
    
    return {"results": results, "total": len(req.items), "successful": successful}

@app.post("/bulk/decode")
def bulk_decode(req: BulkDecodeRequest, api_key: str = Depends(verify_api_key)):
    """Decode multiple Base64 strings (max 1000 items)"""
    if len(req.items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")
    
    results = []
    successful = 0
    for item in req.items:
        result = _decode_single(item, req.encoding)
        if result["error"]:
            results.append({"input": item, "output": None, "error": result["error"]})
        else:
            results.append({"input": item, "output": result["output"], "error": None})
            successful += 1
    
    return {"results": results, "total": len(req.items), "successful": successful}

@app.post("/bulk/validate")
def bulk_validate(req: BulkValidateRequest, api_key: str = Depends(verify_api_key)):
    """Validate multiple Base64 strings (max 1000 items)"""
    if len(req.items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")
    
    results = []
    successful = 0
    for item in req.items:
        result = _validate_single(item)
        results.append({"input": item, "output": result["output"], "error": result["error"]})
        if result["output"]["valid"]:
            successful += 1
    
    return {"results": results, "total": len(req.items), "successful": successful}

@app.post("/bulk/info")
def bulk_info(req: BulkInfoRequest, api_key: str = Depends(verify_api_key)):
    """Get info about multiple Base64 strings (max 1000 items)"""
    if len(req.items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")
    
    results = []
    successful = 0
    for item in req.items:
        result = _info_single(item)
        results.append({"input": item, "output": result["output"], "error": result["error"]})
        if result["output"]["valid"]:
            successful += 1
    
    return {"results": results, "total": len(req.items), "successful": successful}

@app.get("/encode/{text:path}")
def encode_get(text: str, api_key: str = Depends(verify_api_key)):
    encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    return {"original": text, "encoded": encoded}

try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    pass