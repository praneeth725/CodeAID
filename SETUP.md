# CodeAid — Complete Setup & Installation Guide
## Windows 10 · Python 3.10+ · VS Code

---

## PART 1 — Prerequisites

### Step 1: Install Git for Windows
Git is needed to clone your repository later and is used internally by some packages.

1. Go to: https://git-scm.com/download/win
2. Download the **64-bit Git for Windows Setup**
3. Run the installer — accept all defaults
4. When asked about default branch name, select **main**
5. Finish installation

**Verify:**
```
git --version
```
You should see something like `git version 2.x.x`

---

### Step 2: Verify Python version
Open Command Prompt (Win + R → type `cmd` → Enter):
```
python --version
```
You need **Python 3.10 or higher**. If you see 3.10.x, 3.11.x, or 3.12.x — you're good.

If Python is not found, download from: https://www.python.org/downloads/
- Check ✅ "Add Python to PATH" during installation

---

### Step 3: Install VS Code
If not already installed:
1. Go to: https://code.visualstudio.com/
2. Download and install
3. Open VS Code

**Install these VS Code extensions** (open Extensions panel with Ctrl+Shift+X):
- **Python** (by Microsoft)
- **Pylance** (by Microsoft)

---

## PART 2 — Project Setup

### Step 4: Create the project folder
Open Command Prompt and run:
```cmd
mkdir C:\Projects\CodeAid
cd C:\Projects\CodeAid
```

### Step 5: Create a Python virtual environment
A virtual environment keeps CodeAid's packages isolated from your system Python.

```cmd
python -m venv venv
```

**Activate the virtual environment:**
```cmd
venv\Scripts\activate
```

You should now see `(venv)` at the start of your command prompt line.

> ⚠️ Important: You must activate the venv every time you open a new terminal to work on CodeAid.

---

### Step 6: Place all project files
Copy all CodeAid files into `C:\Projects\CodeAid\` so the structure looks like this:

```
CodeAid/
├── app.py
├── requirements.txt
├── SETUP.md               ← this file
├── core/
│   ├── __init__.py
│   └── repo_loader.py
├── agents/
│   ├── __init__.py
│   ├── scanner.py
│   ├── repair.py
│   ├── verifier.py
│   ├── explain.py
│   ├── llm_agent.py
│   ├── coordinator.py
│   └── project_understanding.py
└── utils/
    ├── __init__.py
    ├── metrics.py
    └── codexglue_loader.py
```

---

### Step 7: Install dependencies
With your virtual environment activated, run:

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- `streamlit` — the web UI framework
- `plotly`, `pandas` — charts and data display
- `requests` — GitHub URL downloading
- `radon` — code complexity metrics
- `openai` — OpenAI API client (optional, only needed if you use OpenAI LLM)
- `transformers`, `torch` — HuggingFace models (optional, only needed if you use HuggingFace LLM)
- `datasets` — HuggingFace datasets (for CodeXGLUE evaluation)
- `scikit-learn` — metrics utilities
- `astor` — AST code generation
- `black` — code formatter

> ⏱️ This may take 3-5 minutes. The torch package alone is ~200MB.

---

### Step 8: Open in VS Code
```cmd
code .
```

This opens the CodeAid folder in VS Code.

**Select the Python interpreter:**
1. Press `Ctrl+Shift+P`
2. Type "Python: Select Interpreter"
3. Choose the one inside your `venv` folder (it will show something like `.\venv\Scripts\python.exe`)

---

## PART 3 — Running CodeAid

### Step 9: Run the application
In your terminal (with venv activated):

```cmd
streamlit run app.py
```

Streamlit will start and automatically open your browser to:
```
http://localhost:8501
```

You should see the CodeAid dashboard.

---

### Step 10: Using the app

**To analyze a public GitHub repo:**
1. Select "🌐 Public GitHub URL"
2. Paste a URL like: `https://github.com/username/repository`
3. Click **▶ Analyze**

**To analyze a local project:**
1. Zip your project folder (right-click → Send to → Compressed folder)
2. Select "📦 Upload ZIP file"
3. Upload your .zip
4. Click **▶ Analyze**

**Optional — Enable LLM Agent:**
- In the sidebar, choose "OpenAI GPT-3.5" and enter your API key, OR
- Choose "HuggingFace CodeT5" (free — downloads model on first use, ~300MB)

---

## PART 4 — Development in VS Code

### Running with VS Code Terminal
1. Open VS Code
2. Open Terminal: `Ctrl + backtick`
3. Activate venv: `venv\Scripts\activate`
4. Run: `streamlit run app.py`

### Stopping the app
Press `Ctrl+C` in the terminal.

### Re-running after code changes
Streamlit auto-reloads when you save a file. No need to restart manually.

---

## PART 5 — Pushing to GitHub

### Step 11: Create a .gitignore
Create a file named `.gitignore` in `C:\Projects\CodeAid\` with this content:

```
venv/
__pycache__/
*.pyc
*.pyo
.env
.streamlit/secrets.toml
*.egg-info/
dist/
build/
.pytest_cache/
```

### Step 12: Initialize and push to GitHub

```cmd
git init
git add .
git commit -m "Initial commit: CodeAid v1.0"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub username and repository name.

> You'll need to create the repository on GitHub first at https://github.com/new

---

## PART 6 — Troubleshooting

### "ModuleNotFoundError" for any package
Make sure your venv is activated:
```cmd
venv\Scripts\activate
pip install -r requirements.txt
```

### Port 8501 already in use
```cmd
streamlit run app.py --server.port 8502
```

### Streamlit not recognized as a command
```cmd
python -m streamlit run app.py
```

### HuggingFace model download fails
Check your internet connection. The model downloads to:
`C:\Users\YOUR_NAME\.cache\huggingface\`
If disk space is low (needs ~500MB free), clear the cache or use OpenAI instead.

### GitHub URL says "Could not download"
- Make sure the repository is **public** (private repos are not supported)
- Check the URL format: `https://github.com/username/repo`
- Some repos use `master` as the default branch — CodeAid auto-tries both

### "venv\Scripts\activate is not recognized"
Use PowerShell instead of Command Prompt, or enable script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then try activating again.

---

## PART 7 — Environment Variables (optional)

If you use OpenAI and don't want to enter the key every time, create a file:
`C:\Projects\CodeAid\.env`

```
OPENAI_API_KEY=sk-your-key-here
```

Then at the top of `app.py`, add after imports:
```python
from dotenv import load_dotenv
load_dotenv()
import os
openai_key = os.getenv("OPENAI_API_KEY", "")
```

Install dotenv: `pip install python-dotenv`

---

## Quick Reference — Commands

| Task | Command |
|------|---------|
| Activate venv | `venv\Scripts\activate` |
| Run CodeAid | `streamlit run app.py` |
| Install packages | `pip install -r requirements.txt` |
| Open in VS Code | `code .` |
| Deactivate venv | `deactivate` |
| Freeze packages | `pip freeze > requirements.txt` |

---
*CodeAid v1.0 — Final Year Project — B.Tech CSE*
