# MTech Dissertation Project Options
## BITS Pilani | AI & ML Specialization | April 2026

### Student Profile
- **Electives:** NLP Applications, Social Media Analytics, NLP, Information Retrieval, Conversational AI, Speech Processing
- **Industry Experience:** Multi-agent RAG systems, NL-to-SQL engines, Enterprise Conversational AI (VCS & Alta projects)

---

## Option 1: Multi-Agent Collaborative RAG with Chain-of-Thought Reasoning for Domain-Specific Document Intelligence

**Electives Combined:** NLP + Information Retrieval + Conversational AI

### Description
Design and evaluate a multi-agent RAG framework where specialized agents (query decomposition, retrieval strategy selection, evidence extraction, answer synthesis) collaborate through chain-of-thought reasoning to answer complex multi-hop questions over domain-specific document collections.

### Research Contribution
- Novel agent collaboration protocols with backpropagation-style refinement loops
- Comparative evaluation: hierarchical vs. flat multi-agent RAG on multi-hop reasoning
- Domain-specific adaptation benchmarking (construction/legal/medical documents)
- Open-source LLM performance analysis (Llama 3.3 vs Qwen 2.5 vs Mistral)

### Key Papers
| Paper | Venue/Date | Link |
|-------|-----------|------|
| Agentic RAG: A Survey | Jan 2025 | https://arxiv.org/abs/2501.09136 |
| MA-RAG: Multi-Agent RAG via Collaborative CoT | May 2025 | https://arxiv.org/abs/2505.20096 |
| A-RAG: Scaling via Hierarchical Retrieval Interfaces | Feb 2026 | https://arxiv.org/abs/2602.03442 |
| Reasoning RAG: System 1 or System 2 | Jun 2025 | https://arxiv.org/html/2506.10408v1 |

### Open-Source Stack
| Component | Tool | License |
|-----------|------|---------|
| LLM | Llama 3.3 (8B/70B), Qwen 2.5 | Apache 2.0 / Qwen License |
| Agent Framework | LangGraph v1.0 | MIT |
| Vector DB | FAISS, ChromaDB, Qdrant | Apache 2.0 |
| Inference | vLLM, Ollama | Apache 2.0 |
| Evaluation | RAGAS, DeepEval | Apache 2.0 |
| Embeddings | sentence-transformers, BGE | Apache 2.0 |
| API | FastAPI | MIT |

### Datasets
- MultiHop-RAG (COLM 2024): https://github.com/yixuantt/MultiHop-RAG
- HotpotQA: https://hotpotqa.github.io/
- MuSiQue: https://allenai.org/data/musique
- Natural Questions, TriviaQA

### Industry Applications
Enterprise document intelligence, legal discovery, construction compliance, healthcare evidence synthesis

---

## Option 2: Multi-Agent Text-to-SQL with Domain-Specific Specialist Decomposition and Reinforcement Learning

**Electives Combined:** NLP Applications + Information Retrieval + Conversational AI

### Description
Build a multi-agent NL-to-SQL system where specialist agents handle query classification, schema linking, SQL generation, validation, and execution. Introduce reinforcement learning from SQL execution feedback (MARS-SQL approach) to iteratively improve agent performance on domain-specific databases.

### Research Contribution
- Domain-adaptive multi-agent NL-to-SQL with schema-aware specialists
- RL from execution feedback for open-source LLM refinement
- Cross-database transfer learning evaluation for small LLMs (7B-8B)
- New domain-specific benchmark contribution (construction/enterprise)

### Key Papers
| Paper | Venue/Date | Link |
|-------|-----------|------|
| Multi-Agent Collaborative Framework for Text-to-SQL | COLING 2025 | https://aclanthology.org/2025.coling-main.36.pdf |
| MARS-SQL: Multi-Agent RL for Text-to-SQL | Nov 2025 | https://arxiv.org/html/2511.01008v1 |
| Multi-agent Text2SQL with Small LMs | Dec 2025 | https://arxiv.org/abs/2512.18622 |
| CHASE-SQL: Multi-path Reasoning | ICLR 2025 | https://proceedings.iclr.cc |
| SPS-SQL: Small-Scale LLMs | 2025 | https://www.sciencedirect.com/science/article/abs/pii/S0167865525001497 |
| Bird-Interact: Re-imagining Text-to-SQL Eval | Oct 2025 | https://arxiv.org/html/2510.05318v3 |

### Open-Source Stack
| Component | Tool | License |
|-----------|------|---------|
| LLM | Qwen 2.5-Coder (81.7% Spider), Llama 3.1, DeepSeek-Coder | Open |
| Agent Framework | LangGraph, CrewAI | MIT |
| SQL Engine | SQLite, DuckDB, PostgreSQL | Open |
| Fine-tuning | LoRA/QLoRA via PEFT, Unsloth | Apache 2.0 |
| API | FastAPI | MIT |

### Datasets
- **BIRD** (95 databases, 37 domains, 33.4GB): https://bird-bench.github.io/
- **Spider / Spider 2.0**: Cross-database benchmark
- **Bird-Interact**: Dynamic interaction evaluation
- **ScienceBenchmark**: Scientific domain SQL
- **EHRSQL**: Healthcare domain

### Industry Applications
Enterprise BI dashboards, healthcare analytics, construction project management, financial reporting

---

## Option 3: Graph-Enhanced RAG (GraphRAG) for Social Media Knowledge Extraction and Analysis

**Electives Combined:** NLP + Social Media Analytics + Information Retrieval

### Description
Build a GraphRAG system that constructs entity-relation knowledge graphs from social media data streams, then uses graph traversal combined with vector retrieval for complex analytical queries. Evaluate 40-60% improvement claims over vector-only RAG.

### Research Contribution
- Dynamic GraphRAG from streaming social media (Twitter/Reddit)
- Comparative evaluation: GraphRAG vs vector RAG vs hybrid on social media QA
- Multi-agent graph construction with quality-aware entity resolution
- Open-source implementation benchmark

### Key Papers
| Paper | Venue/Date | Link |
|-------|-----------|------|
| LLMs Meet Knowledge Graphs for QA | EMNLP 2025 | https://aclanthology.org/2025.emnlp-main.1249.pdf |
| Diagnosing Pitfalls in KG-RAG Datasets | 2025 | https://openreview.net/pdf?id=Vd5JXiX073 |
| GRADE: Multi-hop QA with Fine-grained Difficulty | EMNLP 2025 | https://aclanthology.org/2025.findings-emnlp.236.pdf |

### Open-Source Stack
| Component | Tool | License |
|-----------|------|---------|
| Graph DB | Neo4j Community, NetworkX | GPLv3 / BSD |
| KG Construction | LlamaIndex PropertyGraphIndex | MIT |
| LLM | Llama 3.3, Qwen 2.5 | Open |
| Retrieval | Text2Cypher, hybrid vector+graph | Open |
| Social Data | snscrape, PRAW (Reddit) | Open |

### Datasets
- WebQSP, ComplexWebQuestions
- HotpotQA, MuSiQue
- Custom social media datasets (Reddit API dumps)
- Awesome-GraphRAG resources: https://github.com/DEEP-PolyU/Awesome-GraphRAG

### Industry Applications
Brand intelligence, political discourse analysis, supply chain risk, event tracking

---

## Option 4: Voice-Enabled Agentic RAG: Speech-to-Speech Retrieval Systems

**Electives Combined:** Speech Processing + Conversational AI + Information Retrieval + NLP

### Description
Build an end-to-end voice-enabled RAG system where users ask questions verbally and receive spoken answers grounded in a domain knowledge base. Explore transcription-free approaches (VoxRAG) and dual-agent architectures (VoiceAgentRAG) for real-time latency.

### Research Contribution
- End-to-end speech-to-speech RAG pipeline bypassing text transcription
- Latency-optimized dual-agent architecture for real-time voice QA
- **First benchmark for voice-based domain-specific RAG** (highly novel)
- Code-switching and multilingual voice RAG for Indian languages

### Key Papers
| Paper | Venue/Date | Link |
|-------|-----------|------|
| VoxRAG: Transcription-Free RAG in Spoken QA | May 2025 | https://arxiv.org/html/2505.17326v1 |
| VoiceAgentRAG: Solving RAG Latency | Mar 2026 | https://arxiv.org/html/2603.02206 |
| Stream RAG: Instant Spoken Dialogue | Oct 2025 | https://arxiv.org/html/2510.02044v1 |
| Survey on Speech Large Language Models | 2024 | https://arxiv.org/html/2410.18908v3 |

### Open-Source Stack
| Component | Tool | License |
|-----------|------|---------|
| ASR | Whisper, faster-whisper | MIT |
| Multimodal LLM | Qwen2.5-Omni (text+audio+video) | Qwen License |
| TTS | Coqui TTS, Piper, VITS | MPL / Apache 2.0 |
| Voice Agent | Pipecat | BSD |
| RAG | LlamaIndex, LangGraph | MIT |
| Vector DB | FAISS, ChromaDB | Apache 2.0 |

### Datasets
- LibriSpeech: https://www.openslr.org/12
- Mozilla Common Voice (100+ languages): https://commonvoice.mozilla.org/
- Spoken-SQuAD, SpokenCOCO
- Custom voice QA dataset (opportunity to contribute)

### Industry Applications
Hands-free enterprise assistants (construction sites, warehouses), multilingual customer support, accessibility, voice search

---

## Option 5: Social Media Crisis Detection and Response Using Multi-Agent NLP Pipelines

**Electives Combined:** Social Media Analytics + NLP + Information Retrieval + Conversational AI

### Description
Build a multi-agent pipeline for real-time crisis detection from social media: streaming ingestion agent, classification agent, geolocation agent, severity assessment agent, and RAG-augmented response generation agent.

### Research Contribution
- Multi-agent architecture for crisis NLP (novel application of agentic RAG)
- Benchmarking open-source LLMs vs fine-tuned BERT on crisis classification
- RAG-augmented crisis chatbot with historical disaster knowledge base
- Real-time streaming evaluation framework

### Key Papers
| Paper | Venue/Date | Link |
|-------|-----------|------|
| CrisisBench: Benchmarking Crisis Social Media | ICWSM | https://ojs.aaai.org/index.php/ICWSM/article/view/18115 |
| Disaster Detection using NLP in Social Networks | 2025 | https://wseas.com/journals/isa/2025/b205109-031(2025).pdf |
| Real-Time Crisis Detection on Social Media | 2025 | https://www.researchgate.net/publication/393999066 |
| Unified Multimodal Misinformation Detection | 2025 | https://arxiv.org/abs/2509.25991 |

### Open-Source Stack
| Component | Tool | License |
|-----------|------|---------|
| LLM | Llama 3.1, Mistral 7B, Qwen 2.5 | Open |
| Streaming | Apache Kafka, Redis Streams | Apache 2.0 |
| NLP | HuggingFace Transformers, spaCy | Apache 2.0 / MIT |
| Geolocation | mordecai | MIT |
| Agent Framework | LangGraph, CrewAI | MIT |
| Frontend | Streamlit, Gradio | Apache 2.0 |

### Datasets
- **CrisisBench** (166.1K tweets): https://huggingface.co/datasets/QCRI/CrisisBench-all-lang
- **CrisisNLP** (19 disasters): https://crisisnlp.qcri.org/
- **CrisisMMD**: Multimodal crisis data
- **OmniFake** (127K samples): Misinformation detection

### Industry Applications
Disaster response coordination, government emergency management, NGO awareness, insurance risk

---

## Option 6: RAG-Augmented Aspect-Based Opinion Mining for Social Media

**Electives Combined:** Social Media Analytics + NLP + Information Retrieval

### Description
Build a RAG-augmented zero-shot ABSA system where retrieval provides domain context to open-source LLMs, eliminating task-specific fine-tuning. Multi-agent pipeline with separate agents for aspect extraction, sentiment classification, and opinion summarization.

### Research Contribution
- RAG-augmented zero-shot ABSA (novel combination)
- Multi-agent ABSA pipeline evaluation
- Cross-domain transfer evaluation (restaurants vs products vs politics)
- Multilingual ABSA for Indian social media (Hindi-English code-mixing)

### Key Papers
| Paper | Venue/Date | Link |
|-------|-----------|------|
| LLMs as Online Opinion Miners | May 2025 | https://arxiv.org/html/2505.15695 |
| TASCI: Transformers for ABSA | 2025 | https://pmc.ncbi.nlm.nih.gov/articles/PMC12190667/ |
| Systematic Review of ABSA | 2024 | https://link.springer.com/article/10.1007/s10462-024-10906-z |
| EduRABSA Dataset | 2025 | https://arxiv.org/html/2508.17008v1 |

### Open-Source Stack
| Component | Tool | License |
|-----------|------|---------|
| LLM | Llama 3.1, Mistral, Qwen 2.5 | Open |
| Fine-tuning | LoRA/QLoRA, Unsloth | Apache 2.0 |
| ABSA | PyABSA, SetFit | Apache 2.0 |
| Annotation | AnnoABSA | Open |
| NLP | HuggingFace Transformers | Apache 2.0 |

### Datasets
- SemEval-2014/2015/2016 (Restaurant & Laptop)
- M-ABSA (14,800 sentences, 21 languages, 7 domains)
- EduRABSA (Education domain)
- Twitter Sentiment (SemEval tasks)

### Industry Applications
Brand monitoring, product feedback, political sentiment, customer experience

---

## Option 7: Multilingual Conversational Search for Low-Resource Indian Languages

**Electives Combined:** NLP + Information Retrieval + Conversational AI + Speech Processing

### Description
Build a multilingual conversational RAG system for Indian languages (Hindi, Marathi, Bengali) with code-switching support. Voice-first interface using Whisper + multilingual LLM + domain-specific RAG.

### Research Contribution
- Multilingual conversational RAG with code-switching support
- **New benchmark for Hindi/Marathi conversational search** (none exists)
- Cross-lingual transfer evaluation from English RAG pipelines
- Voice-first conversational search for Indian languages

### Key Papers
| Paper | Venue/Date | Link |
|-------|-----------|------|
| Babel: Multilingual LLM (90%+ speakers) | 2025 | https://babel-llm.github.io/babel-llm/ |
| LoResLM 2025 Workshop | COLING 2025 | https://loreslm.github.io/ |
| NLP for Low-Resource Languages | Cambridge | https://www.cambridge.org/core/journals/natural-language-processing/article/... |
| LLM Evaluation for Low-Resource Languages | 2024 | https://www.sciencedirect.com/science/article/pii/S2949719124000724 |

### Open-Source Stack
| Component | Tool | License |
|-----------|------|---------|
| Multilingual LLM | Babel-9B/83B, Qwen 3, Llama 3.3 | Open |
| ASR | Whisper (multilingual), Common Voice | MIT |
| Embeddings | multilingual-e5, SONAR (Meta) | MIT |
| NLP | Stanza (60+ langs), IndicNLP, iNLTK | Apache 2.0 |
| Agent Framework | LangGraph, LlamaIndex | MIT |

### Datasets
- Mozilla Common Voice (100+ languages)
- FLORES (multilingual evaluation)
- IndicGLUE (Indian NLU benchmark)
- XQuAD, TyDi QA (cross-lingual QA)
- OSCAR (multilingual corpus)

### Industry Applications
Government services, rural banking/fintech, multilingual support, education access

---

## Recommendation Ranking (Best Fit for Your Profile)

| Rank | Option | Novelty | Feasibility | Industry Impact | Elective Coverage | Publication Potential |
|------|--------|---------|-------------|-----------------|-------------------|---------------------|
| 1 | **Option 4: Voice-Enabled RAG** | Very High | Medium | Very High | 4/6 electives | High (frontier area) |
| 2 | **Option 2: Multi-Agent Text-to-SQL** | High | Very High | Very High | 3/6 electives | Very High (COLING/ICLR) |
| 3 | **Option 1: Multi-Agent RAG** | High | Very High | Very High | 3/6 electives | High |
| 4 | **Option 5: Crisis Detection** | High | High | Very High | 4/6 electives | High |
| 5 | **Option 3: GraphRAG Social Media** | High | Medium | High | 3/6 electives | High |
| 6 | **Option 7: Multilingual Search** | Very High | Medium | High | 4/6 electives | Very High |
| 7 | **Option 6: ABSA Opinion Mining** | Medium | High | High | 3/6 electives | Medium |

---

## Common Open-Source Infrastructure (All Options)

| Component | Tools | License |
|-----------|-------|---------|
| **LLMs** | Llama 3.1/3.3 (8B-70B), Qwen 2.5/3, Mistral/Mixtral, DeepSeek-R1 | Apache 2.0 / Open |
| **Inference** | vLLM (production), Ollama (dev), llama.cpp (edge) | Apache 2.0 |
| **Fine-tuning** | LoRA/QLoRA via PEFT, Unsloth, Axolotl | Apache 2.0 |
| **Embeddings** | sentence-transformers, multilingual-e5, BGE | Apache 2.0 |
| **Vector Store** | FAISS, ChromaDB, Qdrant, Milvus | Apache 2.0 |
| **Agent Frameworks** | LangGraph v1.0, CrewAI, LlamaIndex | MIT |
| **Experiment Tracking** | MLflow, W&B (free tier), RAGAS | Apache 2.0 |
| **API** | FastAPI | MIT |
| **Frontend** | Streamlit, Gradio, Next.js | Apache 2.0 / MIT |
| **Deployment** | Docker, Docker Compose, Coolify (self-hosted) | Open |

---

*Generated: 2026-04-05 | All tools verified as open-source*
