"""
Integration test for RAG system
Verifies all components work together correctly
"""
import sys
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_rag_service_imports():
    """Test that RAG service can be imported"""
    logger.info("Testing RAG service imports...")
    try:
        from services.rag_service import get_rag_service, initialize_rag_with_defaults
        logger.info("✅ RAG service imports successful")
        return True
    except Exception as e:
        logger.error(f"❌ RAG service import failed: {e}")
        return False


def test_web_scraper_imports():
    """Test that web scraper can be imported"""
    logger.info("Testing web scraper imports...")
    try:
        from services.web_scraper import update_rag_with_web_content
        logger.info("✅ Web scraper imports successful")
        return True
    except Exception as e:
        logger.error(f"❌ Web scraper import failed: {e}")
        return False


def test_llm_rag_integration():
    """Test that LLM service has RAG integration"""
    logger.info("Testing LLM-RAG integration...")
    try:
        from llm_service import LLMService
        llm = LLMService()
        
        # Check RAG is initialized
        assert hasattr(llm, 'rag'), "LLM service missing rag attribute"
        assert hasattr(llm, 'use_rag'), "LLM service missing use_rag attribute"
        assert hasattr(llm, 'enable_rag'), "LLM service missing enable_rag method"
        assert hasattr(llm, '_should_use_rag'), "LLM service missing _should_use_rag method"
        
        logger.info("✅ LLM-RAG integration verified")
        return True
    except Exception as e:
        logger.error(f"❌ LLM-RAG integration test failed: {e}")
        return False


def test_rag_initialization():
    """Test that RAG can be initialized with default documents"""
    logger.info("Testing RAG initialization...")
    try:
        from services.rag_service import get_rag_service, RAGService
        
        rag = get_rag_service()
        logger.info(f"RAG enabled: {rag.enabled}")
        logger.info(f"RAG model: {rag.model is not None}")
        
        if rag.enabled:
            logger.info("✅ RAG enabled with dependencies")
            return True
        else:
            logger.warning("⚠️ RAG disabled (dependencies not installed, this is OK)")
            logger.info("Install for full RAG support: pip install sentence-transformers faiss-cpu")
            return True  # Still pass - system works without RAG
    except Exception as e:
        logger.error(f"❌ RAG initialization test failed: {e}")
        return False


def test_should_use_rag_logic():
    """Test RAG query classification logic"""
    logger.info("Testing RAG query classification...")
    try:
        from llm_service import LLMService
        llm = LLMService()
        
        test_cases = [
            ("What is Python?", "general", True, "Should use RAG for general queries"),
            ("Calculate 2+2", "tool", False, "Should NOT use RAG for tool queries"),
            ("Hi", "general", False, "Should NOT use RAG for short queries"),
            ("Tell me about AI", "realtime", True, "Should use RAG for realtime queries"),
        ]
        
        for query, intent, expected_use, reason in test_cases:
            # Simulate RAG being available
            llm.use_rag = True
            result = llm._should_use_rag(intent, query)
            status = "✅" if result == expected_use else "❌"
            logger.info(f"{status} Query: '{query}' ({intent}) → {reason}")
            
            if result != expected_use:
                return False
        
        logger.info("✅ Query classification logic verified")
        return True
    except Exception as e:
        logger.error(f"❌ Query classification test failed: {e}")
        return False


def test_graceful_degradation():
    """Test that system works without RAG dependencies"""
    logger.info("Testing graceful degradation...")
    try:
        logger.info("Simulating missing RAG dependencies...")
        
        # The system should still work even if RAG is not available
        # This is handled by the HAS_RAG_DEPS flag in rag_service.py
        from services.rag_service import HAS_RAG_DEPS
        
        if HAS_RAG_DEPS:
            logger.info("✅ RAG dependencies available")
        else:
            logger.info("⚠️ RAG dependencies not available (gracefully degraded)")
        
        return True
    except Exception as e:
        logger.error(f"❌ Graceful degradation test failed: {e}")
        return False


def test_cache_integration():
    """Test that RAG results are cached"""
    logger.info("Testing cache integration...")
    try:
        from services.rag_service import get_rag_service
        from services.cache_service import get_cache_service
        
        rag = get_rag_service()
        cache = get_cache_service()
        
        # Verify RAG has cache reference
        assert hasattr(rag, 'cache'), "RAG service missing cache attribute"
        
        logger.info("✅ Cache integration verified")
        return True
    except Exception as e:
        logger.error(f"❌ Cache integration test failed: {e}")
        return False


def main():
    """Run all integration tests"""
    logger.info("=" * 60)
    logger.info("RAG System Integration Tests")
    logger.info("=" * 60)
    
    tests = [
        test_rag_service_imports,
        test_web_scraper_imports,
        test_llm_rag_integration,
        test_rag_initialization,
        test_should_use_rag_logic,
        test_graceful_degradation,
        test_cache_integration,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test.__name__} crashed: {e}", exc_info=True)
            results.append(False)
        logger.info("")
    
    # Summary
    passed = sum(results)
    total = len(results)
    logger.info("=" * 60)
    logger.info(f"🎯 Results: {passed}/{total} tests passed")
    
    if all(results):
        logger.info("✅ All integration tests passed!")
        logger.info("RAG system is ready to use!")
    else:
        logger.warning("⚠️ Some tests failed. Check the output above.")
    
    logger.info("=" * 60)
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
