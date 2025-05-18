from langchain.tools import tool
from typing import Dict, Any
from pydantic import BaseModel
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex

class EducationQuery(BaseModel):
    """Schema for education knowledge base query."""
    query: str
@tool
def query_education_knowledge_base(
    query: str
) -> Dict[Any, Any]:
    """
    Query the education knowledge base using LlamaIndex.
    Args:
        query: The question or query about educational data
    Returns:
        Dictionary containing the response from the knowledge base
    Raises:
        Exception: If the query fails
    """
    try:
        # Validate data with Pydantic model
        payload = EducationQuery(
            query=query
        )
        # Connect to the existing index
        index = LlamaCloudIndex("education_index", project_name="Default")
        # Create query engine and execute query
        query_engine = index.as_query_engine()
        response = query_engine.query(payload.query)
        # Return just the response
        return str(response)
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed",
            "message": "Failed to query education knowledge base"
        }

RAG_TOOLS = [
    query_education_knowledge_base,
]