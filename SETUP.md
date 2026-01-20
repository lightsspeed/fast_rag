# FastRAG Chatbot Setup Guide

Follow these steps to set up and run the FastRAG Chatbot project on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.9+**
- **Node.js 18+** & **npm**
- **Git**

---

## 1. Backend Setup (FastAPI)

1. **Navigate to the root directory:**
   ```bash
   cd rag-chatbot
   ```

2. **Create a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   # macOS/Linux
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**
   ```bash
   # Windows
   .\venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables:**
   - Copy `.env.example` to a new file named `.env`.
   - Update the following values in `.env`:
     - `GROQ_API_KEY`: Get your key from [Groq Console](https://console.groq.com/).
     - `POSTGRES_*`: Required only if using Postgres (the app defaults to local SQLite/ChromaDB if not configured).
     - `REDIS_*`: Required only if using Redis for caching.

6. **Run the Backend Server:**
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   The backend will be available at `http://localhost:8000`.

---

## 2. Frontend Setup (React + Vite)

1. **Open a new terminal window.**

2. **Navigate to the frontend directory:**
   ```bash
   cd rag-chatbot/frontend
   ```

3. **Install npm dependencies:**
   ```bash
   npm install
   ```

4. **Run the Frontend Development Server:**
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`.

---

## 3. Usage Instructions

1. **Access the Chatbot:** Open your browser and go to `http://localhost:5173`.
2. **Upload Documents:** Use the upload feature to add your PDFs to the knowledge base.
3. **Chat:** Ask questions about your documents! The AI will use RAG (Retrieval-Augmented Generation) to answer based on the uploaded content.
4. **Smart Titles:** New conversations will automatically receive descriptive titles after your first message.

---

## Project Structure

- `/app`: Backend source code (FastAPI, LLM logic).
- `/frontend`: Frontend source code (React, Tailwind CSS).
- `/chroma_db`: Local vector database storage.
- `/uploads`: Temporary storage for uploaded documents.

---

## Troubleshooting

- **CORS Errors:** Ensure the backend is running on port 8000 and the frontend is on port 5173.
- **Missing API Key:** If messages fail, verify your `GROQ_API_KEY` is correctly set in the `.env` file.
- **Database Issues:** If documents aren't being searched, try clearing the `chroma_db` folder (it will be recreated on next upload).
