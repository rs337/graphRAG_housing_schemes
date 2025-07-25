# GraphRAG UI

A Gradio-based user interface for interacting with GraphRAG search capabilities.

## Features

- Simple, intuitive interface for asking questions
- Support for multiple search types:
  - Global Search: For broad, knowledge-based queries
  - Local Search: For specific, contextual queries
  - Basic Search: For simple text matching
- Example queries for each search type
- Clean, modern theme

## For Testers

No setup required! You'll receive:
1. A specific time slot for testing
2. A temporary link to access the interface
3. A feedback form to share your experience

Please note:
- The link only works during your assigned time slot
- Use Chrome or Firefox for best experience
- No installation or technical knowledge needed

## For Developers

1. Install dependencies:
```bash
pip install -r ../requirements.txt
```

2. Set up environment:
```bash
# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

3. Run the application:
```bash
python app.py
```

4. Access points:
- Local: http://localhost:7860
- Public URL will be displayed in the console

## Example Queries

- "What are the main topics discussed in the documents?" (Global Search)
- "Tell me about specific details in section 3." (Local Search)
- "Find exact matches for 'important term'" (Basic Search)

## Development Roadmap

Current Phase:
- Collecting user feedback
- Improving retrieval quality
- Testing with different document types (tables)

Future Plans:
- Custom web interface
- Cloud deployment
- Persistent availability
- Enhanced features based on user feedback
- Caching

## Notes

- The interface automatically loads necessary data
- Error messages will be displayed if something goes wrong
- Context information is available but hidden by default 