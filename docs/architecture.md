# CHARAMOU AI v2 — Architecture Technique

## Principes de conception

| Principe | Application |
|----------|-------------|
| **Séparation des responsabilités** | Chaque module a un rôle unique |
| **Modularité** | Remplacement d'un moteur sans toucher au reste |
| **Évolutivité** | Architecture plugin + agents |
| **Résilience** | HealthMonitor + RecoveryManager |
| **Sécurité** | SecurityManager v2 (validator + vault + audit) |
| **Intelligence** | RAG + mémoire sémantique TF-IDF |

---

## Architecture globale

```
┌──────────────────────────────────────────────────────────────────┐
│                        CHARAMOU AI v2                            │
├──────────────┬───────────────────────────┬──────────────────────┤
│   INTERFACES │        CORE ENGINE         │      MODULES         │
│              │                            │                      │
│  CLI         │  AssistantEngine v2        │  voice/             │
│  GUI Jarvis  │  ├── EventBus              │   recognition.py    │
│  API REST    │  ├── AssistantState        │   synthesis.py      │
│              │  ├── ContextManager        │   wake_word.py      │
│              │  ├── MemoryManager v2      │                      │
│              │  │   ├── Court terme       │  nlp/               │
│              │  │   ├── Long terme SQLite │   intent_classifier │
│              │  │   ├── Sémantique TF-IDF │   response_generator│
│              │  │   └── Connaissances     │                      │
│              │  ├── ActionRegistry        │  ai/                │
│              │  ├── TaskRouter            │   openai_client.py  │
│              │  ├── Scheduler             │   local_model.py    │
│              │  ├── SecurityManager v2    │   (OllamaClient)    │
│              │  │   ├── CommandValidator  │   (HybridAIClient)  │
│              │  │   ├── ApiKeyVault       │                      │
│              │  │   └── AuditLogger       │  automation/        │
│              │  ├── HealthMonitor         │   system_controller │
│              │  ├── RecoveryManager       │   word_controller   │
│              │  └── PluginManager         │   browser_controller│
│              │                            │                      │
│              │  AGENTS                    │  services/          │
│              │  ├── WebAgent              │   weather_service   │
│              │  ├── WordAgent             │   calendar_service  │
│              │  ├── SystemAgent           │   reminder_service  │
│              │  └── [dev_agent...]        │   search_service    │
│              │                            │   knowledge_manager │
│              │                            │   translation_svc   │
│              │                            │   news_service      │
│              │                            │                      │
│              │                            │  vision/            │
│              │                            │   screen_reader.py  │
│              │                            │   ocr.py            │
└──────────────┴───────────────────────────┴──────────────────────┘
```

---

## Pipeline de traitement v2

```
Microphone / Saisie texte
         │
         ▼
 ┌───────────────────┐
 │ SecurityManager   │ ← validate_command() bloque les commandes dangereuses
 │ CommandValidator  │
 └─────────┬─────────┘
           │
           ▼
 ┌───────────────────┐
 │ IntentClassifier  │ ← NLP v2 : intentions + entités + résolution pronominale
 │ EntityExtractor   │
 └─────────┬─────────┘
           │
           ▼
 ┌───────────────────┐
 │   Agent Router    │ ← Délègue aux agents spécialisés si applicable
 │   (WebAgent,      │
 │    WordAgent,     │
 │    SystemAgent)   │
 └─────────┬─────────┘
           │ (si pas d'agent)
           ▼
 ┌───────────────────┐
 │  ActionRegistry   │ ← Table de routes propre (remplace if/elif)
 │  TaskRouter       │
 └─────────┬─────────┘
           │
     ┌─────┴──────────────────┐
     │                        │
     ▼                        ▼
┌──────────┐          ┌──────────────┐
│ Services │          │  HybridAI    │
│ météo    │          │  (GPT/Ollama)│
│ agenda   │          │  + RAG       │
│ rappels  │          │  KnowledgeMgr│
└────┬─────┘          └──────┬───────┘
     └──────────┬────────────┘
                │
                ▼
        ┌───────────────┐
        │ MemoryManager │ ← Sauvegarde + mémorise
        │ (SQLite + TF) │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │  Synthesizer  │ ← pyttsx3 / TTS
        └───────┬───────┘
                │
                ▼
         Utilisateur 🔊
```

---

## Mémoire v2 — 4 niveaux

| Niveau | Stockage | Durée | Utilisation |
|--------|----------|-------|-------------|
| **Travail** | dict RAM | Session | Contexte immédiat |
| **Court terme** | ContextManager (deque) | Session | Historique conversation |
| **Long terme** | SQLite (facts, prefs) | Permanent | Préférences, faits user |
| **Sémantique** | TF-IDF Index | Session + rebuild | Recherche par similarité |

---

## Sécurité v2

```
SecurityManager
├── CommandValidator    : bloque rm -rf, eval(), DROP TABLE...
├── ApiKeyVault        : jamais de clés en dur, masquage logs
├── AuditLogger        : logs/security.log (toutes les actions)
└── PermissionManager  : config/permissions.json
    ├── allow_shutdown: false
    ├── allow_delete_files: false
    └── require_confirmation_for: [shutdown, ...]
```

---

## IA Hybride (Cloud + Local)

```
HybridAIClient
├── Stratégie "cloud_first" (défaut)
│   ├── → OpenAI GPT-4o-mini (si clé API présente)
│   └── → Ollama mistral (si OpenAI indisponible)
├── Stratégie "local_first"
│   ├── → Ollama (si démarré)
│   └── → OpenAI (fallback)
└── Stratégie "offline"
    └── → Ollama uniquement
```

Installer Ollama (offline gratuit) :
```bash
# Windows : https://ollama.ai/download
ollama pull mistral    # ~4 Go
ollama serve           # Démarre le serveur local
```

---

## RAG — Knowledge Manager

```
Document (PDF/DOCX/TXT/Web)
         │
         ▼ ingest_file()
    Découpage en chunks
    (500 chars, 100 overlap)
         │
         ▼ add_knowledge()
    MemoryManager
    TF-IDF Index
         │
         ▼ query("ma question")
    Recherche sémantique
    → Top-K chunks
         │
         ▼ HybridAI.ask(context + question)
    Réponse augmentée
```

---

## Agents v2

| Agent | Capacités | Triggers |
|-------|-----------|---------|
| **WebAgent** | Recherche DDG, extraction, résumé | cherche, google, trouve |
| **WordAgent** | Crée, lit, résume des .docx | word, document, lettre |
| **SystemAgent** | Apps, volume, stats, capture | ouvre, volume, cpu, batterie |
| **[DevAgent]** | *(roadmap)* Code, Git, terminal | code, git, terminal |

---

## Logs v2

```
logs/
├── activity.log    ← Toutes les activités (rotation 5 MB × 5)
├── errors.log      ← Erreurs uniquement
├── voice.log       ← STT/TTS
├── ai.log          ← Appels IA (cloud/local)
├── system.log      ← Système et monitoring
└── security.log    ← Audit sécurité (actions sensibles)
```
