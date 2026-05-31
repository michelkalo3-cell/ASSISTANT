"""
CHARAMOU AI - SecureVault v1
Coffre-fort chiffré AES (Fernet) pour clés API et secrets.
Stockage local : data/vault.enc (chiffré) + data/vault.key (clé dérivée)

Flux :
  1. Première utilisation → génère une clé Fernet
  2. Les secrets sont chiffrés et persistés dans vault.enc
  3. Jamais de secret en clair sur disque ni dans les logs

Hiérarchie de lecture (par priorité décroissante) :
  1. SecureVault (vault.enc chiffré)
  2. Variables d'environnement (.env)
  3. None (service désactivé, warning loggé)
"""
import os
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from core.logger import setup_logger

logger = setup_logger("SecureVault_Security")

DATA_DIR   = Path(__file__).parent.parent / "data"
VAULT_FILE = DATA_DIR / "vault.enc"
KEY_FILE   = DATA_DIR / "vault.key"

# Noms de services connus
_SERVICE_MAP = {
    "openai":      "OPENAI_API_KEY",
    "openweather": "OPENWEATHER_API_KEY",
    "news":        "NEWS_API_KEY",
    "porcupine":   "PORCUPINE_ACCESS_KEY",
    "google":      "GOOGLE_API_KEY",
}


def _get_fernet():
    """Retourne l'instance Fernet (crée la clé si absente)."""
    from cryptography.fernet import Fernet
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not KEY_FILE.exists():
        key = Fernet.generate_key()
        KEY_FILE.write_bytes(key)
        KEY_FILE.chmod(0o600)          # Lecture seule pour le propriétaire
        logger.info("Clé Fernet générée → data/vault.key")
    else:
        key = KEY_FILE.read_bytes()

    return Fernet(key)


class SecureVault:
    """
    Coffre-fort chiffré AES-128-CBC (via Fernet).

    Usage :
        vault = SecureVault()
        vault.store("openai", "sk-xxxx")
        key = vault.get("openai")
    """

    def __init__(self):
        self._fernet = None
        self._data:  Dict[str, str] = {}
        self._init()

    def _init(self) -> None:
        try:
            from cryptography.fernet import Fernet, InvalidToken
            self._fernet = _get_fernet()
            self._load()
            logger.info(f"SecureVault initialisé — {len(self._data)} secret(s) chargé(s).")
        except ImportError:
            logger.warning("cryptography non installé — vault désactivé. (pip install cryptography)")
        except Exception as e:
            logger.error(f"Erreur init vault : {e}")

    # ── Persistance ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Charge et déchiffre le vault depuis le disque."""
        if not VAULT_FILE.exists():
            return
        try:
            from cryptography.fernet import InvalidToken
            encrypted = VAULT_FILE.read_bytes()
            decrypted = self._fernet.decrypt(encrypted)
            self._data = json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Impossible de lire le vault (corrompu ?) : {e}")
            self._data = {}

    def _save(self) -> None:
        """Chiffre et persiste le vault sur disque."""
        if not self._fernet:
            return
        try:
            plaintext = json.dumps(self._data, ensure_ascii=False).encode("utf-8")
            encrypted = self._fernet.encrypt(plaintext)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            VAULT_FILE.write_bytes(encrypted)
            VAULT_FILE.chmod(0o600)
        except Exception as e:
            logger.error(f"Impossible de sauvegarder le vault : {e}")

    # ── API publique ─────────────────────────────────────────────────────────

    def store(self, service: str, secret: str) -> bool:
        """Chiffre et stocke un secret."""
        if not secret or not secret.strip():
            logger.warning(f"Tentative de stockage d'un secret vide pour '{service}'")
            return False
        self._data[service.lower()] = secret.strip()
        self._save()
        logger.info(f"Secret '{service}' stocké dans le vault.")
        return True

    def get(self, service: str) -> Optional[str]:
        """
        Retourne le secret pour un service.
        Priorité : vault chiffré → variable d'environnement.
        """
        service_lower = service.lower()

        # 1. Vault chiffré
        secret = self._data.get(service_lower)
        if secret:
            return secret

        # 2. Variable d'environnement
        env_var = _SERVICE_MAP.get(service_lower, service.upper() + "_API_KEY")
        env_val = os.getenv(env_var, "").strip()
        if env_val:
            return env_val

        return None

    def delete(self, service: str) -> bool:
        """Supprime un secret du vault."""
        key = service.lower()
        if key in self._data:
            del self._data[key]
            self._save()
            logger.info(f"Secret '{service}' supprimé du vault.")
            return True
        return False

    def is_available(self, service: str) -> bool:
        return self.get(service) is not None

    def list_services(self) -> list:
        """Retourne la liste des services configurés (sans leurs valeurs)."""
        in_vault = list(self._data.keys())
        in_env   = [svc for svc, env in _SERVICE_MAP.items() if os.getenv(env)]
        return sorted(set(in_vault + in_env))

    def mask(self, secret: str) -> str:
        """Masque un secret pour l'affichage/logs."""
        if not secret or len(secret) < 8:
            return "***"
        return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"

    def migrate_from_env(self) -> int:
        """
        Importe automatiquement toutes les clés trouvées dans les variables
        d'environnement vers le vault chiffré.
        Retourne le nombre de clés migrées.
        """
        count = 0
        for service, env_var in _SERVICE_MAP.items():
            val = os.getenv(env_var, "").strip()
            if val and service not in self._data:
                self.store(service, val)
                count += 1
        if count:
            logger.info(f"Migration .env → vault : {count} clé(s) importée(s).")
        return count

    def export_env_template(self) -> str:
        """Génère un .env.example basé sur les services connus."""
        lines = ["# CHARAMOU AI — Variables d'environnement"]
        for svc, env_var in _SERVICE_MAP.items():
            status = "✓ configuré" if self.is_available(svc) else "non configuré"
            lines.append(f"# {status}")
            lines.append(f"{env_var}=")
        return "\n".join(lines)

    def summary(self) -> str:
        services = self.list_services()
        if not services:
            return "Vault : aucun secret configuré."
        masked = [f"{s}={self.mask(self._data.get(s, '***'))}" for s in services]
        return f"Vault ({len(services)} secret(s)) : {', '.join(services)}"


# ── Singleton global ──────────────────────────────────────────────────────────
_vault_instance: Optional[SecureVault] = None

def get_vault() -> SecureVault:
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = SecureVault()
    return _vault_instance
