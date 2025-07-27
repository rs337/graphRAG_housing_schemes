"""
Django Views for GraphRAG Chat Application
"""

import logging
import asyncio
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from asgiref.sync import sync_to_async
from .services import graphrag_service, format_response, format_context_data

# Set up logging
logger = logging.getLogger('chat')

def index(request):
    """
    Main chat interface view.
    This renders the single-page application with the chat interface.
    """
    # Context data for the template
    context = {
        'title': 'GraphRAG Chat Interface',
        'search_types': [
            {
                'value': 'global',
                'label': 'Global Search',
                'description': 'Analyzes the entire knowledge base to provide broader insights and connections across multiple topics. Best for complex questions requiring synthesis of information.'
            },
            {
                'value': 'local', 
                'label': 'Local Search',
                'description': 'Searches through specific documents and passages to find detailed information. Best for questions about particular sections or specific details.'
            },
            {
                'value': 'basic',
                'label': 'Basic Search', 
                'description': 'Performs direct text matching in documents. Best for factual queries and finding exact text matches.'
            }
        ],
        'example_queries': [
            {
                'query': 'What housing schemes are available in Ireland?',
                'search_type': 'global',
                'description': 'Good for getting an overview of all available housing options'
            },
            {
                'query': 'What are the income limits for Cost Rental homes?',
                'search_type': 'local',
                'description': 'Specific information that would be in particular documents'
            },
            {
                'query': 'STAR investment scheme requirements',
                'search_type': 'basic',
                'description': 'Finding exact text about a specific scheme'
            }
        ],
        'data_sources': [
            {
                'category': 'Government Sources',
                'sources': [
                    {'title': 'Department of Housing Website', 'url': 'https://gov.ie/housing'},
                    {'title': 'Citizens Information - Housing', 'url': 'https://citizensinformation.ie/housing'},
                    {'title': 'Local Authority Housing', 'url': 'https://gov.ie/local-authority-housing'},
                ]
            }
        ]
    }
    
    return render(request, 'chat/index.html', context)

class ChatQueryView(View):
    """
    AJAX endpoint for processing chat queries.
    Handles POST requests with query and search type parameters.
    """
    
    def get(self, request):
        """Handle GET requests (not allowed for this endpoint)."""
        return JsonResponse({
            'success': False,
            'error': 'GET method not allowed. Use POST to submit queries.'
        }, status=405)
    
    def post(self, request):
        """
        Handle POST requests for chat queries.
        Expected JSON payload: {'query': str, 'search_type': str}
        """
        try:
            # Parse JSON request body
            data = json.loads(request.body)
            query = data.get('query', '').strip()
            search_type = data.get('search_type', 'global').lower()
            
            # Validate input
            if not query:
                return JsonResponse({
                    'success': False,
                    'error': 'Query cannot be empty'
                }, status=400)
            
            if search_type not in ['global', 'local', 'basic']:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid search type. Must be: global, local, or basic'
                }, status=400)
            
            logger.info(f"Received {search_type} search query: {query}")
            
            # Check if GraphRAG service is ready
            if not graphrag_service.is_ready():
                logger.info("GraphRAG service not ready, initializing...")
                if not graphrag_service.load_data():
                    return JsonResponse({
                        'success': False,
                        'error': 'Failed to initialize GraphRAG service. Please try again.'
                    }, status=500)
            
            # Perform the search based on type
            try:
                # Use Django's async support to run the search
                response, context = asyncio.run(self._perform_search(query, search_type))
                
                # Format the response for web display
                formatted_response = format_response(response)
                formatted_context = format_context_data(context)
                
                return JsonResponse({
                    'success': True,
                    'response': formatted_response,
                    'context': formatted_context,
                    'search_type': search_type,
                    'query': query
                })
                
            except Exception as e:
                logger.error(f"Search execution error: {str(e)}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'error': f'Search failed: {str(e)}'
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
            
        except Exception as e:
            logger.error(f"Unexpected error in chat query: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred. Please try again.'
            }, status=500)
    
    async def _perform_search(self, query: str, search_type: str):
        """
        Perform the actual search based on the search type.
        This method runs the appropriate GraphRAG search function.
        """
        if search_type == 'global':
            return await graphrag_service.global_search(query)
        elif search_type == 'local':
            return await graphrag_service.local_search(query)
        elif search_type == 'basic':
            return await graphrag_service.basic_search(query)
        else:
            raise ValueError(f"Unknown search type: {search_type}")

@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint to verify the service is running.
    Also checks if GraphRAG service is ready.
    """
    try:
        is_ready = graphrag_service.is_ready()
        
        return JsonResponse({
            'status': 'healthy',
            'graphrag_ready': is_ready,
            'message': 'GraphRAG Chat service is running' + (' and ready' if is_ready else ' but not initialized')
        })
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Service error: {str(e)}'
        }, status=500)
