
## AI Job Recommender & CV Generator


An end-to-end local AI application that:

- fetches real job vacancies (work.ua, DOU),
- ranks them using semantic retrieval (RAG),
- generates ATS-friendly CVs with a local LLM (Gemma 3 12B, GGUF),
- allows manual editing and recompilation of generated CVs,
- maintains profile & CV history to avoid repetitive input and reduce LLM hallucinations.


The project is designed to be fully local, deterministic, debuggable, and suitable both for research and real-world use.


### Key Features


#### Job Recommendation

Live job scraping from work.ua and dou.ua

- Multilingual semantic matching (UA / EN)
- Retrieval-Augmented Generation (RAG) based on sentence embeddings
- Robust ranking even when only partial user input is provided
- UI-driven job exploration


#### CV Generation

- Local Gemma-3-12B-IT (GGUF) inference via llama.cpp
- Explicit separation of:
    - structured user data (personal info, education, experience)
    - LLM-generated content (summary, experience bullets, projects)
- Editable raw LLM output with one-click PDF recompilation
- Clean, minimalistic PDF layout (PyMuPDF)
- Placeholder removal and normalization to prevent template artifacts


#### Profile & History Management

- Save/load multiple profiles
- Timestamped history files
- Automatic fallback to the last saved profile for empty fields
- User notification of auto-filled fields (no silent mutations)
- CV history storage for reproducibility and debugging

#### Desktop UI

- Built with PySide6
- Scrollable, modular layout
- Async workers (QThread) for:
    - job fetching
    - LLM inference
    - PDF generation
- Debug panel showing raw model output


### Project Structure

```{bash}
.
├── app.py                     # Main PySide6 application
├── core
│   ├── rag_engine.py           # Semantic job search (SentenceTransformers)
│   ├── cv_generator.py         # LLM inference (Gemma GGUF via llama.cpp)
│   ├── cv_formatter.py         # Converts UI profile → LLM input
│   ├── pdf_writer.py           # Robust text → PDF renderer
│   ├── prompt.py               # System prompt (unchanged across runs)
│   └── storage.py              # Profile & CV history management
├── fetchers
│   ├── workua_fetcher.py       # work.ua scraper
│   ├── dou_fetcher.py          # dou.ua scraper
│   └── headers.py              # Browser-like headers
├── .cv_app                     # Auto-created (profiles & CVs)
├── gemma-3-12b-it-Q4_K_M.gguf  # Local LLM model
├── requirements.txt
├── README.md
└── LICENSE

```


### Architecture Overview


#### 1. Job Recommendation (RAG)

Pipeline:
1. User profile → semantic query
2. Fetch vacancies from job boards
3. Convert job postings to embeddings (SentenceTransformer)
4. Store in in-memory vector index
5. Rank via cosine similarity
6. Display ranked results in UI

This approach handles multilingual content, avoids brittle keyword matching, works even with sparse input.


#### 2. CV Generation (LLM-assisted, deterministic)

Key design decision:
    The LLM is not trusted with factual personal data.

Flow:
1. UI profile → cv_formatter.py
2. Structured data passed explicitly (name, education, experience)
3. LLM generates narrative sections only
4. Raw output shown to user
5. User can edit text manually
6. PDF compiled from edited text + structured data

This prevents hallucinated education, fake companies, invented experience.


#### 3. PDF Rendering

Implemented in pdf_writer.py using PyMuPDF: bullet indentation handling, automatic page breaks, placeholder cleanup, minimalist layout suitable for ATS


#### 4. History & Auto-Fill Logic

Profiles are saved as JSON with timestamps:
```
YYYY-MM-DD_HH-MM_<role>.json
```

On CV generation:

- Missing fields are auto-filled from the most recent profile
- User is explicitly notified which fields were reused
- No override of user-entered data


### Installation


#### Requirements

- Python 3.11+
- CUDA (optional, for GPU inference)
- ~8–10 GB RAM (CPU inference)
- ~6–8 GB VRAM (GPU inference)


#### Install dependencies

```{bash}
pip install -r requirements.txt
```


#### Place model

Download and place gemma-3-12b-it-Q4_K_M.gguf in project root from huggingface


### Running the App

```{bash}
python app.py
```


### Usage Workflow

1. Fill or load a profile
2. Fetch & rank jobs (Jobs tab)
3. Generate CV (CV tab)
4. Inspect raw LLM output
5. Edit if necessary
6. Recompile PDF
7. Save profile / CV history


### Experiments & Research
The `experiments/` folder contains:

- Gemma fine-tuning notebooks
- Dataset preparation scripts
- Performance benchmarks

These are not required for running the app, but document the research behind model selection and tuning.
We used datasets from huggingface to fine-tune the models:

https://huggingface.co/datasets/lang-uk/recruitment-dataset-candidate-profiles-english

### Usage video

<video src="https://github.com/xsponenta/AI_powered_job_recommendation_system/raw/main/usage.mp4" controls="controls" style="max-width: 730px;">
</video>
