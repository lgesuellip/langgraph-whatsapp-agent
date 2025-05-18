from langchain.tools import tool
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import os

# Try to import Weaviate, but make it optional
try:
    import weaviate
    from weaviate.auth import Auth
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

class Memory(BaseModel):
    """Schema for universal memory operations."""
    content: str = Field(..., description="The memory content to store")
    id: Optional[str] = Field(None, description="Optional ID for the memory")
    metadata: Optional[Dict[str, Any]] = Field({}, description="Optional metadata for the memory")

class MemoryStore:
    """Universal memory store that can work with different backends."""
    
    @staticmethod
    def get_store(store_type="weaviate"):
        """Factory method to get the appropriate store."""
        if store_type == "weaviate":
            if not WEAVIATE_AVAILABLE:
                raise ImportError("Weaviate is not installed. Install with 'pip install weaviate-client'")
            return WeaviateStore()
        elif store_type == "in_memory":
            return InMemoryStore()
        else:
            raise ValueError(f"Unknown store type: {store_type}")

class WeaviateStore:
    """Weaviate implementation of memory store."""
    
    def __init__(self):
        self.collection_name = "Memories"
    
    def _get_client(self):
        """Get Weaviate client."""
        if not WEAVIATE_AVAILABLE:
            raise ImportError("Weaviate is not installed")
            
        weaviate_url = os.environ.get("WEAVIATE_URL")
        weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")
        
        if not weaviate_url or not weaviate_api_key:
            raise ValueError("WEAVIATE_URL or WEAVIATE_API_KEY environment variables are not set")
            
        return weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
        )
    
    def add(self, memory: Memory) -> Dict[str, Any]:
        """Add memory to Weaviate."""
        try:
            client = self._get_client()
            memories_collection = client.collections.get(self.collection_name)
            
            memory_object = {"memory": memory.content}
            # Add metadata if provided
            for key, value in memory.metadata.items():
                memory_object[key] = value
                
            if memory.id:
                result = memories_collection.data.insert(memory_object, uuid=memory.id)
            else:
                result = memories_collection.data.insert(memory_object)
                
            client.close()
            return {"status": "success", "id": result}
            
        except Exception as e:
            if 'client' in locals():
                client.close()
            return {"status": "error", "message": str(e)}
    
    def get_all(self) -> Dict[str, Any]:
        """Get all memories from Weaviate."""
        try:
            client = self._get_client()
            memories_collection = client.collections.get(self.collection_name)
            
            memories = []
            for item in memories_collection.iterator():
                memory_data = {
                    "id": item.uuid,
                    "content": item.properties.get("memory", "")
                }
                # Add any other properties as metadata
                memory_data["metadata"] = {k: v for k, v in item.properties.items() if k != "memory"}
                memories.append(memory_data)
                
            client.close()
            return {"status": "success", "memories": memories}
            
        except Exception as e:
            if 'client' in locals():
                client.close()
            return {"status": "error", "message": str(e), "memories": []}

class InMemoryStore:
    """Simple in-memory implementation for testing or simple use cases."""
    
    def __init__(self):
        self.memories = []
        self.next_id = 1
    
    def add(self, memory: Memory) -> Dict[str, Any]:
        """Add memory to in-memory store."""
        try:
            memory_id = memory.id if memory.id else f"mem_{self.next_id}"
            self.next_id += 1
            
            memory_obj = {
                "id": memory_id,
                "content": memory.content,
                "metadata": memory.metadata
            }
            
            self.memories.append(memory_obj)
            return {"status": "success", "id": memory_id}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_all(self) -> Dict[str, Any]:
        """Get all memories from in-memory store."""
        try:
            return {"status": "success", "memories": self.memories}
        except Exception as e:
            return {"status": "error", "message": str(e), "memories": []}

@tool
def add_memory(
    content: str,
    id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    store_type: str = "weaviate"
) -> Dict[str, Any]:
    """
    Add a memory to the universal memory store.
    
    Args:
        content: The memory content to store
        id: Optional ID for the memory
        metadata: Optional metadata for the memory
        store_type: The type of store to use (weaviate, in_memory)
        
    Returns:
        Dictionary containing the status of the operation
    """
    try:
        memory = Memory(
            content=content,
            id=id,
            metadata=metadata or {}
        )
        
        store = MemoryStore.get_store(store_type)
        return store.add(memory)
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@tool
def get_memories(store_type: str = "weaviate") -> Dict[str, Any]:
    """
    Get all memories from the universal memory store.
    
    Args:
        store_type: The type of store to use (weaviate, in_memory)
        
    Returns:
        Dictionary containing the memories
    """
    try:
        store = MemoryStore.get_store(store_type)
        return store.get_all()
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "memories": []
        }

# Export the tools
MEMORY_TOOLS = [
    add_memory,
    get_memories
]