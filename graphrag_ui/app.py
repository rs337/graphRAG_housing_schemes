import gradio as gr
# Lazy import GraphRAG to improve startup time
# import graphrag.api as api  # Commented out - will import later
from pathlib import Path
import pandas as pd
from typing import Tuple, Dict, Any, Union
import os
from dotenv import load_dotenv
from graphrag.config.load_config import load_config
import asyncio
from functools import partial
import time
import signal
import sys
import logging
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Disable other verbose loggers
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Verify API key
if not os.getenv("GRAPHRAG_API_KEY"):
    logger.error("GRAPHRAG_API_KEY not found in environment variables")
    raise ValueError("GRAPHRAG_API_KEY not found. Please set it in your .env file")

# Global variable to hold the GraphRAG API module
api = None

def load_graphrag_api():
    """Lazy load GraphRAG API with progress indication."""
    global api
    if api is None:
        print("🔄 Loading GraphRAG API (this may take 30-90 seconds)...")
        print("   Loading dependencies: gensim, graspologic, and other ML libraries...")
        logger.info("Loading GraphRAG API...")
        start_time = time.time()
        import graphrag.api as graphrag_api
        api = graphrag_api
        load_time = time.time() - start_time
        print(f"✅ GraphRAG API loaded successfully in {load_time:.1f} seconds!")
        logger.info(f"GraphRAG API loaded successfully in {load_time:.1f} seconds")
    return api

# Load GraphRAG configuration and data
# Get absolute path to project directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIRECTORY = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "my_graphrag_project"))
logger.info(f"Using project directory: {PROJECT_DIRECTORY}")

COMMUNITY_LEVEL = 2
RESPONSE_TYPE = "Multiple Paragraphs"  # Changed for better formatting
CLAIM_EXTRACTION_ENABLED = False

# Add timeout for searches
SEARCH_TIMEOUT = 120  # 120 seconds timeout (first searches can be slow)

# Model configuration
MODELS = {
    "gpt-4-turbo-preview": {
        "name": "GPT-4 Turbo",
        "description": "Best quality, highest cost",
        "input_cost": 0.01,
        "output_cost": 0.03
    },
    "gpt-4": {
        "name": "GPT-4",
        "description": "High quality, high cost",
        "input_cost": 0.03,
        "output_cost": 0.06
    },
    "gpt-3.5-turbo-1106": {
        "name": "GPT-3.5 Turbo",
        "description": "Good quality, lower cost",
        "input_cost": 0.001,
        "output_cost": 0.002
    }
}

# Default model selections
DEFAULT_SEARCH_MODEL = "gpt-3.5-turbo-1106"  # Cheaper model for queries
DEFAULT_GRAPH_MODEL = "gpt-4-turbo-preview"   # Better model for graph construction

class SearchTimeout(Exception):
    """Custom exception for search timeouts."""
    pass

def signal_handler(signum, frame):
    """Handle timeout signal."""
    raise SearchTimeout("Search operation timed out")

def load_graphrag_data():
    """Load all necessary GraphRAG data."""
    try:
        # Load configuration silently
        config = load_config(Path(PROJECT_DIRECTORY))
        
        # Update model configuration in config
        if hasattr(config, 'models') and 'default_chat_model' in config.models:
            config.models['default_chat_model'].model = DEFAULT_SEARCH_MODEL
        
        # Load data with timeout protection
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(30)  # 30 second timeout for data loading
        
        # Load parquet files silently
        entities = pd.read_parquet(f"{PROJECT_DIRECTORY}/output/entities.parquet")
        communities = pd.read_parquet(f"{PROJECT_DIRECTORY}/output/communities.parquet")
        community_reports = pd.read_parquet(f"{PROJECT_DIRECTORY}/output/community_reports.parquet")
        text_units = pd.read_parquet(f"{PROJECT_DIRECTORY}/output/text_units.parquet")
        relationships = pd.read_parquet(f"{PROJECT_DIRECTORY}/output/relationships.parquet")
        
        signal.alarm(0)  # Disable alarm
        
        return {
            "config": config,
            "entities": entities,
            "communities": communities,
            "community_reports": community_reports,
            "text_units": text_units,
            "relationships": relationships
        }
    except SearchTimeout:
        logger.error("Data loading timed out. Check if files are accessible.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}", exc_info=True)
        sys.exit(1)

async def search_with_timeout(search_func, **kwargs) -> Tuple[str, str]:
    """Wrapper to add timeout to search functions."""
    try:
        # Log the function being called and its parameters
        logger.debug(f"Calling {search_func.__name__} with params: {kwargs}")
        
        # Create a task for the search
        search_task = asyncio.create_task(search_func(**kwargs))
        start_time = time.time()
        
        # Wait for the task with timeout
        response, context = await asyncio.wait_for(search_task, timeout=SEARCH_TIMEOUT)
        
        # Log completion time
        duration = time.time() - start_time
        logger.info(f"Search completed in {duration:.2f} seconds")
        
        return response, str(context)
    except asyncio.TimeoutError:
        logger.error(f"Search timed out after {SEARCH_TIMEOUT} seconds")
        return f"⏰ Search timed out after {SEARCH_TIMEOUT} seconds. Please try a more specific query or check your connection.", ""
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", ""

async def search(query: str, search_type: str, model: str, data: Dict[str, Any]) -> Tuple[str, str]:
    """Perform search based on selected type."""
    try:
        logger.info(f"Starting {search_type} with model {model}")
        
        # Load GraphRAG API if not already loaded
        api_module = load_graphrag_api()
        
        # Update model in config
        if hasattr(data["config"], 'llm_config'):
            logger.debug(f"Updating model in config to {model}")
            data["config"].llm_config.model = model
        
        search_params = {
            "config": data["config"],
            "query": query
        }

        if search_type == "Global Search":
            logger.debug("Preparing Global Search parameters")
            search_params.update({
                "entities": data["entities"],
                "communities": data["communities"],
                "community_reports": data["community_reports"],
                "community_level": COMMUNITY_LEVEL,
                "dynamic_community_selection": False,
                "response_type": RESPONSE_TYPE
            })
            return await search_with_timeout(api_module.global_search, **search_params)
            
        elif search_type == "Local Search":
            logger.debug("Preparing Local Search parameters")
            search_params.update({
                "entities": data["entities"],
                "communities": data["communities"],
                "community_reports": data["community_reports"],
                "text_units": data["text_units"],
                "relationships": data["relationships"],
                "covariates": None,
                "community_level": COMMUNITY_LEVEL,
                "response_type": RESPONSE_TYPE
            })
            return await search_with_timeout(api_module.local_search, **search_params)
            
        else:  # Basic Search
            logger.debug("Preparing Basic Search parameters")
            search_params.update({
                "text_units": data["text_units"]
            })
            return await search_with_timeout(api_module.basic_search, **search_params)
            
    except Exception as e:
        logger.error(f"Error in search: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", ""

def format_response(response: str) -> str:
    """Format the response text for better readability."""
    if not response:
        return response
    
    # Add markdown formatting for better readability
    formatted = response.strip()
    
    # Convert bullet points to markdown format
    formatted = re.sub(r'^[•·\-\*]\s+', '- ', formatted, flags=re.MULTILINE)
    
    # Add proper spacing around sections
    formatted = re.sub(r'\n\n+', '\n\n', formatted)
    
    # Bold key terms (entities that might be important)
    # This is a simple heuristic - you might want to make this more sophisticated
    formatted = re.sub(r'\b(Cost Rental|Housing Agency|Local Authority|Dublin|Ireland)\b', 
                      r'**\1**', formatted)
    
    # Add line breaks for better readability
    sentences = formatted.split('. ')
    if len(sentences) > 3:
        # Group sentences into paragraphs
        paragraphs = []
        current_paragraph = []
        for sentence in sentences:
            current_paragraph.append(sentence)
            if len(current_paragraph) >= 3:  # 3 sentences per paragraph
                paragraphs.append('. '.join(current_paragraph) + '.')
                current_paragraph = []
        if current_paragraph:
            paragraphs.append('. '.join(current_paragraph))
        formatted = '\n\n'.join(paragraphs)
    
    return formatted

def format_context_data(context_data: str) -> str:
    """Format context data for display."""
    if not context_data or context_data == "":
        return "No context data available"
    
    # Try to parse and format structured data
    try:
        # If it's a string representation of a list/dict, format it
        if context_data.startswith('[') or context_data.startswith('{'):
            import json
            parsed = json.loads(context_data)
            return f"```json\n{json.dumps(parsed, indent=2)}\n```"
    except:
        pass
    
    # Otherwise, just return the raw context
    return f"```\n{context_data}\n```"

def create_interface(data: Dict[str, Any], loop: asyncio.AbstractEventLoop) -> gr.Interface:
    """Create the Gradio interface."""
    search_types = ["Global Search", "Local Search", "Basic Search"]
    model_choices = list(MODELS.keys())
    
    def sync_search(query: str, search_type: str, model: str) -> Tuple[str, str]:
        """Synchronous wrapper that uses the provided event loop."""
        try:
            if not loop.is_running():
                logger.error("Event loop not running")
                return "Error: Server configuration issue. Please try again.", ""
            
            logger.info(f"Processing search request: {search_type}, Query: {query}, Model: {model}")
            future = asyncio.run_coroutine_threadsafe(
                search(query, search_type, model, data),
                loop
            )
            
            # Use longer timeout for the sync wrapper
            response, context = future.result(timeout=SEARCH_TIMEOUT + 10)
            
            # Format the response for better display
            formatted_response = format_response(response)
            formatted_context = format_context_data(context)
            
            return formatted_response, formatted_context
        except asyncio.TimeoutError:
            logger.error(f"Search request timed out after {SEARCH_TIMEOUT + 10} seconds")
            return f"⏰ **Search Timeout**: Your search took longer than {SEARCH_TIMEOUT} seconds and was cancelled.\n\n**Try these solutions:**\n- Make your question more specific\n- Try a different search type\n- Check your internet connection\n- The GraphRAG system might be under heavy load", ""
        except Exception as e:
            logger.error(f"Error in sync_search: {str(e)}", exc_info=True)
            return f"❌ **Search Error**: {str(e)}\n\nPlease try again or contact support if the issue persists.", ""
    
    # Create model choice descriptions
    model_descriptions = [f"{MODELS[m]['name']} - {MODELS[m]['description']}" for m in model_choices]
    
    interface = gr.Interface(
        fn=sync_search,
        inputs=[
            gr.Textbox(
                label="Enter your question",
                placeholder="What would you like to know?",
                info="Try to be as specific as possible with your question"
            ),
            gr.Dropdown(
                choices=search_types,
                label="Search Type",
                value="Global Search",
                info="Global: Overall knowledge, Local: Specific sections, Basic: Exact matches"
            ),
            gr.Dropdown(
                choices=model_choices,
                label="Model",
                value=DEFAULT_SEARCH_MODEL,
                info="Select the model to use for search (affects cost and quality)"
            )
        ],
        outputs=[
            gr.Markdown(label="Answer", show_copy_button=True),
            gr.Markdown(label="Context Information", visible=True)
        ],
        title="Document Search Interface",
        description=f"""Ask questions about your documents using different search strategies:
        
- **Global Search**: Best for general questions about overall topics and themes
- **Local Search**: Best for finding specific information in particular sections  
- **Basic Search**: Best for finding exact text matches

**Available Models:**
{chr(10).join(f'- {desc}' for desc in model_descriptions)}

**⚠️ Search Times:** 
- First search: 30-90 seconds (GraphRAG API loading + processing)
- Subsequent searches: 15-60 seconds depending on complexity
- Searches timeout after 2 minutes

**Tips for Better Results:**
- Be specific with your questions
- Use different search types for different kinds of information
- Try rephrasing if you don't get the expected results""",
        examples=[
            ["What are the main housing schemes available in Ireland?", "Global Search", DEFAULT_SEARCH_MODEL],
            ["What are the income limits for Cost Rental homes?", "Local Search", DEFAULT_SEARCH_MODEL],
            ["Find information about STAR investment scheme", "Basic Search", DEFAULT_SEARCH_MODEL]
        ]
    )
    
    return interface

def main():
    """Main application entry point."""
    try:
        print("🚀 Starting GraphRAG UI...")
        logger.info("Starting GraphRAG UI...")
        
        print("📂 Loading GraphRAG data...")
        # Load data silently
        data = load_graphrag_data()
        print("✅ Data loaded successfully!")
        
        # Create and get event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create interface with loop
        demo = create_interface(data, loop)
        
        # Run the event loop in a separate thread
        import threading
        def run_event_loop():
            loop.run_forever()
            
        loop_thread = threading.Thread(target=run_event_loop, daemon=True)
        loop_thread.start()
        
        print("🌐 Starting web interface...")
        print("📝 Note: Your first search will take 30-90 seconds (API loading + processing)")
        print("     Searches timeout after 2 minutes if no response")
        
        # Run the Gradio interface
        try:
            demo.launch(
                server_name="0.0.0.0",
                server_port=7860,
                share=True,
                show_error=True
            )
        finally:
            # Clean up
            loop.call_soon_threadsafe(loop.stop)
            loop_thread.join()
            loop.close()
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 