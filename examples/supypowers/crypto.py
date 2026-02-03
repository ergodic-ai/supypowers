# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
"""
crypto.py - Encoding, hashing, and ID generation

Run with:
  supypowers run crypto:hash '{"text": "hello", "algorithm": "sha256"}'
  supypowers run crypto:base64_encode '{"text": "hello world"}'
  supypowers run crypto:uuid '{}'
"""
import base64
import hashlib
import uuid as uuid_lib
from typing import Optional
from pydantic import BaseModel, Field


class HashInput(BaseModel):
    text: str = Field(..., description="Text to hash")
    algorithm: str = Field(default="sha256", description="Hash algorithm: md5, sha1, sha256, sha512")


class HashOutput(BaseModel):
    success: bool
    hash: Optional[str] = None
    algorithm: Optional[str] = None
    error: Optional[str] = None


def hash(input: HashInput) -> HashOutput:
    """Generate a hash of the input text."""
    try:
        algo = input.algorithm.lower()
        if algo == "md5":
            h = hashlib.md5(input.text.encode()).hexdigest()
        elif algo == "sha1":
            h = hashlib.sha1(input.text.encode()).hexdigest()
        elif algo == "sha256":
            h = hashlib.sha256(input.text.encode()).hexdigest()
        elif algo == "sha512":
            h = hashlib.sha512(input.text.encode()).hexdigest()
        else:
            return HashOutput(success=False, error=f"Unknown algorithm: {algo}")
        
        return HashOutput(success=True, hash=h, algorithm=algo)
    except Exception as e:
        return HashOutput(success=False, error=str(e))


class Base64Input(BaseModel):
    text: str = Field(..., description="Text to encode/decode")


class Base64Output(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None


def base64_encode(input: Base64Input) -> Base64Output:
    """Encode text to base64."""
    try:
        result = base64.b64encode(input.text.encode()).decode()
        return Base64Output(success=True, result=result)
    except Exception as e:
        return Base64Output(success=False, error=str(e))


def base64_decode(input: Base64Input) -> Base64Output:
    """Decode base64 to text."""
    try:
        result = base64.b64decode(input.text).decode()
        return Base64Output(success=True, result=result)
    except Exception as e:
        return Base64Output(success=False, error=str(e))


class UuidInput(BaseModel):
    version: int = Field(default=4, description="UUID version: 1 (time-based) or 4 (random)")


class UuidOutput(BaseModel):
    success: bool
    uuid: Optional[str] = None
    error: Optional[str] = None


def uuid(input: UuidInput) -> UuidOutput:
    """Generate a UUID."""
    try:
        if input.version == 1:
            u = str(uuid_lib.uuid1())
        elif input.version == 4:
            u = str(uuid_lib.uuid4())
        else:
            return UuidOutput(success=False, error=f"Unsupported UUID version: {input.version}")
        
        return UuidOutput(success=True, uuid=u)
    except Exception as e:
        return UuidOutput(success=False, error=str(e))
