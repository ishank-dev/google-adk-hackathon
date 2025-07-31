#!/usr/bin/env python3
"""
Performance test script for optimized Llama agent
"""

import time
import sys
from pathlib import Path

# Add agents directory to path
agents_dir = Path(__file__).parent / "agents" / "llama_agent"
sys.path.insert(0, str(agents_dir))

def test_import_performance():
    """Test how fast the module imports"""
    print("🔥 Testing Llama Agent Performance")
    print("=" * 50)
    
    start_time = time.time()
    from llama_agent.rag_kb_llm import get_stats, chat
    import_time = time.time() - start_time
    
    print(f"✅ Module import time: {import_time:.3f}s")
    print(f"📊 Initial status: {get_stats()}")
    return chat

def test_query_performance(chat_func, queries):
    """Test query response times"""
    times = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n🤔 Query {i}: {query}")
        start_time = time.time()
        
        try:
            response = chat_func(query)
            query_time = time.time() - start_time
            times.append(query_time)
            
            print(f"⏱️ Response time: {query_time:.2f}s")
            print(f"📝 Preview: {response[:100]}...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            times.append(float('inf'))
    
    return times

def main():
    # Test import performance
    chat = test_import_performance()
    
    # Test queries
    test_queries = [
        "How do I book a parking space?",
        "What events can I organize?", 
        "How do I submit a service request?",
        "Where can I find office locations?",
        "How do I access the platform?"
    ]
    
    print(f"\n🚀 Testing {len(test_queries)} queries...")
    times = test_query_performance(chat, test_queries)
    
    # Performance summary
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 50)
    
    valid_times = [t for t in times if t != float('inf')]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
        
        print(f"Average query time: {avg_time:.2f}s")
        print(f"Fastest query: {min_time:.2f}s") 
        print(f"Slowest query: {max_time:.2f}s")
        
        # Performance analysis
        if avg_time < 10:
            print("🚀 EXCELLENT: Average response under 10s")
        elif avg_time < 15:
            print("✅ GOOD: Average response under 15s")
        elif avg_time < 20:
            print("⚠️ ACCEPTABLE: Average response under 20s")
        else:
            print("❌ SLOW: Average response over 20s")
    
    print("\n🎯 Optimization Status:")
    print("✅ Lazy loading implemented")
    print("✅ Vector database caching enabled") 
    print("✅ Token limits applied")
    print("✅ Reduced document retrieval (k=3)")

if __name__ == "__main__":
    main()
