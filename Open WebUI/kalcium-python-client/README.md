# Kalcium Monorepo

This is a monorepo containing both the **Kalcium Client** and the **MCP Server**, structured using a `src/` layout and managed with [uv](https://github.com/astral-sh/uv) for modern Python dependency management.

---

## 🗂️ Project Structure

```
kalcium_client/
├── pyproject.toml
├── readme.md
├── uv.lock
├── src/
│   ├── kalcium_client/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── kalcium_tag_functions.py
│   │   ├── kalcium_termchecker.py
│   │   ├── kalcium_translator.py
│   │   ├── retrieval_endpoint_functions.py
│   │   └── xml_utils/
│   │       ├── Kalcium-v3-fields.xsd
│   │       ├── Kalcium-v3-terms.xsd
│   │       └── KalciumXML.py
│   └── kalcium_mcp_server/
│       ├── __init__.py
│       └── kalcium_mcp_server.py
├── test/
│   ├── __init__.py
│   ├── test_client.ipynb
│   └── test_client.py
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone git clone https://username@bitbucket.org/kaleidoscope-group/kalcium-python-client.git
cd kalcium
````

### 2. Create and activate a virtual environment with `uv`

```bash
uv venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate      # Windows
```

### 3. Install the project in editable mode

This allows you to import from both `kalcim_client` and `kalcium_mcp_server` packages across the repo.

```bash
uv pip install -e .
```

---

## 🧠 Cross-Package Imports

This project uses a `src/` layout with proper packaging, so you can import across packages:

For example, in `src/kalcium_mcp_server/kalcium_mcp_server.py`:

```python
from client import KalciumClient
```

No manual `PYTHONPATH` setting is needed—`uv pip install -e .` handles it.

---

## ▶️ Running the Server or Client

You can run the MCP server with uv:

```bash
puv run mcp run ./src/kalcium_mcp_server/kalcium_mcp_server.py
```

Or define CLI scripts in `pyproject.toml` (already included):

```bash
kalcium-server
```

---

## 📦 Adding Dependencies

To add dependencies with `uv`, use:

```bash
uv pip install requests
uv pip freeze > requirements.txt  # optional
```

---

## ⚙️ pyproject.toml Overview

```toml
[project]
name = "kalcium"
version = "0.1.0"
description = "Kalcium Client + MCP Server"
requires-python = ">=3.10"

[project.scripts]
kalcium-server = "mcp.mcp_server:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

---

## ✅ Notes

* This layout supports **editable installs**, **cross-package imports**, and clean modular development.
* `uv` handles dependency and virtualenv management faster and safer than `pip` and `venv`.

---

## 📌 License

Apache 2.0? Actually not defined yet.