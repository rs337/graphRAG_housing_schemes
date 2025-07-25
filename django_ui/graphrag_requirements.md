# GraphRAG Django Web Application - Project Requirements

## Project Overview
A simple, single-page Django web application that provides a chat interface for querying a GraphRAG knowledge base built from Irish government and citizen information sources.

## Core Functionality

### 1. Application Structure
- **Framework**: Django (latest stable version)
- **Architecture**: Single-page application with one main view
- **Data Source**: Pre-built .parquet files from GraphRAG indexing
- **API Integration**: Use `graphrag.api` for query processing

### 2. User Interface Layout

#### Header Section
- **Application Title**: Prominent title for the GraphRAG chat application
- **Description Panel**: 
  - Brief explanation of what the application does
  - Example queries to help users get started
  - Clear explanation of search types (Global vs Basic)

#### Search Type Explanations
- **Basic Search**: "Searches through specific documents and passages to find direct answers to your question. Best for factual queries about specific topics (e.g., 'What are the requirements for a driving license?')"
- **Global Search**: "Analyzes the entire knowledge base to provide broader insights and connections across multiple topics. Best for complex questions requiring synthesis of information (e.g., 'What government services are available for new parents?')"

#### Chat Interface
- **Search Type Selection**: Radio buttons or dropdown for Global/Basic search
- **Input Field**: Text input for user queries
- **Send Button**: Submit query button
- **Chat History**: Display conversation with user queries and GraphRAG responses
- **Loading State**: Show processing indicator during API calls

#### Footer Section
- **Data Sources**: Static list of sources used to build the knowledge base
  - List of .gov.ie pages with clickable links
  - List of citizensinformation.ie pages with clickable links
  - Organize by category/department if applicable

## Technical Requirements

### 3. Backend Implementation

#### Django Project Structure
```
graphrag_chat_project/
├── manage.py
├── requirements.txt
├── .env (for environment variables)
├── graphrag_chat_project/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── chat/
    ├── __init__.py
    ├── views.py
    ├── urls.py
    ├── models.py (minimal usage)
    ├── services.py (GraphRAG integration)
    └── templates/
        └── chat/
            └── index.html
```

#### Key Components

**Settings Configuration**:
- Add GraphRAG data file paths as configurable settings
- Support for environment variables for file paths
- Static files configuration for CSS/JS

**GraphRAG Integration Service**:
- Service function to handle `graphrag.api` calls
- Support for both global and basic search modes
- Error handling for API failures
- Response formatting for frontend consumption

**Views**:
- Main page view to render the chat interface
- AJAX endpoint for processing chat queries
- JSON response handling

**URL Configuration**:
- Root URL for main chat page
- API endpoint for query processing

### 4. Frontend Implementation

#### Templates
- **Base Template**: HTML structure with responsive design
- **Chat Interface**: Dynamic chat bubbles for conversation flow
- **Responsive Design**: Works on desktop and mobile devices

#### JavaScript Functionality
- **AJAX Handling**: Send queries without page refresh
- **Real-time Updates**: Update chat interface with responses
- **Loading States**: Show processing indicators
- **Form Validation**: Basic input validation
- **Error Handling**: Display error messages to users

#### Styling
- **CSS Framework**: Bootstrap for quick, professional styling
- **Custom Styles**: Additional CSS for chat interface and branding
- **Responsive Layout**: Mobile-friendly design

### 5. Data Integration

#### File Management
- **Parquet File Access**: Direct file system access to GraphRAG output
- **Configurable Paths**: Environment variables or settings for file locations
- **Error Handling**: Graceful handling of missing files

#### API Integration
```python
# Expected API usage pattern
import graphrag.api as api

# Basic search
response = api.search(query="user question", search_type="basic")

# Global search  
response = api.search(query="user question", search_type="global")
```

### 6. Static Content

#### Source Lists
Create comprehensive lists of data sources:
- **Government Sources**: All .gov.ie pages used in indexing
- **Citizen Information**: All citizensinformation.ie pages used
- **Format**: Title, URL, brief description
- **Organization**: Group by topic/department where logical

## Implementation Phases

### Phase 1: Basic Django Setup
1. Create Django project and app
2. Configure settings and basic URL routing
3. Create main template structure
4. Test basic page rendering

### Phase 2: GraphRAG Integration
1. Install and configure graphrag.api
2. Create service layer for API calls
3. Test file access and API integration
4. Implement error handling

### Phase 3: Frontend Development
1. Build chat interface HTML/CSS
2. Implement JavaScript for AJAX communication
3. Create responsive design
4. Add loading states and error handling

### Phase 4: Content and Polish
1. Add comprehensive source lists
2. Write user-friendly descriptions and examples
3. Style and polish the interface
4. Test thoroughly with various queries

## Dependencies

### Python Packages
```
Django>=4.2
graphrag
python-dotenv
gunicorn (for deployment)
```

### Frontend Libraries
- Bootstrap 5 (CSS framework)
- jQuery (for AJAX handling)
- Font Awesome (icons, optional)

## Configuration Files

### Environment Variables (.env)
```
GRAPHRAG_DATA_PATH=/path/to/parquet/files
DEBUG=True
SECRET_KEY=your-secret-key
```

### Example Queries for Description
Include these example queries in the user interface:
- "What documents do I need to apply for Irish citizenship?"
- "How do I register a business in Ireland?"
- "What social welfare payments are available for families?"
- "What are the steps to buy a house in Ireland?"

## Error Handling Requirements
- Graceful handling of GraphRAG API failures
- User-friendly error messages
- Fallback responses when data is unavailable
- Logging for debugging purposes

## Performance Considerations
- Implement basic caching for repeated queries
- Optimize frontend asset loading
- Consider async processing for long-running queries
- Add request timeout handling

## Future Enhancement Considerations
- User session management for chat history
- Export chat conversations
- Advanced search filters
- Admin interface for content management
- Analytics and usage tracking

## Deployment Notes
- Application should be deployable to standard hosting platforms
- Include instructions for setting up environment variables
- Document any server requirements
- Consider containerization with Docker for easier deployment

## Success Criteria
1. Users can successfully query the GraphRAG knowledge base
2. Both global and basic search modes work correctly
3. Chat interface is intuitive and responsive
4. Source attribution is clear and accessible
5. Application handles errors gracefully
6. Interface works on both desktop and mobile devices