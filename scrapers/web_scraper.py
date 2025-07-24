import os
import re
from pathlib import Path
from dotenv import load_dotenv
import hashlib

load_dotenv()

# Get API keys from environment variables
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

from camel.loaders import Firecrawl

# Initialize Firecrawl
firecrawl = Firecrawl()

def clean_for_graphrag(markdown_content):
    """Clean markdown content while preserving structure for GraphRAG"""
    # Remove cookie notice at the beginning (from start until "Service")
    cleaned = re.sub(r'^A notice about cookies.*?(?=Service)', '', markdown_content, flags=re.DOTALL)
    
    # Remove cookie preferences section at the end
    cleaned = re.sub(r'Manage cookie preferences.*$', '', cleaned, flags=re.DOTALL)
    
    # Also handle alternative ending patterns
    cleaned = re.sub(r'### Manage cookie preferences.*$', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'Cookie preferences.*?Close\s*$', '', cleaned, flags=re.DOTALL)
    
    # Remove excessive whitespace but preserve structure
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned

def generate_document_id(url):
    """Generate a unique document ID from URL"""
    return hashlib.md5(url.encode()).hexdigest()[:12]

def scrape_and_save_for_graphrag(url, output_dir="graphrag_input"):
    """
    Scrape a URL and save as plain text for GraphRAG
    """
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    try:
        # Scrape the URL
        response = firecrawl.app.scrape_url(
            url=url,
            formats=['markdown']
        )
        
        # Extract and clean the markdown content
        if hasattr(response, 'markdown') and response.markdown:
            content = response.markdown
        elif isinstance(response, dict) and 'markdown' in response:
            content = response['markdown']
        else:
            content = str(response)
        
        cleaned_content = clean_for_graphrag(content)
        
        # Generate simple filename from URL
        doc_id = generate_document_id(url)
        filename = f"{doc_id}.txt"
        filepath = Path(output_dir) / filename
        
        # Save as plain text file (just the cleaned content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"Successfully saved: {filepath}")
        print(f"Content length: {len(cleaned_content)} characters")
        
        return filepath
        
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None



if __name__ == "__main__":
    # Single URL scraping - just change the URL as needed
    url = "https://insert url here"
    scrape_and_save_for_graphrag(url)