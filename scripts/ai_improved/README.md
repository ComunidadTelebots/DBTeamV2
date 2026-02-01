# AI improved scripts

This folder contains helper scripts for building embeddings and indexes used by the RAG endpoints.

Quick start:

1. Activate your venv:

```powershell
& ".venv/Scripts/Activate.ps1"
```

2. Install heavy dependencies (sentence-transformers, faiss optional):

```powershell
pip install -r python_api/requirements_ai.txt
# or
pip install sentence-transformers faiss-cpu
```

3. Build the index:

```powershell
python scripts/build_ai_search_index.py --root . --out projects/bot/python_bot/data/ai_index_faiss.pkl
```

4. Run the API server:

```powershell
python python_api/ai_server.py --host 127.0.0.1 --port 8081
```

5. Test RAG search:

```bash
curl -X POST http://127.0.0.1:8081/rag/search -H "Content-Type: application/json" -d '{"q":"how do I run the bot?","top_k":5}'
```
