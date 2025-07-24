#!/usr/bin/env python3
"""
Structured Web Scraper for GraphRAG
"""

import os
import re
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import hashlib
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Tuple, Optional
import json
from urllib.parse import urljoin, urlparse

# Try to import Firecrawl, fallback to requests if not available
try:
    from camel.loaders import Firecrawl
    FIRECRAWL_AVAILABLE = True
except ImportError:
    print("Firecrawl not available, using requests + BeautifulSoup")
    FIRECRAWL_AVAILABLE = False

load_dotenv()

class StructuredWebScraper:
    """
    Web scraper that handles both structured and unstructured data.
    """
    
    def __init__(self):
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        if FIRECRAWL_AVAILABLE and self.firecrawl_api_key:
            self.firecrawl = Firecrawl()
            print("✅ Firecrawl initialized")
        else:
            self.firecrawl = None
            print("📝 Using requests + BeautifulSoup")
    
    def extract_tables_from_html(self, html_content: str, base_url: str = "") -> List[Dict[str, Any]]:
        """
        Extract tables as structured data with context.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = []
        
        for i, table in enumerate(soup.find_all('table')):
            try:
                # Extract table as DataFrame
                df = pd.read_html(str(table))[0]
                
                # Clean column names
                if len(df.columns) > 0:
                    df.columns = [str(col).strip().replace('\n', ' ') for col in df.columns]
                
                # Extract context around the table
                context = self._extract_table_context(table, soup)
                
                # Generate meaningful summary
                summary = self._generate_table_summary(df, context)
                
                # Create table dictionary
                table_info = {
                    'index': i,
                    'dataframe': df,
                    'summary': summary,
                    'context': context,
                    'html': str(table),
                    'shape': df.shape,
                    'location': f"Table {i+1} of {len(soup.find_all('table'))}"
                }
                
                tables.append(table_info)
                
            except Exception as e:
                print(f"Could not parse table {i}: {e}")
                continue
        
        return tables
    
    def _extract_table_context(self, table_element, soup) -> str:
        """Extract contextual information around a table."""
        context_parts = []
        
        # Look for preceding heading
        current = table_element.find_previous()
        heading_distance = 0
        while current and heading_distance < 5:
            if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                context_parts.append(f"Section: {current.get_text(strip=True)}")
                break
            elif current.name == 'p':
                text = current.get_text(strip=True)
                if len(text) > 10:  # Meaningful paragraph
                    context_parts.append(f"Context: {text}")
                    break
            current = current.find_previous()
            heading_distance += 1
        
        # Look for table caption
        caption = table_element.find('caption')
        if caption:
            context_parts.append(f"Caption: {caption.get_text(strip=True)}")
        
        # Look for following explanatory text
        next_elem = table_element.find_next('p')
        if next_elem:
            next_text = next_elem.get_text(strip=True)
            if len(next_text) > 10 and 'table' in next_text.lower():
                context_parts.append(f"Note: {next_text}")
        
        return " | ".join(context_parts) if context_parts else "No context found"
    
    def _generate_table_summary(self, df: pd.DataFrame, context: str) -> str:
        """Generate a human-readable summary of the table for GraphRAG."""
        if df.empty:
            return "Empty table"
        
        summary_parts = []
        
        # Basic info
        rows, cols = df.shape
        summary_parts.append(f"Table with {rows} rows and {cols} columns")
        
        # Column information
        if cols > 0:
            column_names = list(df.columns)
            summary_parts.append(f"Columns: {', '.join(column_names)}")
        
        # Data types and patterns
        if rows > 0:
            # Look for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                summary_parts.append(f"Numeric data in: {', '.join(numeric_cols)}")
            
            # Look for patterns in data
            for col in df.columns:
                if col and len(str(col)) > 0:
                    unique_vals = df[col].nunique() if rows > 1 else 1
                    if unique_vals <= 5 and rows > 3:  # Categorical data
                        vals = df[col].unique()[:3]  # First 3 unique values
                        summary_parts.append(f"{col} categories: {', '.join(str(v) for v in vals)}")
        
        # Sample data description
        if rows > 0 and cols > 0:
            try:
                first_row = df.iloc[0]
                sample_data = []
                for col, val in first_row.items():
                    if pd.notna(val) and str(val).strip():
                        sample_data.append(f"{col}: {val}")
                if sample_data:
                    summary_parts.append(f"Example row - {', '.join(sample_data[:3])}")
            except:
                pass
        
        return ". ".join(summary_parts)
    
    def _extract_page_title(self, html_content: str) -> str:
        """Extract the page title from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try multiple methods to get title
        title_candidates = []
        
        # Method 1: <title> tag
        title_tag = soup.find('title')
        if title_tag:
            title_candidates.append(title_tag.get_text(strip=True))
        
        # Method 2: h1 tag
        h1_tag = soup.find('h1')
        if h1_tag:
            title_candidates.append(h1_tag.get_text(strip=True))
        
        # Method 3: Meta title (skip due to type issues)
        # meta_title = soup.find('meta', attrs={'property': 'og:title'}) or soup.find('meta', attrs={'name': 'title'})
        # if meta_title:
        #     title_candidates.append(meta_title.get('content', ''))
        
        # Filter out common unwanted titles
        unwanted_terms = ['cookies', 'analytics', 'citizensinformation.ie', 'home']
        
        for title in title_candidates:
            if title and len(title) > 0:
                # Skip if it's just website name or generic terms
                if not any(term in title.lower() for term in unwanted_terms):
                    return title
                # But if it contains useful info, clean it
                elif len(title) > 20:
                    return title
        
        # Return first non-empty title if no good one found
        for title in title_candidates:
            if title and len(title.strip()) > 0:
                return title
        
        return "No title"
    
    def scrape_page(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a webpage and extract both structured and unstructured content.
        
        Returns:
        - main_content: cleaned text content
        - tables: list of extracted tables with metadata
        - metadata: page information
        """
        try:
            # Method 1: Try Firecrawl for general content
            main_content = ""
            html_content = ""
            
            if self.firecrawl:
                try:
                    response = self.firecrawl.app.scrape_url(
                        url=url,
                        formats=['markdown', 'html']
                    )
                    
                    if hasattr(response, 'markdown'):
                        main_content = response.markdown
                    elif isinstance(response, dict) and 'markdown' in response:
                        main_content = response['markdown']
                    
                    # Get HTML for table extraction
                    if hasattr(response, 'html'):
                        html_content = response.html
                    elif isinstance(response, dict) and 'html' in response:
                        html_content = response['html']
                        
                except Exception as e:
                    print(f"Firecrawl failed: {e}, falling back to requests")
            
            # Method 2: Use requests if Firecrawl unavailable or failed
            if not html_content:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                html_content = response.text
                
                if not main_content:
                    # Extract main content with BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Remove unwanted elements
                    for elem in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                        elem.decompose()
                    
                    # Extract main content
                    main = soup.find('main') or soup.find('article') or soup.find('body')
                    if main:
                        main_content = main.get_text(separator='\n', strip=True)
                    else:
                        main_content = soup.get_text(separator='\n', strip=True)
            
            # Extract tables
            tables = self.extract_tables_from_html(html_content, url)
            
            # Clean main content
            cleaned_content = self._clean_content(main_content or "")
            
            # Extract metadata
            page_title = self._extract_page_title(html_content)
            soup = BeautifulSoup(html_content, 'html.parser')
            metadata = {
                'url': url,
                'title': page_title,
                'description': self._get_meta_description(soup),
                'num_tables': len(tables),
                'content_length': len(cleaned_content)
            }
            
            return {
                'main_content': cleaned_content,
                'tables': tables,
                'metadata': metadata
            }
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    def _clean_content(self, content: str) -> str:
        """Clean content while preserving structure."""
        if not content:
            return ""
        
        # Remove cookie notices and analytics content
        cleaned = re.sub(r'(?i)### Cookies used by Google Analytics.*?Close\s*', '', content, flags=re.DOTALL)
        cleaned = re.sub(r'(?i)## Cookies on.*?Manage my preferences\s*', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'(?i)(accept all cookies|manage cookies|cookie preferences).*?\n', '', cleaned)
        cleaned = re.sub(r'(?i)(skip to main content|skip navigation).*?\n', '', cleaned)
        cleaned = re.sub(r'(?i)Allow analytics cookies.*?Close\s*', '', cleaned, flags=re.DOTALL)
        
        # Remove social sharing buttons at the end
        cleaned = re.sub(r'\[Share to Facebook\].*?\[Print This Page\].*?\n', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\[Back to top\].*?\n', '', cleaned)
        
        # Remove "Related documents" numerical scores (only at end of lines)
        cleaned = re.sub(r'\n\d+\.\d+\s*$', '', cleaned, flags=re.MULTILINE)
        
        # Remove "Manage preferences" at the end
        cleaned = re.sub(r'## Manage\s*\nManage preferences\s*$', '', cleaned, flags=re.DOTALL)
        
        # Clean up formatting issues
        cleaned = re.sub(r'\[\s*\n#', '# ', cleaned)  # Fix broken headings
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Multiple line breaks
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Multiple spaces
        
        return cleaned.strip()
    
    def _get_meta_description(self, soup) -> str:
        """Extract meta description from HTML."""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '')
        return ''
    
    def create_graphrag_content(self, scraped_data: Dict[str, Any]) -> str:
        """
        Create enhanced content for GraphRAG that includes both unstructured text
        and structured table information.
        """
        if not scraped_data:
            return ""
        
        content_parts = []
        metadata = scraped_data['metadata']
        
        # Add document header with metadata
        content_parts.append(f"# {metadata['title']}")
        content_parts.append(f"Source: {metadata['url']}")
        if metadata['description']:
            content_parts.append(f"Description: {metadata['description']}")
        content_parts.append("")  # Empty line
        
        # Add main content
        if scraped_data['main_content']:
            content_parts.append("## Main Content")
            content_parts.append(scraped_data['main_content'])
            content_parts.append("")
        
        # Process tables - THIS IS THE KEY PART
        if scraped_data['tables']:
            content_parts.append("## Structured Data (Tables)")
            content_parts.append("")
            
            for i, table_info in enumerate(scraped_data['tables']):
                content_parts.append(f"### Table {i+1}: {table_info['context']}")
                content_parts.append(f"**Summary**: {table_info['summary']}")
                content_parts.append("")
                
                # Include table data in a GraphRAG-friendly format
                df = table_info['dataframe']
                
                # Method 1: Create descriptive text from table
                content_parts.append("**Table Data Analysis:**")
                table_description = self._create_table_description(df)
                content_parts.append(table_description)
                content_parts.append("")
                
                # Method 2: Include formatted table for structure
                content_parts.append("**Formatted Table:**")
                if not df.empty and df.shape[0] <= 20:  # Only include if not too large
                    # Convert to markdown table
                    table_md = df.to_markdown(index=False)
                    content_parts.append(table_md)
                else:
                    content_parts.append(f"Large table ({df.shape[0]} rows) - see summary above")
                content_parts.append("")
        
        return "\n".join(content_parts)
    
    def _create_table_description(self, df: pd.DataFrame) -> str:
        """
        Convert table data into narrative text that GraphRAG can understand.
        This is crucial for making structured data searchable.
        """
        if df.empty:
            return "No data available in this table."
        
        descriptions = []
        
        # Describe each row as a relationship/fact
        for i, (idx, row) in enumerate(df.iterrows()):
            if i >= 10:  # Limit to prevent huge chunks
                descriptions.append(f"... and {len(df) - i} more entries")
                break
                
            row_desc = []
            for col, value in row.items():
                if pd.notna(value) and str(value).strip():
                    row_desc.append(f"{col} is {value}")
            
            if row_desc:
                descriptions.append(f"Entry {i + 1}: {', '.join(row_desc)}")
        
        # Add column relationships
        if len(df.columns) > 1:
            descriptions.append(f"\nThis table shows relationships between: {', '.join(df.columns)}")
        
        return ". ".join(descriptions)
    
    def save_for_graphrag(self, url: str, output_dir: str = "graphrag_input") -> Optional[str]:
        """
        Scrape a URL and save in GraphRAG-optimized format.
        """
        Path(output_dir).mkdir(exist_ok=True)
        
        # Scrape the page
        scraped_data = self.scrape_page(url)
        if not scraped_data:
            return None
        
        # Create GraphRAG content
        graphrag_content = self.create_graphrag_content(scraped_data)
        
        # Save main content
        doc_id = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"{doc_id}.txt"
        filepath = Path(output_dir) / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(graphrag_content)
        
        # Save structured data separately for analysis
        if scraped_data['tables']:
            tables_dir = Path(output_dir) / "tables"
            tables_dir.mkdir(exist_ok=True)
            
            for i, table_info in enumerate(scraped_data['tables']):
                table_file = tables_dir / f"{doc_id}_table_{i}.json"
                
                # Save table metadata and data
                table_data = {
                    'url': url,
                    'table_index': i,
                    'summary': table_info['summary'],
                    'context': table_info['context'],
                    'shape': table_info['shape'],
                    'data': table_info['dataframe'].to_dict('records') if not table_info['dataframe'].empty else []
                }
                
                with open(table_file, 'w', encoding='utf-8') as f:
                    json.dump(table_data, f, indent=2, default=str)
        
        print(f"✅ Successfully saved: {filepath}")
        print(f"📊 Content length: {len(graphrag_content)} characters")
        print(f"📋 Tables found: {len(scraped_data['tables'])}")
        
        return str(filepath)

if __name__ == "__main__":
    
    # Create scraper instance
    scraper = StructuredWebScraper()
    
    # Test with page that has tables
    test_url = "https://insert url here"
    
    print(f"\n🔍 Testing with: {test_url}")
    
    result = scraper.save_for_graphrag(test_url)
    
    if result:
        print(f"\nSuccess! Check the file: {result}")
        
    else:
        print("\nFailed to scrape the page") 