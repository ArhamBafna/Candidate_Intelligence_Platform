# Ollama Setup Guide (Windows)

This document provides a concise step-by-step guide to set up **Ollama** on a Windows computer for the **Candidate Intelligence Platform (CIP)** offline AI extraction pipeline.

---

## 1. Install Ollama on Windows

Choose **one** of the following options:

### Option A: Official Installer (Recommended)
1. Download the Windows installer from [ollama.com/download/windows](https://ollama.com/download/windows).
2. Run `OllamaSetup.exe` and follow the installer steps.

### Option B: Windows Package Manager (winget)
Run in PowerShell:
```powershell
winget install Ollama.Ollama
```

*Note: The installer automatically starts the Ollama background service running on `http://localhost:11434`.*

---

## 2. Pull Required LLM Model

The default model used by CIP is **`llama3.2`** (configured in [`config/settings.py`](file:///c:/Users/bafna_ci/OneDrive/Desktop/Candidate_Intelligence_Platform/config/settings.py#L9)).

Open PowerShell or Command Prompt and download the model:
```powershell
ollama pull llama3.2
```

---

## 3. Verify Ollama Setup

### Step A: Test Ollama CLI
Run a quick test in PowerShell:
```powershell
ollama run llama3.2 "Hello"
```

### Step B: Test CIP Integration
Run the automated test suite for the local LLM fallback module:
```powershell
# Using uv:
uv run pytest tests/test_local_llm_fallback.py

# Or using virtual environment:
pytest tests/test_local_llm_fallback.py
```

---

## 4. Configuration Options (Optional)

- **Change LLM Model**: Set the environment variable `CIP_LLM_MODEL` or update `llm_model` in [`config/settings.py`](file:///c:/Users/bafna_ci/OneDrive/Desktop/Candidate_Intelligence_Platform/config/settings.py#L9):
  ```powershell
  $env:CIP_LLM_MODEL="llama3.1"
  ```
- **Custom Ollama Endpoint**: If Ollama is running on a non-default host/port, set:
  ```powershell
  $env:OLLAMA_HOST="http://localhost:11434"
  ```
