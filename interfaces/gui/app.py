"""
CHARAMOU AI - Dashboard Jarvis v3
Cartes : Système | IA | Mémoire | Conversation temps réel
"""
import sys, threading, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))


class CharamouDashboard:

    C = {
        "bg":       "#080818",  "panel":    "#0d0d24",  "card":     "#111130",
        "accent":   "#00d4ff",  "accent2":  "#7b2fff",  "accent3":  "#00e676",
        "user":     "#0f2040",  "ai":       "#090930",   "text":     "#ddeeff",
        "dim":      "#445566",  "ok":       "#00e676",   "warn":     "#ffab00",
        "err":      "#ff5252",  "border":   "#1a2a4a",
    }

    def __init__(self):
        try:
            import customtkinter as ctk
            self.ctk = ctk
        except ImportError:
            print("pip install customtkinter"); sys.exit(1)

        self.ctk.set_appearance_mode("dark")
        self.ctk.set_default_color_theme("blue")
        self.root = self.ctk.CTk()
        self.root.title("CHARAMOU AI — Dashboard")
        self.root.geometry("1200x780")
        self.root.configure(fg_color=self.C["bg"])

        self.engine     = None
        self._resp_times: list = []   # historique temps de réponse
        self._tokens_total  = 0

        self._init_engine_thread()
        self._build_ui()
        self._start_refresh_loop()

    # ── Init moteur ──────────────────────────────────────────────────────────
    def _init_engine_thread(self):
        def _init():
            try:
                from core.engine import AssistantEngine
                self.engine = AssistantEngine()
                self.engine._voice_enabled = False
                
                # Initialisation complète (similaire à engine.start() sans la boucle bloquante)
                self.engine._init_modules()
                self.engine._init_agents()
                self.engine._register_routes()
                self.engine._subscribe_events()
                self.engine._register_health_checks()

                self.engine.scheduler.start()
                self.engine.health.start()
                self.engine.plugins.load_all()
                
                self.root.after(0, self._on_ready)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: self._set_status(f"ERREUR : {str(e)[:40]}", self.C["err"]))
        threading.Thread(target=_init, daemon=True).start()

    def _on_ready(self):
        self._set_status("PRÊT", self.C["ok"])
        self._refresh_all()
        self._add_msg("CHARAMOU", "Bonjour ! Dashboard CHARAMOU AI v3 opérationnel.", False)

    # ── Mise en page ─────────────────────────────────────────────────────────
    def _build_ui(self):
        ctk, C = self.ctk, self.C
        self.root.grid_columnconfigure(0, weight=0, minsize=240)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # ══ SIDEBAR ══
        sb = ctk.CTkFrame(self.root, fg_color=C["panel"], width=240, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nswe")
        sb.grid_propagate(False)

        ctk.CTkLabel(sb, text="⬡  CHARAMOU AI", font=("Courier New",15,"bold"),
                     text_color=C["accent"]).pack(pady=(18,2), padx=12)
        ctk.CTkLabel(sb, text="Assistant Personnel v3", font=("Segoe UI",9),
                     text_color=C["dim"]).pack()

        self.status_lbl = ctk.CTkLabel(sb, text="● INIT", font=("Segoe UI",11,"bold"),
                                        text_color=C["warn"])
        self.status_lbl.pack(pady=6)

        ctk.CTkFrame(sb, height=1, fg_color=C["border"]).pack(fill="x", padx=18, pady=6)

        # ── Carte Système ──
        sys_card = self._sidebar_card(sb, "💻 SYSTÈME")
        self._sys_rows = {}
        for label in ["CPU", "RAM", "Disque", "Batterie"]:
            row = ctk.CTkFrame(sys_card, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(row, text=label, font=("Segoe UI",10), text_color=C["text"],
                         width=70, anchor="w").pack(side="left")
            pb = ctk.CTkProgressBar(row, width=80, height=8, progress_color=C["accent"])
            pb.pack(side="left", padx=4)
            pb.set(0)
            val = ctk.CTkLabel(row, text="—", font=("Segoe UI",9), text_color=C["dim"])
            val.pack(side="left")
            self._sys_rows[label] = (pb, val)

        ctk.CTkFrame(sb, height=1, fg_color=C["border"]).pack(fill="x", padx=18, pady=6)

        # ── Carte IA ──
        ai_card = self._sidebar_card(sb, "🤖 IA")
        self._ai_labels = {}
        for k in ["Modèle actif", "Temps moy.", "Tokens totaux", "Backend"]:
            row = ctk.CTkFrame(ai_card, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(row, text=k+":", font=("Segoe UI",9), text_color=C["dim"],
                         width=90, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", font=("Segoe UI",9,"bold"),
                               text_color=C["accent"])
            lbl.pack(side="left")
            self._ai_labels[k] = lbl

        ctk.CTkFrame(sb, height=1, fg_color=C["border"]).pack(fill="x", padx=18, pady=6)

        # ── Carte Mémoire ──
        mem_card = self._sidebar_card(sb, "🧠 MÉMOIRE")
        self._mem_labels = {}
        for k in ["Préférences", "Faits", "Échanges", "Connaissances", "Backend", "Entrées"]:
            row = ctk.CTkFrame(mem_card, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(row, text=k+":", font=("Segoe UI",9), text_color=C["dim"],
                         width=95, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", font=("Segoe UI",9,"bold"),
                               text_color=C["accent3"])
            lbl.pack(side="left")
            self._mem_labels[k] = lbl

        ctk.CTkFrame(sb, height=1, fg_color=C["border"]).pack(fill="x", padx=18, pady=6)

        # ── Modules ──
        mod_card = self._sidebar_card(sb, "📦 MODULES")
        self._mod_lbls = {}
        for mod in ["Voix STT", "Synthèse TTS", "NLP", "IA Cloud", "IA Local", "RAG", "Vision"]:
            row = ctk.CTkFrame(mod_card, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(row, text=mod, font=("Segoe UI",9), text_color=C["text"],
                         width=95, anchor="w").pack(side="left")
            dot = ctk.CTkLabel(row, text="○", font=("Segoe UI",10), text_color=C["warn"])
            dot.pack(side="right")
            self._mod_lbls[mod] = dot

        # ══ PANNEAU PRINCIPAL ══
        main = ctk.CTkFrame(self.root, fg_color=C["bg"], corner_radius=0)
        main.grid(row=0, column=1, sticky="nswe")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Topbar
        top = ctk.CTkFrame(main, fg_color=C["panel"], height=44, corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)
        ctk.CTkLabel(top, text="CONVERSATION", font=("Courier New",11,"bold"),
                     text_color=C["accent"]).pack(side="left", padx=14, pady=12)
        self.backend_lbl = ctk.CTkLabel(top, text="Backend : —", font=("Segoe UI",9),
                                         text_color=C["dim"])
        self.backend_lbl.pack(side="right", padx=14)
        self.time_lbl = ctk.CTkLabel(top, text="", font=("Segoe UI",9), text_color=C["dim"])
        self.time_lbl.pack(side="right", padx=6)

        # Chat
        self.chat_frame = self.ctk.CTkScrollableFrame(main, fg_color=C["bg"], corner_radius=0)
        self.chat_frame.pack(fill="both", expand=True, padx=0)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        # Raccourcis rapides
        shortcuts_bar = ctk.CTkFrame(main, fg_color=C["panel"], height=36, corner_radius=0)
        shortcuts_bar.pack(fill="x")
        shortcuts_bar.pack_propagate(False)
        SHORTCUTS = [
            ("🌤 Météo",      "météo Paris"),
            ("📅 Agenda",     "agenda aujourd'hui"),
            ("📰 Actualités", "actualités"),
            ("💻 Système",    "état du système"),
            ("🧠 Mémoire",    "résumé mémoire"),
            ("🔍 Recherche",  "cherche "),
        ]
        for label, cmd in SHORTCUTS:
            ctk.CTkButton(shortcuts_bar, text=label, height=28, width=100,
                          command=lambda c=cmd: self._quick(c),
                          fg_color=C["card"], hover_color=C["border"],
                          text_color=C["text"], font=("Segoe UI",10),
                          corner_radius=4).pack(side="left", padx=3, pady=4)

        # Barre de saisie
        inp_bar = ctk.CTkFrame(main, fg_color=C["panel"], height=58, corner_radius=0)
        inp_bar.pack(fill="x")
        inp_bar.pack_propagate(False)
        inp_bar.grid_columnconfigure(0, weight=1)

        self.input_field = ctk.CTkEntry(
            inp_bar, placeholder_text="Parlez à CHARAMOU...",
            font=("Segoe UI",13), fg_color=C["card"],
            border_color=C["accent"], text_color=C["text"], border_width=1
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=(10,6), pady=9)
        self.input_field.bind("<Return>", self._on_send)

        btns = ctk.CTkFrame(inp_bar, fg_color="transparent")
        btns.pack(side="right", padx=8)

        self.send_btn = ctk.CTkButton(
            btns, text="➤", width=44, height=38,
            fg_color=C["accent"], text_color="#000", font=("Segoe UI",16,"bold"),
            command=self._on_send, corner_radius=6
        )
        self.send_btn.pack(side="left", padx=2)
        ctk.CTkButton(btns, text="🗑", width=38, height=38,
                      fg_color=C["card"], text_color=C["dim"],
                      command=self._clear_chat, corner_radius=6).pack(side="left", padx=2)

    def _sidebar_card(self, parent, title: str):
        ctk, C = self.ctk, self.C
        frame = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=6)
        frame.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(frame, text=title, font=("Courier New",9,"bold"),
                     text_color=C["accent2"]).pack(anchor="w", padx=8, pady=(5,2))
        return frame

    # ── Messages ─────────────────────────────────────────────────────────────
    def _add_msg(self, sender: str, text: str, is_user: bool):
        ctk, C = self.ctk, self.C
        color  = C["user"] if is_user else C["ai"]
        border = C["accent2"] if is_user else C["accent"]
        icon   = "👤" if is_user else "🤖"
        ts     = datetime.now().strftime("%H:%M:%S")

        row = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=3)
        bub = ctk.CTkFrame(row, fg_color=color, corner_radius=10,
                            border_color=border, border_width=1)
        bub.pack(side="right" if is_user else "left", padx=5)

        hdr = ctk.CTkFrame(bub, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(6,0))
        ctk.CTkLabel(hdr, text=f"{icon} {sender}", font=("Segoe UI",9,"bold"),
                     text_color=border).pack(side="left")
        ctk.CTkLabel(hdr, text=ts, font=("Segoe UI",8),
                     text_color=C["dim"]).pack(side="right")

        ctk.CTkLabel(bub, text=text, font=("Segoe UI",12), text_color=C["text"],
                     wraplength=560, justify="left", anchor="w"
                     ).pack(anchor="w", padx=10, pady=(2,8))
        self.root.after(120, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))

    # ── Actions UI ───────────────────────────────────────────────────────────
    def _on_send(self, event=None):
        text = self.input_field.get().strip()
        if not text: return
        self.input_field.delete(0, "end")
        self._add_msg("Vous", text, True)
        self._set_status("TRAITEMENT...", self.C["warn"])
        self.send_btn.configure(state="disabled")

        def _process():
            t0 = time.time()
            try:
                if self.engine:
                    # Commandes internes
                    if text.lower() in ("résumé mémoire", "mémoire"):
                        resp = self.engine.memory.get_memory_summary() if self.engine.memory else "—"
                    elif text.lower() in ("état du système", "stats"):
                        resp = self.engine.get_status().__str__() if hasattr(self.engine, 'get_status') else "—"
                    else:
                        resp = self.engine.process_input(text)
                else:
                    resp = "L'assistant s'initialise..."
            except Exception as e:
                resp = f"Erreur : {e}"

            elapsed = round((time.time() - t0) * 1000)
            self._resp_times.append(elapsed)
            if len(self._resp_times) > 20:
                self._resp_times.pop(0)

            self.root.after(0, lambda: self._add_msg("CHARAMOU", resp or "...", False))
            self.root.after(0, lambda: self._set_status("PRÊT", self.C["ok"]))
            self.root.after(0, lambda: self.send_btn.configure(state="normal"))
            self.root.after(0, self._refresh_all)

        threading.Thread(target=_process, daemon=True).start()

    def _quick(self, cmd: str):
        self.input_field.delete(0, "end")
        self.input_field.insert(0, cmd)
        self._on_send()

    def _clear_chat(self):
        for w in self.chat_frame.winfo_children():
            w.destroy()

    def _set_status(self, text: str, color: str):
        self.status_lbl.configure(text=f"● {text}", text_color=color)

    # ── Refresh ──────────────────────────────────────────────────────────────
    def _start_refresh_loop(self):
        def _loop():
            while True:
                time.sleep(5)
                self.root.after(0, self._refresh_all)
        threading.Thread(target=_loop, daemon=True).start()

    def _refresh_all(self):
        self._refresh_time()
        self._refresh_system()
        self._refresh_modules()
        self._refresh_ai()
        self._refresh_memory()

    def _refresh_time(self):
        now = datetime.now().strftime("%H:%M:%S — %d/%m/%Y")
        self.time_lbl.configure(text=now)

    def _refresh_system(self):
        try:
            import psutil
            cpu  = psutil.cpu_percent(interval=0)
            ram  = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            bat  = psutil.sensors_battery()

            def _update(label, pct, text):
                pb, lbl = self._sys_rows[label]
                pb.set(min(pct / 100, 1.0))
                color = self.C["err"] if pct > 85 else self.C["warn"] if pct > 65 else self.C["ok"]
                pb.configure(progress_color=color)
                lbl.configure(text=text)

            _update("CPU",    cpu,          f"{cpu:.0f}%")
            _update("RAM",    ram.percent,  f"{ram.percent:.0f}%")
            _update("Disque", disk.percent, f"{disk.percent:.0f}%")
            if bat:
                pct = bat.percent
                icon = "⚡" if bat.power_plugged else "🔋"
                _update("Batterie", pct, f"{pct:.0f}% {icon}")
            else:
                self._sys_rows["Batterie"][1].configure(text="N/A")
        except Exception:
            pass

    def _refresh_modules(self):
        if not self.engine: return
        def _dot(mod, ok):
            if mod in self._mod_lbls:
                c = self.C["ok"] if ok else self.C["err"]
                self._mod_lbls[mod].configure(text="●" if ok else "○", text_color=c)

        _dot("Voix STT",    bool(self.engine.recognizer))
        _dot("Synthèse TTS",bool(self.engine.synthesizer))
        _dot("NLP",         bool(self.engine.nlp))
        _dot("RAG",         bool(self.engine.knowledge))
        _dot("Vision",      True)   # disponible si libs présentes

        ai = self.engine.ai_client
        if ai:
            try:
                from modules.ai.openai_client import OpenAIClient
                cloud_ok = isinstance(getattr(ai, '_cloud', None), OpenAIClient) and ai._cloud.available
            except Exception:
                cloud_ok = False
            _dot("IA Cloud", cloud_ok)
            _dot("IA Local", ai._local.is_available() if hasattr(ai, '_local') else False)

    def _refresh_ai(self):
        if not self.engine or not self.engine.ai_client: return
        ai = self.engine.ai_client
        backend = ai.current_backend()
        self.backend_lbl.configure(text=f"Backend : {backend}")

        avg_ms = round(sum(self._resp_times) / len(self._resp_times)) if self._resp_times else 0
        self._ai_labels["Modèle actif"].configure(text=backend.split("(")[-1].rstrip(")") if "(" in backend else backend)
        self._ai_labels["Temps moy."].configure(text=f"{avg_ms} ms")
        self._ai_labels["Tokens totaux"].configure(text=str(self._tokens_total))
        self._ai_labels["Backend"].configure(text="cloud" if "cloud" in backend else "local" if "local" in backend else "—")

    def _refresh_memory(self):
        if not self.engine or not self.engine.memory: return
        try:
            stats = self.engine.memory.get_stats()
            self._mem_labels["Préférences"].configure(text=str(stats.get("preferences", 0)))
            self._mem_labels["Faits"].configure(text=str(stats.get("facts", 0)))
            self._mem_labels["Échanges"].configure(text=str(stats.get("conversations", 0)))
            self._mem_labels["Connaissances"].configure(text=str(stats.get("knowledge", 0)))
            self._mem_labels["Backend"].configure(text=stats.get("semantic_backend", "—"))
            self._mem_labels["Entrées"].configure(text=str(stats.get("semantic_entries", 0)))
        except Exception:
            pass

    def run(self): self.root.mainloop()


def launch_gui():
    CharamouDashboard().run()

if __name__ == "__main__":
    launch_gui()
