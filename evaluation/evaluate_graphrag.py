#!/usr/bin/env python3
"""
GraphRAG Evaluation Script

This script evaluates the graphRAG system by:
1. Loading test cases from test_cases_simple.json
2. Querying the graphRAG system with each question
3. Comparing responses against ground truth using three metrics:
   - Factual Accuracy: Keyword/entity matching
   - Relevance: Semantic similarity using embeddings
   - BLEU Score: Text similarity
"""

import json
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import pandas as pd
from datetime import datetime
import re

# Add the parent directory to sys.path to import from graphrag_ui
sys.path.append(str(Path(__file__).parent.parent))

# Import graphRAG modules
import graphrag.api as api
from graphrag.config.load_config import load_config
from dotenv import load_dotenv

# Import evaluation libraries
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import nltk
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    nltk.download('punkt', quiet=True)
except ImportError as e:
    print(f"Missing required packages: {e}")
    sys.exit(1)

# Load environment variables
load_dotenv()

class GraphRAGEvaluator:
    def __init__(self, project_dir: str = "../my_graphrag_project"):
        """Initialize the evaluator with project directory."""
        self.project_dir = Path(project_dir).resolve()
        self.test_cases_path = Path("tests/test_cases_simple.json")
        
        # Initialize evaluation models
        print("Loading evaluation models...")
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.smoothing = SmoothingFunction().method1
        
        # Load GraphRAG data
        print("Loading GraphRAG data...")
        self.data = self._load_graphrag_data()
        
    def _load_graphrag_data(self) -> Dict[str, Any]:
        """Load GraphRAG configuration and data files."""
        try:
            config = load_config(self.project_dir)
            
            # Load parquet files
            entities = pd.read_parquet(self.project_dir / "output" / "entities.parquet")
            communities = pd.read_parquet(self.project_dir / "output" / "communities.parquet")
            community_reports = pd.read_parquet(self.project_dir / "output" / "community_reports.parquet")
            text_units = pd.read_parquet(self.project_dir / "output" / "text_units.parquet")
            relationships = pd.read_parquet(self.project_dir / "output" / "relationships.parquet")
            
            return {
                "config": config,
                "entities": entities,
                "communities": communities,
                "community_reports": community_reports,
                "text_units": text_units,
                "relationships": relationships
            }
        except Exception as e:
            print(f"Error loading GraphRAG data: {e}")
            sys.exit(1)

    def load_test_cases(self) -> List[Dict]:
        """Load test cases from JSON file."""
        try:
            with open(self.test_cases_path, 'r') as f:
                data = json.load(f)
                return data['test_cases']
        except Exception as e:
            print(f"Error loading test cases: {e}")
            sys.exit(1)

    async def query_graphrag(self, query: str, search_type: str = "Global Search") -> str:
        """Query the GraphRAG system and return the response."""
        try:
            search_params = {
                "config": self.data["config"],
                "query": query
            }

            if search_type == "Global Search":
                search_params.update({
                    "entities": self.data["entities"],
                    "communities": self.data["communities"],
                    "community_reports": self.data["community_reports"],
                    "community_level": 2,
                    "dynamic_community_selection": False,
                    "response_type": "Multiple Paragraphs"
                })
                response, _ = await api.global_search(**search_params)
                
            elif search_type == "Local Search":
                search_params.update({
                    "entities": self.data["entities"],
                    "communities": self.data["communities"],
                    "community_reports": self.data["community_reports"],
                    "text_units": self.data["text_units"],
                    "relationships": self.data["relationships"],
                    "covariates": None,
                    "community_level": 2,
                    "response_type": "Multiple Paragraphs"
                })
                response, _ = await api.local_search(**search_params)
                
            else:  # Basic Search
                search_params.update({
                    "text_units": self.data["text_units"]
                })
                response, _ = await api.basic_search(**search_params)
                
            return response if response else "No response generated"
            
        except Exception as e:
            print(f"Error querying GraphRAG: {e}")
            return f"Error: {str(e)}"

    def calculate_factual_accuracy(self, response: str, ground_truth: str) -> float:
        """
        Calculate factual accuracy by comparing key entities/numbers in response vs ground truth.
        Simple implementation using keyword matching and number extraction.
        """
        # Extract numbers from both texts
        response_numbers = set(re.findall(r'[\d,]+(?:\.\d+)?', response.replace(',', '')))
        truth_numbers = set(re.findall(r'[\d,]+(?:\.\d+)?', ground_truth.replace(',', '')))
        
        # Extract key terms (capitalized words, schemes, etc.)
        response_terms = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', response))
        truth_terms = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', ground_truth))
        
        # Add scheme-specific keywords
        scheme_keywords = {
            'First Home Scheme', 'Help to Buy', 'Local Authority', 'HAP', 'RAS', 
            'Cost Rental', 'Vacant Property', 'Affordable Purchase', 'Enhanced',
            'Dublin', 'Cork', 'Galway', 'fresh start'
        }
        
        response_lower = response.lower()
        truth_lower = ground_truth.lower()
        
        response_schemes = {kw for kw in scheme_keywords if kw.lower() in response_lower}
        truth_schemes = {kw for kw in scheme_keywords if kw.lower() in truth_lower}
        
        # Calculate accuracy as intersection over union
        number_accuracy = len(response_numbers & truth_numbers) / max(len(truth_numbers), 1)
        term_accuracy = len(response_terms & truth_terms) / max(len(truth_terms), 1)
        scheme_accuracy = len(response_schemes & truth_schemes) / max(len(truth_schemes), 1)
        
        # Weighted average (numbers are most important for factual accuracy)
        return (0.5 * number_accuracy + 0.3 * scheme_accuracy + 0.2 * term_accuracy)

    def calculate_relevance(self, response: str, ground_truth: str) -> float:
        """Calculate semantic relevance using sentence embeddings."""
        try:
            # Generate embeddings
            response_embedding = self.sentence_model.encode([response])
            truth_embedding = self.sentence_model.encode([ground_truth])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(response_embedding, truth_embedding)[0][0]
            return float(similarity)
        except Exception as e:
            print(f"Error calculating relevance: {e}")
            return 0.0

    def calculate_bleu_score(self, response: str, ground_truth: str) -> float:
        """Calculate BLEU score between response and ground truth."""
        try:
            # Tokenize
            response_tokens = nltk.word_tokenize(response.lower())
            truth_tokens = nltk.word_tokenize(ground_truth.lower())
            
            # Calculate BLEU score
            bleu_score = sentence_bleu(
                [truth_tokens], 
                response_tokens, 
                smoothing_function=self.smoothing
            )
            return float(bleu_score)
        except Exception as e:
            print(f"Error calculating BLEU score: {e}")
            return 0.0

    async def evaluate_single_case(self, test_case: Dict, search_type: str = "Global Search") -> Dict:
        """Evaluate a single test case."""
        question = test_case['question']
        ground_truth = test_case['ground_truth']
        test_id = test_case['id']
        
        print(f"Evaluating: {test_id}")
        
        # Query GraphRAG
        response = await self.query_graphrag(question, search_type)
        
        # Calculate metrics
        factual_accuracy = self.calculate_factual_accuracy(response, ground_truth)
        relevance = self.calculate_relevance(response, ground_truth)
        bleu_score = self.calculate_bleu_score(response, ground_truth)
        
        return {
            'id': test_id,
            'question': question,
            'ground_truth': ground_truth,
            'response': response,
            'search_type': search_type,
            'metrics': {
                'factual_accuracy': factual_accuracy,
                'relevance': relevance,
                'bleu_score': bleu_score
            }
        }

    async def run_evaluation(self, search_types: List[str] = ["Global Search"]) -> Dict:
        """Run evaluation on all test cases."""
        test_cases = self.load_test_cases()
        results = []
        
        print(f"Starting evaluation of {len(test_cases)} test cases...")
        
        for search_type in search_types:
            print(f"\n=== Evaluating with {search_type} ===")
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"Progress: {i}/{len(test_cases)}")
                result = await self.evaluate_single_case(test_case, search_type)
                results.append(result)
        
        # Calculate overall statistics
        all_metrics = [r['metrics'] for r in results]
        avg_metrics = {
            'factual_accuracy': sum(m['factual_accuracy'] for m in all_metrics) / len(all_metrics),
            'relevance': sum(m['relevance'] for m in all_metrics) / len(all_metrics),
            'bleu_score': sum(m['bleu_score'] for m in all_metrics) / len(all_metrics)
        }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_cases': len(test_cases),
            'search_types': search_types,
            'average_metrics': avg_metrics,
            'detailed_results': results
        }

    def save_results(self, results: Dict, filename: str = None):
        """Save evaluation results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"
        
        filepath = Path(filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {filepath}")
        return filepath

    def print_summary(self, results: Dict):
        """Print a summary of evaluation results."""
        print("\n" + "="*60)
        print("GRAPHRAG EVALUATION SUMMARY")
        print("="*60)
        print(f"Total test cases: {results['total_cases']}")
        print(f"Search methods: {', '.join(results['search_types'])}")
        print(f"Evaluation date: {results['timestamp']}")
        
        print("\nAVERAGE METRICS:")
        print("-" * 30)
        avg = results['average_metrics']
        print(f"Factual Accuracy: {avg['factual_accuracy']:.3f}")
        print(f"Relevance:        {avg['relevance']:.3f}")
        print(f"BLEU Score:       {avg['bleu_score']:.3f}")
        
        # Show top and bottom performers
        detailed = results['detailed_results']
        if detailed:
            print("\nTOP PERFORMERS (by average score):")
            print("-" * 40)
            
            # Calculate average score for each result
            for result in detailed:
                metrics = result['metrics']
                avg_score = (metrics['factual_accuracy'] + metrics['relevance'] + metrics['bleu_score']) / 3
                result['avg_score'] = avg_score
            
            # Sort by average score
            top_results = sorted(detailed, key=lambda x: x['avg_score'], reverse=True)[:3]
            
            for i, result in enumerate(top_results, 1):
                print(f"{i}. {result['id']}: {result['avg_score']:.3f}")
                print(f"   Question: {result['question'][:80]}...")
            
            print("\nLOWEST PERFORMERS:")
            print("-" * 20)
            bottom_results = sorted(detailed, key=lambda x: x['avg_score'])[:3]
            
            for i, result in enumerate(bottom_results, 1):
                print(f"{i}. {result['id']}: {result['avg_score']:.3f}")
                print(f"   Question: {result['question'][:80]}...")

async def main():
    """Main evaluation function."""
    print("GraphRAG Evaluation Tool")
    print("=" * 40)
    
    # Initialize evaluator
    evaluator = GraphRAGEvaluator()
    
    # Run evaluation (you can test multiple search types)
    search_types = ["Global Search"]  # Start with Global Search
    
    try:
        results = await evaluator.run_evaluation(search_types)
        
        # Print summary
        evaluator.print_summary(results)
        
        # Save results
        filepath = evaluator.save_results(results)
        
        print(f"\nEvaluation complete! Check {filepath} for detailed results.")
        
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user.")
    except Exception as e:
        print(f"Error during evaluation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 