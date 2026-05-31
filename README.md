# 🤖 CHARAMOU AI — Assistant Personnel Vocal v3

> Assistant intelligent pour Windows 10 — Python — Architecture modulaire professionnelle.
> Interaction vocale · Automatisation bureautique · IA hybride Cloud/Local · RAG · Vision

---

## ✨ Fonctionnalités v3

| Catégorie | Détails |
|-----------|---------|
| 🎙️ **Voix** | Google STT · Whisper local · pyttsx3 TTS · Wake word Porcupine |
| 🧠 **NLP v2** | Intentions · Entités · Résolution pronominale · Contexte long |
| 🤖 **IA Hybride** | GPT-4o-mini (cloud) ↔ Ollama (local offline) — bascule auto |
| 🦙 **Ollama** | mistral · llama3 · phi3:mini · fallback cascade automatique |
| 🔐 **Vault AES** | Coffre-fort chiffré Fernet · jamais de clés en clair sur disque |
| 💾 **Mémoire v3** | TF-IDF / ChromaDB / FAISS — backend auto selon dispo |
| 📚 **RAG** | PDF · DOCX · XLSX · PPTX · HTML · Markdown · CSV · Web |
| 👁️ **Vision v2** | OCR Tesseract/EasyOCR · détection boutons · clic visuel |
| 🔧 **Agents** | WebAgent · WordAgent · SystemAgent · architecture extensible |
| 💻 **Dashboard** | Cartes : Système (CPU/RAM/disque) · IA (modèle/temps) · Mémoire |
| 🔒 **Sécurité v2** | CommandValidator · ApiKeyVault · AuditLogger · liste blanche |

---

## 🚀 Installation

```bat
scripts\install.bat
```

Ou manuellement :
```bash
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # Éditez avec vos clés
```

---

## ⚙️ Configuration

### Clés API — 2 méthodes

**Méthode 1 — Fichier `.env`** (simple)
```env
OPENAI_API_KEY=sk-...
OPENWEATHER_API_KEY=...
```

**Méthode 2 — Vault chiffré** (recommandé)
```python
from core.vault import get_vault
vault = get_vault()
vault.store("openai", "sk-...")          # Chiffré AES sur disque
vault.migrate_from_env()                 # Import depuis .env → vault
```

### IA Locale (Ollama, 100% offline)
```bash
# Installer : https://ollama.ai/download
ollama pull mistral      # ~4 Go, recommandé
ollama pull phi3:mini    # ~2.3 Go, rapide
ollama serve             # Démarre le serveur
```
Dans `config/settings.json` :
```json
{ "ai_strategy": "local_first", "local_model": "mistral" }
```

---

## 🎯 Démarrage

```bash
python launcher.py                    # Complet (voix + IA)
python interfaces/cli/terminal_ui.py  # CLI uniquement
python interfaces/gui/app.py          # Dashboard Jarvis
python -m pytest tests/ -v            # Tests (229 tests)
```

---

## 🗣️ Commandes vocales

| Commande | Exemple |
|----------|---------|
| Météo | *« Météo à Lyon »* |
| Rappel | *« Rappelle-moi la réunion à 14h30 »* |
| Document | *« Crée un rapport sur les ventes »* |
| Recherche | *« Cherche FastAPI sur Google »* |
| Traduction | *« Traduis merci en anglais »* |
| Volume | *« Monte le volume »* |
| Capture | *« Fais une capture d'écran »* |
| Actualités | *« Donne-moi les actualités »* |
| Système | *« Quel est l'état du système »* |

---

## 📚 Base de connaissances (RAG)

```python
# Via le KnowledgeManager
km = KnowledgeManager(memory=engine.memory, ai_client=engine.ai_client)

km.ingest_file("rapport_annuel.pdf")      # PDF
km.ingest_file("tableau_bord.xlsx")       # Excel
km.ingest_file("presentation.pptx")       # PowerPoint
km.ingest_file("documentation.md")        # Markdown
km.ingest_url("https://docs.python.org")  # Page web

# Recherche augmentée
reponse = km.query("Quels sont les résultats du T3 ?")
```

---

## 🔐 Sécurité

```
SecurityManager v2
├── CommandValidator   : bloque rm -rf, eval(), DROP TABLE, net user...
├── ApiKeyVault        : lit vault chiffré → .env (jamais en dur)
├── AuditLogger        : trace toutes les actions → logs/security.log
└── PermissionManager  : config/permissions.json
```

---

## 🧠 Mémoire

| Backend | Capacité | Installation |
|---------|----------|-------------|
| **TF-IDF** | ~5 000 docs | Inclus (zéro dépendance) |
| **ChromaDB** | 100 000+ docs | `pip install chromadb` |
| **FAISS** | Millions | `pip install faiss-cpu` |

Bascule automatique selon ce qui est installé.

---

## 🔌 Créer un plugin

```python
# modules/plugins/mon_plugin/plugin.py
from core.plugin_manager import BasePlugin

class Plugin(BasePlugin):
    name = "mon_plugin"

    def setup(self): return True

    def register_routes(self, router):
        router.register("MA_COMMANDE", self.handle)

    def handle(self, entities, context):
        return "Plugin activé !"
```

---

## 📊 Tests

```bash
python -m pytest tests/ -v
# 229 tests · 0 échec · ~3.5s
```

Fichiers de tests :
- `test_nlp.py` · `test_memory.py` · `test_voice.py`
- `test_services.py` · `test_security.py` · `test_agents.py`
- `test_knowledge.py` · `test_vault.py` · `test_vision.py`

---

## 📋 Roadmap

- [ ] Plugin Spotify
- [ ] Contrôle domotique (MQTT)
- [ ] Interface mobile (API REST WebSocket)
- [ ] Agent développement (Code, Git, terminal)
- [ ] Embeddings sentence-transformers
- [ ] Multi-utilisateurs

---

*CHARAMOU AI v3 — Architecture 9.5/10*
