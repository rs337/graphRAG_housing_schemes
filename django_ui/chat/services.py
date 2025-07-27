"""
GraphRAG Service Layer
This module handles all GraphRAG API interactions for the Django chat application.
"""

import logging
import asyncio
import pandas as pd
from pathlib import Path
from typing import Tuple, Dict, Any
from django.conf import settings
from graphrag.config.load_config import load_config
import graphrag.api as api

# Set up logging
logger = logging.getLogger('chat')

class GraphRAGService:
    """
    Service class to handle GraphRAG operations.
    This replaces the lazy loading approach with direct initialization.
    """
    
    def __init__(self):
        """Initialize GraphRAG service with data loading."""
        self._data = None
        self._config = None
        
    def load_data(self) -> bool:
        """
        Load GraphRAG data files and configuration.
        Returns True if successful, False otherwise.
        """
        try:
            logger.info("Loading GraphRAG data and configuration...")
            
            # Load configuration
            config_path = Path(settings.GRAPHRAG_PROJECT_PATH)
            self._config = load_config(config_path)
            
            # Override model configuration with our fixed model
            if hasattr(self._config, 'llm_config'):
                self._config.llm_config.model = settings.GRAPHRAG_CONFIG['DEFAULT_MODEL']
            
            # Load all required parquet files
            output_path = settings.GRAPHRAG_OUTPUT_PATH
            
            self._data = {
                "entities": pd.read_parquet(f"{output_path}/entities.parquet"),
                "communities": pd.read_parquet(f"{output_path}/communities.parquet"),
                "community_reports": pd.read_parquet(f"{output_path}/community_reports.parquet"),
                "text_units": pd.read_parquet(f"{output_path}/text_units.parquet"),
                "relationships": pd.read_parquet(f"{output_path}/relationships.parquet"),
                "config": self._config
            }
            
            logger.info(f"GraphRAG data loaded successfully:")
            logger.info(f"  - Entities: {len(self._data['entities'])} records")
            logger.info(f"  - Communities: {len(self._data['communities'])} records")
            logger.info(f"  - Text Units: {len(self._data['text_units'])} records")
            logger.info(f"  - Relationships: {len(self._data['relationships'])} records")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading GraphRAG data: {str(e)}", exc_info=True)
            return False
    
    def is_ready(self) -> bool:
        """Check if the service is ready to handle queries."""
        return self._data is not None and self._config is not None
    
    async def search_with_timeout(self, search_func, **kwargs) -> Tuple[str, str]:
        """
        Wrapper to add timeout to search functions.
        Returns (response, context) tuple.
        """
        try:
            logger.info(f"Starting search with timeout: {settings.GRAPHRAG_CONFIG['SEARCH_TIMEOUT']}s")
            
            # Create search task
            search_task = asyncio.create_task(search_func(**kwargs))
            
            # Wait for completion with timeout
            response, context = await asyncio.wait_for(
                search_task, 
                timeout=settings.GRAPHRAG_CONFIG['SEARCH_TIMEOUT']
            )
            
            logger.info("Search completed successfully")
            return response, str(context)
            
        except asyncio.TimeoutError:
            error_msg = f"Search timed out after {settings.GRAPHRAG_CONFIG['SEARCH_TIMEOUT']} seconds"
            logger.error(error_msg)
            return error_msg, ""
            
        except Exception as e:
            error_msg = f"Search error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg, ""
    
    async def global_search(self, query: str) -> Tuple[str, str]:
        """
        Perform Global Search - analyzes entire knowledge base for broad insights.
        Best for: Complex questions requiring synthesis across multiple topics.
        """
        if not self.is_ready():
            return "GraphRAG service not initialized", ""
        
        logger.info(f"Performing Global Search for: {query}")
        
        search_params = {
            "config": self._data["config"],
            "query": query,
            "entities": self._data["entities"],
            "communities": self._data["communities"],
            "community_reports": self._data["community_reports"],
            "community_level": settings.GRAPHRAG_CONFIG['COMMUNITY_LEVEL'],
            "dynamic_community_selection": False,
            "response_type": settings.GRAPHRAG_CONFIG['RESPONSE_TYPE']
        }
        
        return await self.search_with_timeout(api.global_search, **search_params)
    
    async def local_search(self, query: str) -> Tuple[str, str]:
        """
        Perform Local Search - searches specific documents and passages.
        Best for: Finding detailed information in particular sections.
        """
        if not self.is_ready():
            return "GraphRAG service not initialized", ""
        
        logger.info(f"Performing Local Search for: {query}")
        
        search_params = {
            "config": self._data["config"],
            "query": query,
            "entities": self._data["entities"],
            "communities": self._data["communities"],
            "community_reports": self._data["community_reports"],
            "text_units": self._data["text_units"],
            "relationships": self._data["relationships"],
            "covariates": None,
            "community_level": settings.GRAPHRAG_CONFIG['COMMUNITY_LEVEL'],
            "response_type": settings.GRAPHRAG_CONFIG['RESPONSE_TYPE']
        }
        
        return await self.search_with_timeout(api.local_search, **search_params)
    
    async def basic_search(self, query: str) -> Tuple[str, str]:
        """
        Perform Basic Search - direct text matching in documents.
        Best for: Finding exact text matches and specific factual information.
        """
        if not self.is_ready():
            return "GraphRAG service not initialized", ""
        
        logger.info(f"Performing Basic Search for: {query}")
        
        search_params = {
            "config": self._data["config"],
            "query": query,
            "text_units": self._data["text_units"]
        }
        
        return await self.search_with_timeout(api.basic_search, **search_params)

# Global service instance
graphrag_service = GraphRAGService()

def format_response(response: str) -> str:
    """Format the response text for better readability in web interface."""
    if not response:
        return response
    
    import re
    
    # Clean up the response
    formatted = response.strip()
    
    # Convert bullet points to HTML-friendly format
    formatted = re.sub(r'^[•·\-\*]\s+', '• ', formatted, flags=re.MULTILINE)
    
    # Add proper spacing
    formatted = re.sub(r'\n\n+', '\n\n', formatted)
    
    # Bold important terms (you can customize this based on your domain)
    important_terms = [
        'Cost Rental', 'Housing Agency', 'Local Authority', 
        'Dublin', 'Ireland', 'Government', 'Citizen'
    ]
    
    for term in important_terms:
        formatted = re.sub(f'\\b({term})\\b', f'**{term}**', formatted, flags=re.IGNORECASE)
    
    return formatted

def format_context_data(context_data: str) -> str:
    """Format context data for display in web interface."""
    if not context_data or context_data.strip() == "":
        return "No context data available"
    
    # Limit context data length for web display
    if len(context_data) > 1000:
        return f"{context_data[:1000]}... (truncated)"
    
    return context_data 