from langchain_core.tools import tool
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
import weaviate
from weaviate.auth import Auth
import os

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

class WeaviateMemory(BaseModel):
    """Schema for adding a memory to the Weaviate memories collection."""
    memory: str = Field(..., description="The memory string to add to the collection")
    uuid: Optional[str] = Field(None, description="Optional UUID for the memory object")
@tool
def add_memory_to_weaviate(
    memory: str,
    uuid: Optional[str] = None
) -> Dict[Any, Any]:
    """
    Add a memory to the Weaviate memories collection about students.
    Args:
        memory: The memory string to add
        uuid: Optional UUID for the memory object
    Returns:
        Dictionary containing the status of the operation
    Raises:
        Exception: If the operation fails
    """
    try:
        # Validate data with Pydantic model
        payload = WeaviateMemory(
            memory=memory,
            uuid=uuid
        )
        # Connect to Weaviate
        weaviate_url = os.environ.get("WEAVIATE_URL")
        weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")
        if not weaviate_url or not weaviate_api_key:
            return {
                "error": "Missing Weaviate credentials",
                "status": "failed",
                "message": "WEAVIATE_URL or WEAVIATE_API_KEY environment variables are not set"
            }
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
        )
        # Get the memories collection
        try:
            memories_collection = client.collections.get("Memories")
        except Exception as e:
            client.close()
            return {
                "error": str(e),
                "status": "failed",
                "message": "Failed to get 'memories' collection"
            }
        # Add the memory to the collection
        try:
            memory_object = {"memory": payload.memory}
            if payload.uuid:
                result = memories_collection.data.insert(memory_object, uuid=payload.uuid)
            else:
                result = memories_collection.data.insert(memory_object)
            client.close()  # Free up resources
            return {
                "status": "success",
                "message": "Memory added to collection",
                "uuid": result
            }
        except Exception as e:
            client.close()
            return {
                "error": str(e),
                "status": "failed",
                "message": "Failed to add memory to collection"
            }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed",
            "message": "Failed to add memory to Weaviate collection"
        }

@tool
def fetch_memories() -> dict:
    """
    Fetch memories from the Weaviate database.
    Returns:
        A dictionary with the status of the operation and the retrieved memories
    """
    try:
        # Get Weaviate credentials from environment variables
        weaviate_url = os.getenv("WEAVIATE_URL")
        weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
        if not weaviate_url or not weaviate_api_key:
            return {
                "status": "failed",
                "message": "Weaviate credentials not found in environment variables",
                "memories": []
            }
        # Connect to Weaviate
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
        )
        # Get the memories collection
        try:
            memories_collection = client.collections.get("Memories")
        except Exception as e:
            client.close()
            return {
                "error": str(e),
                "status": "failed",
                "message": "Failed to get 'Memories' collection",
                "memories": []
            }
        # Fetch memories from the collection
        try:
            memories = []
            # Use iterator to get all memories (default limit of 100)
            for item in memories_collection.iterator():
                memories.append({
                    "uuid": item.uuid,
                    "memory": item.properties.get("memory", ""),
                    # Remove created_time as it's not available in the object
                })
            client.close()  # Free up resources
            return {
                "status": "success",
                "message": f"Retrieved {len(memories)} memories",
                "memories": memories
            }
        except Exception as e:
            client.close()
            return {
                "error": str(e),
                "status": "failed",
                "message": "Failed to fetch memories from collection",
                "memories": []
            }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed",
            "message": "Failed to fetch memories from Weaviate collection",
            "memories": []
        }
    
MEMORY_TOOLS = [
    add_memory_to_weaviate,
    fetch_memories
]

RAG_TOOLS = [
    query_education_knowledge_base
]