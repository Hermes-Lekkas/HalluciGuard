# HalluciGuard Troubleshooting Guide

This guide helps you diagnose and fix common issues when using HalluciGuard.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [API Key Problems](#api-key-problems)
3. [Provider Connection Errors](#provider-connection-errors)
4. [Hallucination Detection Issues](#hallucination-detection-issues)
5. [Cache Problems](#cache-problems)
6. [Streaming Issues](#streaming-issues)
7. [LangChain Integration](#langchain-integration)
8. [Benchmark/Leaderboard Issues](#benchmarkleaderboard-issues)

---

## Installation Issues

### Missing Dependencies

**Error:**
```
ModuleNotFoundError: No module named 'openai'/'anthropic'/'google'
```

**Solution:**
Install the required provider package(s):

```bash
# For OpenAI
pip install openai

# For Anthropic
pip install anthropic

# For Google
pip install google-genai

# Install all at once
pip install halluciGuard[all]
```

### Version Conflicts

**Error:**
```
ImportError: cannot import name '...' from 'openai'
```

**Solution:**
Update to the latest version of the provider SDK:

```bash
pip install --upgrade openai anthropic google-genai
```

---

## API Key Problems

### Invalid API Key

**Error:**
```
InvalidAPIKeyError: OpenAI API key is invalid or missing.
```

**Help Message:**
> Set your API key as an environment variable: `export OPENAI_API_KEY='sk-...'`
> Or pass it when creating the client: `openai.OpenAI(api_key='sk-...')`
> You can find your API key at: https://platform.openai.com/api-keys

**Solutions:**

1. **Set environment variable (recommended):**
   ```bash
   export OPENAI_API_KEY='sk-your-key-here'
   ```

2. **Pass directly to client:**
   ```python
   import openai
   from halluciGuard import Guard
   
   client = openai.OpenAI(api_key='sk-your-key-here')
   guard = Guard(client=client, provider="openai")
   ```

3. **Use a .env file:**
   ```bash
   # .env file
   OPENAI_API_KEY=sk-your-key-here
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```
   
   ```python
   from dotenv import load_dotenv
   load_dotenv()  # Loads from .env file
   ```

### Missing API Key

**Error:**
```
ClientInitializationError: OpenAI client not initialized. 
client must be provided for OpenAI provider.
```

**Solution:**
Make sure you're passing a properly initialized client:

```python
import openai
from halluciGuard import Guard

# Wrong - no client
guard = Guard(provider="openai")  # ❌

# Right - with client
client = openai.OpenAI()  # Uses OPENAI_API_KEY env var
guard = Guard(client=client, provider="openai")  # ✅
```

---

## Provider Connection Errors

### Rate Limiting

**Error:**
```
ProviderAPIError: openai rate limit exceeded (429)
```

**Help Message:**
> You've hit the rate limit. Wait a moment and retry, or upgrade your plan.
> Consider implementing exponential backoff in your application.

**Solutions:**

1. **Wait and retry:**
   ```python
   import time
   import random
   
   def call_with_retry(guard, model, messages, max_retries=3):
       for attempt in range(max_retries):
           try:
               return guard.chat(model=model, messages=messages)
           except ProviderAPIError as e:
               if e.status_code == 429 and attempt < max_retries - 1:
                   wait = (2 ** attempt) + random.random()
                   time.sleep(wait)
               else:
                   raise
   ```

2. **Use a higher tier API plan** for increased rate limits.

### Model Not Found

**Error:**
```
ModelNotFoundError: Model 'gpt-5' not found for provider 'openai'
```

**Help Message:**
> The model name may be incorrect. Available models include: gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.
> Check https://platform.openai.com/models for available models.

**Solution:**
Use a valid model name:

```python
# Valid OpenAI models
guard.chat(model="gpt-4o", messages=[...])
guard.chat(model="gpt-4o-mini", messages=[...])
guard.chat(model="gpt-4-turbo", messages=[...])

# Valid Anthropic models
guard.chat(model="claude-sonnet-4.6", messages=[...])
guard.chat(model="claude-haiku-4-5-20251001", messages=[...])
```

### Ollama Connection Failed

**Error:**
```
ProviderAPIError: ollama - Connection refused
```

**Help Message:**
> Make sure Ollama is running locally. Start it with: `ollama serve`
> Or specify a different base_url if Ollama is running elsewhere.

**Solutions:**

1. **Start Ollama:**
   ```bash
   ollama serve
   ```

2. **Check Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. **Specify custom base_url:**
   ```python
   guard = Guard(
       provider="ollama",
       base_url="http://your-server:11434"
   )
   ```

---

## Hallucination Detection Issues

### All Responses Flagged as Hallucinations

**Symptom:**
Every response has a low trust score, even accurate ones.

**Possible Causes & Solutions:**

1. **Overly sensitive threshold:**
   ```python
   # Lower the threshold (default is 0.7)
   config = GuardConfig(trust_threshold=0.5)
   guard = Guard(client=client, provider="openai", config=config)
   ```

2. **Claims extracted incorrectly:**
   ```python
   # Reduce max claims per response
   config = GuardConfig(max_claims_per_response=5)
   ```

3. **Web verification returning false negatives:**
   ```python
   # Disable web verification if search API is unreliable
   config = GuardConfig(enable_web_verification=False)
   ```

### No Hallucinations Detected

**Symptom:**
Obviously false responses get high trust scores.

**Possible Causes & Solutions:**

1. **Claim extraction missing claims:**
   - Check if claims are being extracted at all
   - Enable verbose logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Scorer not running:**
   ```python
   # Make sure scoring is enabled
   config = GuardConfig(
       enable_web_verification=True,  # Enable web verification
       search_provider="tavily",       # Requires TAVILY_API_KEY
   )
   ```

### Claim Extraction Fallback to Heuristics

**Warning in logs:**
```
LLM-based claim extraction failed, falling back to heuristics.
```

**Cause:**
The LLM used for claim extraction failed or is not configured.

**Solutions:**

1. **Ensure API key is set for the extraction model:**
   ```bash
   export OPENAI_API_KEY='sk-...'
   ```

2. **Use the same provider for extraction:**
   ```python
   # HalluciGuard uses the same client for extraction
   guard = Guard(client=client, provider="openai")
   ```

---

## Cache Problems

### Cache Permission Denied

**Error:**
```
CachePermissionError: Cannot write to cache directory '/path/.halluciguard_cache'
```

**Help Message:**
> Check directory permissions: `ls -la /path/.halluciguard_cache`
> Fix with: `chmod 755 /path/.halluciguard_cache`
> Or set a different cache directory in config.

**Solutions:**

1. **Fix permissions:**
   ```bash
   chmod 755 .halluciguard_cache
   ```

2. **Use a different cache directory:**
   ```python
   config = GuardConfig(
       cache_enabled=True,
       cache_dir="/tmp/halluciguard_cache"
   )
   ```

3. **Disable caching:**
   ```python
   config = GuardConfig(cache_enabled=False)
   ```

### Stale Cache Data

**Symptom:**
Old/incorrect scores persist across runs.

**Solution:**
Clear the cache:

```bash
rm -rf .halluciguard_cache
```

Or programmatically:

```python
import shutil
shutil.rmtree(".halluciguard_cache", ignore_errors=True)
```

---

## Streaming Issues

### Streaming Not Supported

**Error:**
```
StreamingError: Streaming not supported for provider 'ollama'
```

**Solution:**
Streaming is currently supported for OpenAI, Anthropic, and Google. For Ollama, use non-streaming calls:

```python
# Use regular chat instead of stream
response = guard.chat(model="llama2", messages=[...])
```

### Stream Iterator Not Consumed

**Symptom:**
Streaming response object returned but no content processed.

**Solution:**
Make sure to iterate over the stream:

```python
# Wrong - doesn't process the stream
response = guard.stream(model="gpt-4o", messages=[...])
# Nothing happens!

# Right - iterate over the stream
for chunk in guard.stream(model="gpt-4o", messages=[...]):
    print(chunk.content, end="", flush=True)
```

---

## LangChain Integration

### Callback Not Firing

**Symptom:**
HalluciGuardCallbackHandler installed but not detecting hallucinations.

**Solutions:**

1. **Attach to the LLM correctly:**
   ```python
   from langchain_openai import ChatOpenAI
   from halluciGuard.integrations.langchain import HalluciGuardCallbackHandler
   
   callback = HalluciGuardCallbackHandler()
   llm = ChatOpenAI(
       model="gpt-4o",
       callbacks=[callback]  # Must be in callbacks list
   )
   ```

2. **Check callback is being used:**
   ```python
   # Invoke with callbacks
   response = llm.invoke("What is the capital of France?", config={"callbacks": [callback]})
   ```

### HalluciGuardLLMWrapper Issues

**Error:**
```
TypeError: 'HalluciGuardLLMWrapper' object is not callable
```

**Solution:**
Use the wrapper's methods, not call it directly:

```python
from halluciGuard.integrations.langchain import create_guarded_llm

guarded_llm = create_guarded_llm(
    provider="openai",
    model="gpt-4o"
)

# Use invoke method
response = guarded_llm.invoke("Your prompt here")
```

---

## Benchmark/Leaderboard Issues

### No Results to Aggregate

**Error:**
```
BenchmarkError: No benchmark results to aggregate
```

**Solution:**
Run benchmark cases before aggregating:

```python
from halluciGuard import Guard
from halluciGuard.leaderboard import BenchmarkRunner, BenchmarkDataset

dataset = BenchmarkDataset()
runner = BenchmarkRunner(dataset)

# Run benchmark first
results = runner.run_model(guard, "gpt-4o")

# Then aggregate
scores = runner.aggregate_scores(results)
```

### Dataset Loading Failed

**Error:**
```
DatasetError: Failed to load benchmark dataset from 'path.json'
```

**Solutions:**

1. **Check file exists:**
   ```python
   import os
   print(os.path.exists("benchmark_cases.json"))
   ```

2. **Validate JSON format:**
   ```python
   import json
   with open("benchmark_cases.json") as f:
       data = json.load(f)  # Will raise if invalid
   ```

3. **Use default dataset:**
   ```python
   dataset = BenchmarkDataset()  # Uses built-in cases
   ```

---

## Getting More Help

If your issue isn't covered here:

1. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check error details:**
   All HalluciGuard errors include a `help_message` attribute:
   ```python
   try:
       guard.chat(model="gpt-4o", messages=[...])
   except HalluciGuardError as e:
       print(f"Error: {e}")
       print(f"Help: {e.help_message}")
       print(f"Code: {e.error_code}")
   ```

3. **Open an issue:**
   - GitHub: https://github.com/your-repo/halluciGuard/issues
   - Include: error message, stack trace, Python version, package versions

4. **Check the documentation:**
   - README.md for quick start
   - examples/ directory for usage examples