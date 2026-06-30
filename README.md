# Career Lens

Welcome to **Career Lens**, an AI-powered job search agent and career mentor application. Career Lens goes beyond simple job boards by intelligently matching your resume to live job openings, providing real-time market analytics, and offering personalized career coaching.

The application leverages advanced AI techniques using **LangChain** and **LangGraph**, alongside a robust backend powered by **FastAPI** and **PostgreSQL**.

---

## 🚀 Modules and Features

### 1. Job Searching & Resume Matching
This module automates the tedious process of finding relevant jobs and figuring out if you are a good fit. It uses a concurrent LangGraph workflow to process live job data and your resume side-by-side.

**Key Features:**
- **Live Job Search:** Scrapes and fetches active job listings based on your specific queries.
- **Concurrent Extraction:** Uses parallel graph execution to extract structured fields (skills, experience, requirements) from both the job descriptions and your uploaded PDF resume.
- **Similarity Scoring:** AI-driven comparison between your extracted resume profile and the job requirements to calculate a fit score.
- **Actionable Feedback:** Generates tailored feedback highlighting exactly which skills you meet and which ones are missing, helping you tailor your applications.

### 2. Job Real-Time Analytics
An aggregated market intelligence dashboard that pulls data from tracked job postings to give you a bird's-eye view of the current job market.

**Key Features:**
- **Market Trends:** Tracks the total number of jobs, top companies hiring, and geographic hotspots.
- **Skill Demand Analysis:** Identifies the most demanded skills across the industry and breaks them down by specific roles (e.g., Data Engineer vs. Frontend Developer).
- **Role Analytics:** Monitors which roles are most active and how they map to specific geographic locations.
- **Time-Series Tracking:** Timeline visualizations of job posting frequencies to identify hiring seasons.

### 3. Career ChatBot (CareerLens Mentor)
A generative AI chatbot that acts as your personalized career coach, grounded in real data rather than generic advice.

**Key Features:**
- **Data-Driven Advice:** The bot can query the **Real-Time Analytics** module to answer questions about market trends (e.g., "What are the most demanded skills for a ML Engineer right now?").
- **Live Workflow Integration:** It can seamlessly trigger the **Job Searching & Resume Matching** module. By analyzing live jobs against your resume during the chat, it computes real skill gaps.
- **Transition Guidance:** Ask the bot how to transition from one role to another (e.g., "How do I switch from Data Analyst to Data Scientist?"), and it will formulate a concrete upskilling plan based on real market data.
- **Actionable Next Steps:** Provides structured, concise, and motivating next steps for your career development.

---

## 🛠️ Technology Stack & Architecture Choices

Here is a breakdown of the technologies used in Career Lens and the rationale behind each choice:

- **FastAPI & Uvicorn**: 
  - *Why*: FastAPI is extremely fast and natively supports asynchronous operations. Given that job matching and web scraping involve heavy network I/O, an async framework ensures the API remains highly responsive.

- **LangChain & LangGraph**:
  - *Why*: The application requires complex, multi-step AI reasoning. LangGraph allows us to build stateful, multi-actor applications by orchestrating parallel AI tasks (like processing the resume and job postings concurrently). LangChain provides robust wrappers for LLM calls and prompt engineering.

- **PostgreSQL & SQLModel**:
  - *Why*: PostgreSQL is a powerful relational database needed for storing structured analytics data (like job features, top skills, and roles). SQLModel bridges Pydantic and SQLAlchemy, making it seamless to interact with the database using native Python types while ensuring data validation.

- **Celery & Redis**:
  - *Why*: Long-running tasks, such as massive live job scrapes or prolonged analytics aggregations, shouldn't block the main API threads. Celery manages these asynchronous background queues efficiently, utilizing Redis as its robust message broker.

- **SlowAPI**:
  - *Why*: To protect the system resources and prevent abuse. SlowAPI integrates smoothly with FastAPI to provide per-IP or user-based rate limiting on intensive endpoints like the live career chatbot.

- **Google GenAI / LLM Endpoints**:
  - *Why*: The backend relies on top-tier language models to generate accurate semantic similarities, parse chaotic job descriptions into structured JSON fields, and power the CareerLens conversational mentor.

- **PyMuPDF & PyPDF2**:
  - *Why*: Extracting clean, high-quality text from diverse user resumes is critical to the accuracy of the matching algorithm. These libraries provide reliable text extraction from PDF files.

- **Apify Client**:
  - *Why*: Building and maintaining custom scrapers for job sites can be fragile due to frequent DOM changes. Apify provides robust, managed scraper APIs, ensuring the live job search remains reliable over time.

---

## 📋 Getting Started

The easiest way to get Career Lens up and running is by using Docker Compose, which spins up the FastAPI backend, PostgreSQL database, Redis message broker, Celery workers, and Nginx proxy seamlessly.

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- API Keys for Google GenAI or other configured LLMs
- Apify API Key (for job scraping)

### 2. Environment Setup
Clone the repository and configure your environment variables:
```bash
git clone https://github.com/Jugal-lachhwani/Job_AI_Agent_Local.git
cd Job_AI_Agent_Local

# Create a copy of the environment template (if available) or create a new .env file
touch .env
```

Populate the `.env` file with your credentials:
```env
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=careerlens_db
API_KEY=your_secure_api_key_for_backend
APIFY_API_TOKEN=your_apify_token
GOOGLE_API_KEY=your_gemini_api_key
```

### 3. Launch the Application
Run the following command to build the images and start all services in the background:
```bash
docker compose up --build -d
```

### 4. Accessing the Application
Once the containers are healthy, you can access the services:
- **Web Frontend:** Open `http://localhost:80` (or just `http://localhost`) in your browser to access the Career Lens user interface.
- **API Documentation:** Open `http://localhost:8000/docs` to interact with the Swagger UI and test the API endpoints directly.

### 5. Managing Services
To view logs for the API and background workers:
```bash
docker compose logs -f api worker
```

To stop all services:
```bash
docker compose down
```

*(To completely wipe the database and queues, run `docker compose down -v`)*