#!/usr/bin/env python3
"""
RAG System Example and Quick Test
Demonstrates how to use the Retrieval-Augmented Generation system
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Example 1: Initialize RAG with documents
def example_add_documents():
    """Add custom documents to RAG knowledge base"""
    from services.rag_service import get_rag_service
    
    logger.info("📚 Example 1: Adding custom documents to RAG")
    
    rag = get_rag_service()
    if not rag.enabled:
        logger.warning("RAG not enabled. Install: pip install sentence-transformers faiss-cpu")
        return
    
    # Example documents about Python
    documents = [
        "Python is a high-level, interpreted programming language known for its simplicity and readability. "
        "It's widely used in web development, data science, machine learning, and automation.",
        
        "FastAPI is a modern, fast web framework for building APIs with Python. "
        "It automatically generates API documentation and is built on standards like OpenAPI.",
        
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data. "
        "Popular ML libraries in Python include scikit-learn, TensorFlow, and PyTorch.",
    ]
    
    success = rag.add_documents(documents, document_ids=["python_basics", "fastapi_guide", "ml_intro"])
    
    if success:
        logger.info(f"✅ Added {len(documents)} documents")
        stats = rag.get_stats()
        logger.info(f"📊 RAG now has {stats['document_count']} documents")
    else:
        logger.warning("Failed to add documents")


# Example 2: Retrieve context for a query
def example_retrieve_context():
    """Demonstrate context retrieval"""
    from services.rag_service import get_rag_service
    
    logger.info("\n🔍 Example 2: Retrieving context")
    
    rag = get_rag_service()
    if not rag.enabled:
        logger.warning("RAG not enabled")
        return
    
    # Test query
    query = "What is Python used for?"
    logger.info(f"Query: {query}")
    
    result = rag.retrieve_context(query, top_k=3)
    
    if result['found']:
        logger.info(f"✅ Found {len(result['sources'])} relevant documents")
        logger.info(f"Context:\n{result['context'][:200]}...")
        for i, source in enumerate(result['sources'], 1):
            logger.info(f"  Source {i} (similarity: {source['similarity']:.2f}): {source['document_id']}")
    else:
        logger.info("No relevant documents found")


# Example 3: Use RAG with LLM Service
def example_rag_with_llm():
    """Demonstrate RAG integration with LLM"""
    from llm_service import LLMService
    from services.rag_service import initialize_rag_with_defaults
    
    logger.info("\n🤖 Example 3: RAG with LLM Service")
    
    # Initialize RAG
    if not initialize_rag_with_defaults():
        logger.warning("RAG initialization failed")
        return
    
    # Initialize LLM
    llm = LLMService()
    llm.enable_rag()
    
    logger.info(f"RAG enabled: {llm.use_rag}")
    logger.info("RAG is now active and will be used for relevant queries")


# Example 4: API Endpoints
def example_api_endpoints():
    """Demonstrate available API endpoints"""
    logger.info("\n🌐 Example 4: RAG API Endpoints")
    
    endpoints = [
        ("GET", "/api/rag/stats", "Get RAG statistics"),
        ("POST", "/api/rag/add_documents", "Add documents to RAG knowledge base"),
        ("POST", "/api/rag/update_web_content", "Update RAG with web content"),
        ("POST", "/api/rag/clear", "Clear RAG knowledge base"),
    ]
    
    logger.info("Available RAG endpoints:")
    for method, path, desc in endpoints:
        logger.info(f"  [{method:4}] {path:35} - {desc}")


# Example 5: Web Scraping
def example_web_scraping():
    """Demonstrate web scraping for dynamic content"""
    from services.web_scraper import update_rag_with_web_content
    
    logger.info("\n🌐 Example 5: Dynamic Web Content")
    
    topics = ["Artificial Intelligence", "Python Programming", "Machine Learning"]
    logger.info(f"Updating RAG with content about: {topics}")
    
    # Note: This is a demonstration - actual web scraping may require additional dependencies
    for topic in topics:
        logger.info(f"  Scraping: {topic}")
        # success = update_rag_with_web_content(topic)
    
    logger.info("Web scraping is available to keep RAG knowledge base fresh")


# Example 6: Query Classification and Routing
def example_query_routing():
    """Demonstrate how queries are routed"""
    logger.info("\n📍 Example 6: Query Routing and RAG Usage")
    
    examples = [
        ("What is Python?", "Should use RAG - general knowledge query"),
        ("Calculate 2 + 2", "Should NOT use RAG - calculator query"),
        ("Hi there!", "Should NOT use RAG - greeting is too short"),
        ("Tell me about machine learning algorithms", "Should use RAG - detailed factual query"),
    ]
    
    for query, note in examples:
        logger.info(f"  Query: '{query}' → {note}")


def main():
    """Run examples"""
    logger.info("=" * 60)
    logger.info("RAG (Retrieval-Augmented Generation) System Examples")
    logger.info("=" * 60)
    
    # Run examples
    example_add_documents()
    example_retrieve_context()
    example_rag_with_llm()
    example_api_endpoints()
    example_web_scraping()
    example_query_routing()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ RAG system is ready to enhance your chatbot!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
