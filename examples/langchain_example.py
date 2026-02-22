#!/usr/bin/env python3
# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
HalluciGuard + LangChain Integration Examples

This file demonstrates how to use HalluciGuard with LangChain for
automatic hallucination detection in your LLM applications.

Requirements:
    pip install halluciGuard[langchain] langchain-openai
"""

import os
from typing import List


def example_1_callback_handler():
    """
    Example 1: Using HalluciGuardCallbackHandler with an existing LLM.
    
    This is the simplest integration - just add the callback handler
    to your existing LangChain LLM.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("Install langchain-openai: pip install langchain-openai")
        return
    
    from halluciGuard.integrations.langchain import HalluciGuardCallbackHandler
    
    print("=" * 60)
    print("Example 1: Callback Handler Integration")
    print("=" * 60)
    
    # Create the callback handler
    handler = HalluciGuardCallbackHandler(
        provider="openai",
        api_key=os.environ.get("OPENAI_API_KEY"),
        trust_threshold=0.6,
    )
    
    # Attach to your LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        callbacks=[handler],
    )
    
    # Run as normal
    response = llm.invoke("What did Einstein win the Nobel Prize for?")
    
    print(f"\n📝 Response: {response.content[:200]}...")
    
    # Access hallucination analysis
    if handler.last_result:
        result = handler.last_result
        print(f"\n🛡️ Trust Score: {result.trust_score:.2%}")
        print(f"✅ Is Trustworthy: {result.is_trustworthy}")
        print(f"⚠️ Flagged Claims: {len(result.flagged_claims)}")
        
        for claim in result.flagged_claims:
            print(f"   - [{claim.risk_level.value}] {claim.text[:50]}...")


def example_2_wrapper():
    """
    Example 2: Using HalluciGuardLLMWrapper for a cleaner interface.
    
    The wrapper provides a simpler API that returns GuardedLLMResult
    directly from invoke().
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("Install langchain-openai: pip install langchain-openai")
        return
    
    from halluciGuard.integrations.langchain import HalluciGuardLLMWrapper
    
    print("\n" + "=" * 60)
    print("Example 2: LLM Wrapper Integration")
    print("=" * 60)
    
    # Wrap your LLM
    base_llm = ChatOpenAI(model="gpt-4o-mini")
    llm = HalluciGuardLLMWrapper(
        base_llm,
        provider="openai",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    
    # Invoke returns GuardedLLMResult directly
    result = llm.invoke("Who invented the telephone?")
    
    print(f"\n📝 Content: {result.content[:200]}...")
    print(f"\n🛡️ Trust Score: {result.trust_score:.2%}")
    print(f"✅ Is Trustworthy: {result.is_trustworthy}")
    
    if result.guarded_response:
        print(f"\n📊 Summary: {result.guarded_response.summary()}")


def example_3_quick_setup():
    """
    Example 3: Quick setup with create_guarded_llm().
    
    The fastest way to get started - one function call.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("Install langchain-openai: pip install langchain-openai")
        return
    
    from halluciGuard.integrations.langchain import create_guarded_llm
    
    print("\n" + "=" * 60)
    print("Example 3: Quick Setup (One-Liner)")
    print("=" * 60)
    
    # One-line setup
    llm = create_guarded_llm(
        ChatOpenAI(model="gpt-4o-mini"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        trust_threshold=0.6,
    )
    
    # Use normally
    result = llm.invoke("What is the capital of Australia?")
    
    print(f"\n📝 Content: {result.content}")
    print(f"\n🛡️ Trust Score: {result.trust_score:.2%}")
    
    if not result.is_trustworthy:
        print(f"⚠️ Warning: {len(result.flagged_claims)} claims flagged!")


def example_4_rag_verification():
    """
    Example 4: RAG-aware hallucination detection.
    
    Verify LLM responses against your own retrieved context.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("Install langchain-openai: pip install langchain-openai")
        return
    
    from halluciGuard.integrations.langchain import HalluciGuardLLMWrapper
    
    print("\n" + "=" * 60)
    print("Example 4: RAG Context Verification")
    print("=" * 60)
    
    # Your RAG context (e.g., from a vector store)
    rag_context: List[str] = [
        "Albert Einstein was born on March 14, 1879, in Ulm, Germany.",
        "Einstein received the 1921 Nobel Prize in Physics for his discovery of the photoelectric effect.",
        "He did NOT receive the Nobel Prize for the theory of relativity.",
    ]
    
    # Create wrapper with RAG context
    base_llm = ChatOpenAI(model="gpt-4o-mini")
    llm = HalluciGuardLLMWrapper(
        base_llm,
        provider="openai",
        api_key=os.environ.get("OPENAI_API_KEY"),
        rag_context=rag_context,
    )
    
    # Ask a question that might trigger hallucination
    result = llm.invoke("What did Einstein win the Nobel Prize for?")
    
    print(f"\n📝 Response: {result.content[:200]}...")
    print(f"\n🛡️ Trust Score: {result.trust_score:.2%}")
    print(f"📚 Verified against RAG context")
    
    # Check if claims match RAG context
    for claim in result.guarded_response.claims if result.guarded_response else []:
        if "RAG" in claim.sources:
            print(f"   ✅ Verified: {claim.text[:50]}...")


def example_5_streaming():
    """
    Example 5: Streaming with hallucination analysis.
    
    Stream tokens in real-time, then get analysis at the end.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("Install langchain-openai: pip install langchain-openai")
        return
    
    from halluciGuard.integrations.langchain import HalluciGuardLLMWrapper
    
    print("\n" + "=" * 60)
    print("Example 5: Streaming with Analysis")
    print("=" * 60)
    
    base_llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)
    llm = HalluciGuardLLMWrapper(
        base_llm,
        provider="openai",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    
    print("\n📝 Streaming response: ")
    print("-" * 40)
    
    final_result = None
    for chunk in llm.stream("Explain quantum entanglement in one paragraph."):
        if hasattr(chunk, 'content') and chunk.content:
            print(chunk.content, end="", flush=True)
        elif hasattr(chunk, 'trust_score'):
            final_result = chunk
    
    print("\n" + "-" * 40)
    
    if final_result:
        print(f"\n🛡️ Trust Score: {final_result.trust_score:.2%}")
        print(f"⚠️ Flagged Claims: {len(final_result.flagged_claims)}")


def example_6_custom_callbacks():
    """
    Example 6: Custom callbacks for low trust and critical hallucinations.
    
    Take action when hallucinations are detected.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("Install langchain-openai: pip install langchain-openai")
        return
    
    from halluciGuard.integrations.langchain import HalluciGuardCallbackHandler
    from halluciGuard.models import Claim
    
    print("\n" + "=" * 60)
    print("Example 6: Custom Callbacks")
    print("=" * 60)
    
    def on_low_trust(result):
        """Called when trust score is below threshold."""
        print(f"\n⚠️ LOW TRUST ALERT: Score {result.trust_score:.2%}")
        print("   Consider verifying the response manually.")
    
    def on_critical(claims: List[Claim], result):
        """Called when critical hallucination is detected."""
        print(f"\n🚨 CRITICAL HALLUCINATION DETECTED!")
        for claim in claims:
            print(f"   - {claim.text}")
            print(f"     Confidence: {claim.confidence:.2%}")
    
    handler = HalluciGuardCallbackHandler(
        provider="openai",
        api_key=os.environ.get("OPENAI_API_KEY"),
        trust_threshold=0.7,
        on_low_trust=on_low_trust,
        on_critical=on_critical,
    )
    
    llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])
    
    # This might trigger callbacks
    response = llm.invoke("Tell me a surprising historical fact.")
    print(f"\n📝 Response: {response.content[:200]}...")


def example_7_chain_integration():
    """
    Example 7: Integration with LangChain chains.
    
    Use HalluciGuard in a larger LangChain pipeline.
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
    except ImportError:
        print("Install langchain-openai and langchain-core: pip install langchain-openai langchain-core")
        return
    
    from halluciGuard.integrations.langchain import HalluciGuardCallbackHandler
    
    print("\n" + "=" * 60)
    print("Example 7: Chain Integration")
    print("=" * 60)
    
    # Create handler
    handler = HalluciGuardCallbackHandler(
        provider="openai",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    
    # Create chain components
    llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])
    prompt = ChatPromptTemplate.from_template(
        "Tell me 3 interesting facts about {topic}. Be accurate!"
    )
    parser = StrOutputParser()
    
    # Create chain
    chain = prompt | llm | parser
    
    # Run chain
    result = chain.invoke({"topic": "the Roman Empire"})
    
    print(f"\n📝 Chain Output:\n{result[:300]}...")
    
    if handler.last_result:
        print(f"\n🛡️ Trust Score: {handler.last_result.trust_score:.2%}")


if __name__ == "__main__":
    print("\n🛡️ HalluciGuard + LangChain Integration Examples\n")
    
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️ Set OPENAI_API_KEY environment variable to run these examples.")
        print("\nExamples will run in simulation mode.\n")
    
    # Run examples
    # Note: These require actual API calls, so they're commented out by default
    # Uncomment to test with a real API key
    
    # example_1_callback_handler()
    # example_2_wrapper()
    # example_3_quick_setup()
    # example_4_rag_verification()
    # example_5_streaming()
    # example_6_custom_callbacks()
    # example_7_chain_integration()
    
    print("\n" + "=" * 60)
    print("To run these examples:")
    print("1. Set OPENAI_API_KEY environment variable")
    print("2. Uncomment the example functions above")
    print("=" * 60)
