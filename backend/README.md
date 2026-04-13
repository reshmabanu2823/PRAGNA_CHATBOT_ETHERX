Chat_Assistant_EtherX (Pragna-1 A)

Chat_Assistant_EtherX, also known as Pragna-1 A, is a clean, multilingual AI chat assistant powered by Groq (Llama 3) and OpenAI technologies. It features voice interaction, real-time web search capabilities, and a knowledge base for enhanced context-aware responses.

Key Features

-   Multilingual Support: Fluent in English, Hindi, Telugu, Kannada, and Tamil.
-   High-Performance AI: Powered by Groq's Llama 3 model for near-instant responses.
-   Voice Interaction:
    -   Speech-to-Text (STT): Uses Groq Whisper for accurate multilingual audio transcription.
    -   (Coming Soon) Text-to-Speech (TTS).
-   Smart Context:
    -   Web Search: Integrates Serper API to fetch real-time information (news, weather, etc.).
    -   RAG (Retrieval-Augmented Generation): (Optional) Uses FAISS and OpenAI embeddings to learn from documents and web content.
-   Adaptive Responses: Automatically adjusts response length and detail based on the user's query complexity.

 🛠️ Prerequisites

-   Python 3.8+
-   API Keys:
    -   Groq API Key: For the main LLM and Whisper STT.
    -   OpenAI API Key: For text embeddings (used in RAG/Knowledge Base).
    -   Serper API Key: For Google Search integration.

 🚀 Installation

1.  Clone the Repository
    ```bash
    git clone https://github.com/shashidhar0109/Chat_Assistant_EtherX.git
    cd Chat_Assistant_EtherX
    ```

2.  Install Dependencies
    It is recommended to use a virtual environment.
    ```bash
    pip install -r ChatBot/requirements.txt
    ```

3.  Configuration
    Create a `.env` file in the `ChatBot` directory with your API keys. You can copy the structure from `config.py`.

    `ChatBot/.env`:
    ```env
    GROQ_API_KEY=your_groq_api_key
    GROQ_MODEL=llama-3.3-70b-versatile
    OPENAI_API_KEY=your_openai_api_key
    SERPER_API_KEY=your_serper_api_key
    PORT=5001
    DEBUG=True
    ```

 Usage

 Option 1: Quick Start (Windows)
Run the included batch script to check dependencies and start the server:
```cmd
ChatBot\start_lingobot.bat
```

 Option 2: Manual Start
Navigate to the `ChatBot` directory and run the Flask app:
```bash
cd ChatBot
python app.py
```

The server will start at `http://localhost:5001` (or the port specified in your `.env`).

 Project Structure

-   `ChatBot/`: Main application directory.
    -   `app.py`: Flask backend server and API endpoints.
    -   `config.py`: Configuration and environment variable management.
    -   `llm_service.py`: Core logic for LLM interaction, RAG, and web search.
    -   `stt_service.py`: Speech-to-Text service using Groq Whisper.
    -   `web_scraper.py`: Utility to scrape content from search results.
    -   `knowledge_base.py`: Vector database (FAISS) implementation for RAG.
    -   `static/`: Frontend assets (HTML/CSS/JS).

 🔌 API Endpoints

-   `POST /api/chat`: Main chat endpoint.
-   `POST /api/process_audio`: Upload audio for transcription and response.
-   `POST /api/clear_history`: Clear user conversation context.
-   `GET /api/status`: Check server health.


