# GraphRAG Housing Schemes Explorer

## The Challenge

This project documents a challenge that I took on before returning to college for my masters. Back in my final year, we built a RAG (Retrieval-Augmented Generation) LLM and at the time it completely blew my mind - I found it really difficult to wrap my head around.

So I decided to recreate the project to better understand it. I started building what I later discovered was a "traditional" RAG system using vector embeddings. What we thought was cutting edge 12 months ago is now considered the old school approach!

That's when I stumbled upon Microsoft's GraphRAG, which is apparently the new hotness in the RAG world.

## What This Project Actually Does

The real motivation behind this isn't just the technical challenge - it's solving a genuine problem. Government housing schemes exist everywhere, but they're nearly impossible to navigate. The language is confusing, the eligibility criteria are buried in legal jargon, and finding the ones that actually apply to you feels like solving a puzzle nobody wants you to solve.

I wanted to make this information easily accessible to everyone, without needing a PhD in government bureaucracy.

## How GraphRAG Works (And Why It's Different)

Instead of just throwing documents into a vector database and hoping for the best, GraphRAG does something smarter:

1. **Knowledge Graph Construction**: It analyzes your documents and builds a knowledge graph, identifying entities (in my case, housing schemes) and their relationships
2. **Few-Shot Prompting**: You define prompts with examples of what good entity extraction looks like
3. **Community Detection**: It finds clusters and communities within the data
4. **Better Retrieval**: When you ask questions, it can understand context and relationships way better than traditional vector search

## What's In This Repo

- **`scrapers/`** - Scripts to gather housing scheme data from various government sources
- **`my_graphrag_project/`** - The main GraphRAG implementation with all the processing cache
- **`graphrag_ui/`** - A simple UI to interact with the knowledge graph (because nobody wants to use command line for this)
- **`evaluation/`** - Tests and evaluation metrics to see if this thing actually works better than traditional methods

## The Reality Check

This is very much a learning project. I'm documenting my journey from "traditional RAG is magic" to "oh wait, there's an even better way to do this." If you're also trying to make sense of government bureaucracy or just want to see someone figure out GraphRAG in real-time, you're in the right place.

I have also come to the harsh realisation of how expensive it is to use an  OpenAI API in this project. It has made me interested in exploring the idea of hosting a LLM locally using ollama but that could be another project in itself!