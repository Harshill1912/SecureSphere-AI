#  SecureSphere AI — Privacy-First Document Intelligence

SecureSphere AI is a high-performance **Retrieval-Augmented Generation (RAG)** platform designed for **100% offline document interaction**.  
By leveraging **local LLM inference** and **on-device vector search**, it eliminates the security risks of cloud-based AI—making it ideal for **sensitive legal, financial, and enterprise documents**.

---

## 🚀 Key Features

- **100% Local Inference**  
  Powered by **Ollama (Llama 3)** — no data ever leaves your machine.

- **Advanced RAG Pipeline**  
  Implements **Recursive Character Text Splitting** and **Semantic Search** using **ChromaDB** for high-precision retrieval.

- **Privacy-First Architecture**  
  Runs entirely offline, ensuring full data sovereignty and compliance.

- **Real-Time Streaming Responses**  
  Reactive **React frontend** + **FastAPI backend** delivering sub-2s, word-by-word responses.

---

## 🛠️ Tech Stack

| Layer | Technology |
|------|-----------|
| Backend | Python, FastAPI |
| Orchestration | LangChain |
| AI Model | Ollama (Llama 3) |
| Vector Database | ChromaDB |
| Embeddings | `nomic-embed-text` |
| Frontend | React, Tailwind CSS |

---

## ⚙️ Installation & Setup

Follow the steps below to run SecureSphere AI locally.

### ✅ Prerequisites

- Python **3.10+**
- Node.js **18+**
- **Ollama** installed and running

---

### 1️⃣ Backend Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/SecureSphere-AI.git
cd SecureSphere-AI/backend

# Install dependencies
pip install -r requirements.txt

# Pull required models
ollama pull llama3
ollama pull nomic-embed-text

# Start the FastAPI server
uvicorn main:app --reload

2️⃣ Frontend Setup
cd ../frontend

# Install dependencies
npm install

# Start the React application
npm run dev


🔍 How It Works
1)Document Ingestion
Users upload a PDF, which is split into 500-character chunks with semantic overlap.

2))Vectorization
Each chunk is converted into embeddings and stored in a local ChromaDB collection.

3)Context Retrieval
User queries trigger a similarity search to fetch the most relevant chunks.

4)Answer Generation
Llama 3 synthesizes retrieved context into accurate, grounded responses.


 Why SecureSphere AI?

No cloud dependency

No data leakage

No vendor lock-in

Built for enterprises, legal, and finance domains
