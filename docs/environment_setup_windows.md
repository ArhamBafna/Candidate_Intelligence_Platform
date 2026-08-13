# Environment & Tools Setup Guide (Windows)

This document provides a concise guide to set up the necessary tools and runtime dependencies for **Candidate Intelligence Platform (CIP)** on Windows.

---

## 1. Tool Checklist & Current Status

| Tool | Status | Binary Path / Details |
|---|---|---|
| **Git** | Installed | `C:\Users\bafna_ci\AppData\Local\Programs\Git\cmd\git.exe` |
| **uv** | Installed | `C:\Users\bafna_ci\.local\bin\uv.exe` *(Needs PATH setup)* |
| **Python** | Installed (Managed by uv) | Python 3.14 (`C:\Users\bafna_ci\AppData\Roaming\uv\python\...`) |
| **Ollama** | Installed | Installed by user (Default model: `llama3.2`) |

---

## 2. Setting Up PATH (Required for `uv` & `python`)

Because `uv` was installed into `~/.local/bin`, Windows needs `C:\Users\bafna_ci\.local\bin` added to your User `PATH` so you can use `uv`, `python`, and `pytest` from any PowerShell window.

### Option A: Via PowerShell (Automated)
Run in PowerShell (User environment):
```powershell
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Users\bafna_ci\.local\bin",
    "User"
)
```
*After running this, restart your terminal/IDE for PATH changes to take effect.*

### Option B: Via GUI
1. Press `Win + R`, type `sysdm.cpl`, and press **Enter**.
2. Go to **Advanced** tab -> **Environment Variables**.
3. Under **User variables for bafna_ci**, select **Path** and click **Edit**.
4. Click **New** and add: `C:\Users\bafna_ci\.local\bin`
5. Click **OK** and restart terminal.

---

## 3. Installing `uv` (If setting up on a clean machine)

If setting up on another Windows machine from scratch:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## 4. Install Project Dependencies (`uv sync`)

Once `uv` is in your PATH (or using full path):

```powershell
# Navigate to project root
cd Candidate_Intelligence_Platform

# Install/sync Python and all dependencies into .venv
uv sync
```

---

## 5. Verify Full Environment & Tests

Run the test suite to confirm all components (FastAPI, SQLAlchemy, LanceDB, PyMuPDF, Ollama fallback) work:

```powershell
# Using uv:
uv run pytest

# Or directly activating virtualenv:
.\.venv\Scripts\activate
pytest
```
