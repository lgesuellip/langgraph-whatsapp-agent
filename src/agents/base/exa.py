from langchain.tools import tool
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import os
import requests

class ExaBaseSearch(BaseModel):
    """Base schema for Exa search parameters."""
    query: str = Field(..., description="Search query")
    num_results: Optional[int] = Field(5, description="Number of results to return (default: 5)")
    max_characters: Optional[int] = Field(3000, description="Maximum number of characters to return for each result's text content (Default: 3000)")

class ResearchPaperSearch(ExaBaseSearch):
    """Schema for research paper search parameters."""
    query: str = Field(..., description="Research topic or keyword to search for")

class WebSearchExa(ExaBaseSearch):
    """Schema for web search parameters."""
    pass

def _call_exa_api(
    payload: ExaBaseSearch,
    search_type: Literal["research", "web"] = "web"
) -> Dict[Any, Any]:
    """
    Helper function to call the Exa API.
    
    Args:
        payload: The validated search parameters
        search_type: The type of search to perform ("research" or "web")
        
    Returns:
        Dictionary containing search results from Exa AI
    """
    # Get API key from environment
    exa_api_key = os.getenv("EXA_API_KEY")
    if not exa_api_key:
        return {
            "status": "failed",
            "message": "EXA_API_KEY environment variable is not set",
            "results": []
        }
        
    # Prepare request
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": exa_api_key
    }
    
    search_request = {
        "query": payload.query,
        "type": "auto",
        "numResults": payload.num_results,
        "contents": {
            "text": {
                "maxCharacters": payload.max_characters
            },
            "livecrawl": "always" if search_type == "web" else "fallback"
        }
    }
    
    # Add category for research papers
    if search_type == "research":
        search_request["category"] = "research paper"
    
    try:
        # Send request to Exa API
        response = requests.post(
            "https://api.exa.ai/search",
            headers=headers,
            json=search_request,
            timeout=25
        )
        
        # Handle response
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        if not data or "results" not in data or not data["results"]:
            result_type = "research papers" if search_type == "research" else "search results"
            return {
                "status": "success",
                "message": f"No {result_type} found. Please try a different query.",
                "results": []
            }
            
        result_type = "research papers" if search_type == "research" else "web search results"
        return {
            "status": "success",
            "message": f"Found {len(data['results'])} {result_type}",
            "results": data["results"]
        }
        
    except requests.exceptions.RequestException as e:
        # Handle request errors
        status_code = e.response.status_code if hasattr(e, 'response') and e.response else 'unknown'
        error_message = e.response.text if hasattr(e, 'response') and e.response else str(e)
        
        error_type = "Research paper search" if search_type == "research" else "Web search"
        return {
            "status": "failed",
            "message": f"{error_type} error ({status_code}): {error_message}",
            "results": []
        }
    except Exception as e:
        error_type = "Research paper search" if search_type == "research" else "Web search"
        return {
            "status": "failed",
            "message": f"{error_type} error: {str(e)}",
            "results": []
        }

@tool
def search_research_papers(
    query: str,
    num_results: Optional[int] = 5,
    max_characters: Optional[int] = 3000
) -> Dict[Any, Any]:
    """
    Search across 100M+ research papers with full text access using Exa AI.
    
    This tool performs targeted academic paper searches with deep research content coverage.
    Returns detailed information about relevant academic papers including titles, authors,
    publication dates, and full text excerpts.
    
    Args:
        query: Research topic or keyword to search for
        num_results: Number of research papers to return (default: 5)
        max_characters: Maximum number of characters to return for each result's text content (Default: 3000)
    
    Returns:
        Dictionary containing research paper results from Exa AI
    
    Raises:
        Exception: If the search fails
    """
    # Validate data with Pydantic model
    payload = ResearchPaperSearch(
        query=query,
        num_results=num_results,
        max_characters=max_characters
    )
    
    return _call_exa_api(payload, search_type="research")

@tool
def web_search_exa(
    query: str,
    num_results: Optional[int] = 5,
    max_characters: Optional[int] = 3000
) -> Dict[Any, Any]:
    """
    Search the web using Exa AI - performs real-time web searches and can scrape content from specific URLs.
    
    Supports configurable result counts and returns the content from the most relevant websites.
    
    Args:
        query: Search query
        num_results: Number of search results to return (default: 5)
        max_characters: Maximum number of characters to return for each result's text content (Default: 3000)
    
    Returns:
        Dictionary containing web search results from Exa AI
    
    Raises:
        Exception: If the search fails
    """
    # Validate data with Pydantic model
    payload = WebSearchExa(
        query=query,
        num_results=num_results,
        max_characters=max_characters
    )
    
    return _call_exa_api(payload, search_type="web")

# Export the tools
EXA_TOOLS = [
    search_research_papers,
    web_search_exa
] 