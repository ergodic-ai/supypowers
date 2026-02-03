# /// script
# dependencies = [
#   "pydantic",
#   "httpx",
#   "beautifulsoup4",
# ]
# ///
"""
scrape.py - Web scraping utilities

Run with:
  supypowers run scrape:get_text '{"url": "https://example.com"}'
  supypowers run scrape:get_links '{"url": "https://example.com"}'
  supypowers run scrape:css_select '{"url": "https://example.com", "selector": "h1"}'
"""
from typing import Optional
from pydantic import BaseModel, Field
import httpx
from bs4 import BeautifulSoup


class UrlInput(BaseModel):
    url: str = Field(..., description="URL to scrape")
    timeout: int = Field(default=30, description="Timeout in seconds")


class GetTextOutput(BaseModel):
    success: bool
    title: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None


def get_text(input: UrlInput) -> GetTextOutput:
    """Fetch a URL and extract readable text content."""
    try:
        resp = httpx.get(input.url, timeout=input.timeout, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        title = soup.title.string if soup.title else None
        text = soup.get_text(separator="\n", strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)
        
        return GetTextOutput(
            success=True,
            title=title,
            text=text[:50000],  # Limit size
        )
    except Exception as e:
        return GetTextOutput(success=False, error=str(e))


class Link(BaseModel):
    text: str
    href: str


class GetLinksOutput(BaseModel):
    success: bool
    links: Optional[list[Link]] = None
    error: Optional[str] = None


def get_links(input: UrlInput) -> GetLinksOutput:
    """Extract all links from a webpage."""
    try:
        resp = httpx.get(input.url, timeout=input.timeout, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True) or href
            links.append(Link(text=text[:200], href=href))
            if len(links) >= 500:
                break
        
        return GetLinksOutput(success=True, links=links)
    except Exception as e:
        return GetLinksOutput(success=False, error=str(e))


class CssSelectInput(BaseModel):
    url: str = Field(..., description="URL to scrape")
    selector: str = Field(..., description="CSS selector")
    attribute: Optional[str] = Field(default=None, description="Extract this attribute instead of text")
    timeout: int = Field(default=30, description="Timeout in seconds")


class CssSelectOutput(BaseModel):
    success: bool
    results: Optional[list[str]] = None
    count: Optional[int] = None
    error: Optional[str] = None


def css_select(input: CssSelectInput) -> CssSelectOutput:
    """Select elements from a webpage using CSS selectors."""
    try:
        resp = httpx.get(input.url, timeout=input.timeout, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        elements = soup.select(input.selector)
        results = []
        for el in elements[:100]:  # Limit results
            if input.attribute:
                val = el.get(input.attribute, "")
            else:
                val = el.get_text(strip=True)
            results.append(val[:1000])
        
        return CssSelectOutput(success=True, results=results, count=len(results))
    except Exception as e:
        return CssSelectOutput(success=False, error=str(e))
