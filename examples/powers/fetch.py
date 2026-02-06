# /// script
# dependencies = [
#   "pydantic",
#   "httpx",
# ]
# ///
"""
fetch.py - HTTP requests for agents

Run with:
  supypowers run fetch:get '{"url": "https://httpbin.org/get"}'
  supypowers run fetch:post '{"url": "https://httpbin.org/post", "json_body": {"key": "value"}}'
"""
from typing import Optional
from pydantic import BaseModel, Field
import httpx


class GetInput(BaseModel):
    url: str = Field(..., description="URL to fetch")
    headers: Optional[dict] = Field(default=None, description="Optional HTTP headers")
    timeout: int = Field(default=30, description="Timeout in seconds")


class HttpOutput(BaseModel):
    success: bool
    status_code: Optional[int] = None
    headers: Optional[dict] = None
    body: Optional[str] = None
    error: Optional[str] = None


def get(input: GetInput) -> HttpOutput:
    """Fetch a URL via HTTP GET."""
    try:
        resp = httpx.get(
            input.url,
            headers=input.headers or {},
            timeout=input.timeout,
            follow_redirects=True,
        )
        return HttpOutput(
            success=True,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            body=resp.text[:50000],  # Limit response size
        )
    except Exception as e:
        return HttpOutput(success=False, error=str(e))


class PostInput(BaseModel):
    url: str = Field(..., description="URL to post to")
    json_body: Optional[dict] = Field(default=None, description="JSON body to send")
    form_data: Optional[dict] = Field(default=None, description="Form data to send")
    headers: Optional[dict] = Field(default=None, description="Optional HTTP headers")
    timeout: int = Field(default=30, description="Timeout in seconds")


def post(input: PostInput) -> HttpOutput:
    """Send an HTTP POST request."""
    try:
        resp = httpx.post(
            input.url,
            json=input.json_body,
            data=input.form_data,
            headers=input.headers or {},
            timeout=input.timeout,
            follow_redirects=True,
        )
        return HttpOutput(
            success=True,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            body=resp.text[:50000],
        )
    except Exception as e:
        return HttpOutput(success=False, error=str(e))
