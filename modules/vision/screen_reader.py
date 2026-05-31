"""
CHARAMOU AI - VisionManager v2
OCR avancé, analyse d'interface, détection de boutons, contrôle visuel.
"""
import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from core.logger import setup_logger

logger = setup_logger("VisionManager")
SHOTS_DIR = Path.home() / "Pictures" / "CHARAMOU_Screenshots"


class ScreenReader:
    """Capture, OCR et analyse d'interface."""

    def __init__(self):
        self._pil_ok  = self._check("PIL",        "from PIL import Image, ImageGrab")
        self._tess_ok = self._check("Tesseract",  "import pytesseract; pytesseract.get_tesseract_version()")
        self._cv2_ok  = self._check("OpenCV",     "import cv2")
        self._easy_ok = self._check("EasyOCR",    "import easyocr")
        SHOTS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"VisionManager — PIL:{self._pil_ok} Tesseract:{self._tess_ok} "
            f"OpenCV:{self._cv2_ok} EasyOCR:{self._easy_ok}"
        )

    def _check(self, name: str, stmt: str) -> bool:
        try:
            exec(stmt)
            return True
        except Exception:
            return False

    # ── Capture ───────────────────────────────────────────────────────────────

    def capture(self, region: Tuple[int,int,int,int] = None):
        """Capture l'écran (PIL Image)."""
        if not self._pil_ok:
            raise RuntimeError("Pillow requis : pip install Pillow")
        from PIL import ImageGrab
        return ImageGrab.grab(bbox=region)

    def save_screenshot(self, region=None) -> str:
        from datetime import datetime
        img  = self.capture(region)
        path = SHOTS_DIR / f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        img.save(str(path))
        logger.info(f"Screenshot : {path.name}")
        return str(path)

    # ── OCR principal ─────────────────────────────────────────────────────────

    def read_screen(self, region=None, lang: str = "fra+eng") -> str:
        """
        Lit le texte de l'écran.
        Préfère EasyOCR (meilleure précision) si disponible, sinon Tesseract.
        """
        img = self.capture(region)
        if self._easy_ok:
            return self._ocr_easyocr(img)
        if self._tess_ok:
            return self._ocr_tesseract(img, lang)
        return "OCR non disponible. Installez Tesseract ou EasyOCR."

    def read_image_file(self, path: str, lang: str = "fra+eng") -> str:
        """OCR d'un fichier image."""
        if self._tess_ok:
            import pytesseract
            from PIL import Image
            return pytesseract.image_to_string(Image.open(path), lang=lang).strip()
        if self._easy_ok:
            import easyocr
            reader = easyocr.Reader(["fr", "en"], gpu=False)
            result = reader.readtext(path, detail=0)
            return " ".join(result)
        return "OCR non disponible."

    def _ocr_tesseract(self, img, lang: str) -> str:
        import pytesseract
        raw  = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
        text = "\n".join(l.strip() for l in raw.split("\n") if l.strip())
        logger.info(f"Tesseract OCR : {len(text)} chars")
        return text

    def _ocr_easyocr(self, img) -> str:
        import easyocr, numpy as np
        reader = easyocr.Reader(["fr", "en"], gpu=False)
        arr    = np.array(img)
        result = reader.readtext(arr, detail=0)
        text   = " ".join(result)
        logger.info(f"EasyOCR : {len(text)} chars")
        return text

    # ── Détection d'éléments UI ───────────────────────────────────────────────

    def find_text_position(self, target: str, region=None) -> Optional[Tuple[int, int]]:
        """
        Localise un texte à l'écran et retourne ses coordonnées (x, y).
        Utile pour cliquer sur un bouton par son libellé.
        """
        if not self._tess_ok:
            return None
        import pytesseract
        img  = self.capture(region)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="fra+eng")
        for i, text in enumerate(data["text"]):
            if target.lower() in text.lower() and int(data["conf"][i]) > 40:
                x = data["left"][i] + data["width"][i] // 2
                y = data["top"][i]  + data["height"][i] // 2
                logger.info(f"'{target}' trouvé à ({x}, {y})")
                return (x, y)
        return None

    def detect_buttons(self, region=None) -> List[Dict[str, Any]]:
        """
        Détecte les éléments cliquables (boutons) via OpenCV.
        Retourne une liste de {text, x, y, w, h, confidence}.
        """
        if not (self._cv2_ok and self._tess_ok):
            return []
        import cv2, pytesseract, numpy as np
        img   = self.capture(region)
        gray  = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        # Détection des rectangles (bordures boutons)
        edges = cv2.Canny(gray, 50, 150)
        cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        buttons = []
        for cnt in cnts:
            x, y, w, h = cv2.boundingRect(cnt)
            if 30 < w < 400 and 15 < h < 80:  # Taille typique bouton
                roi  = img.crop((x, y, x+w, y+h))
                text = pytesseract.image_to_string(roi, config="--psm 8").strip()
                if text:
                    buttons.append({"text": text, "x": x+w//2, "y": y+h//2, "w": w, "h": h})
        logger.info(f"{len(buttons)} bouton(s) détecté(s)")
        return buttons

    def click_button(self, label: str) -> bool:
        """Clique sur un bouton par son texte."""
        pos = self.find_text_position(label)
        if pos:
            try:
                import pyautogui
                pyautogui.click(pos[0], pos[1])
                logger.info(f"Clic sur '{label}' à {pos}")
                return True
            except ImportError:
                logger.warning("pyautogui requis pour le clic.")
        return False

    def highlight_region(self, x: int, y: int, w: int, h: int, color=(0, 255, 0)) -> None:
        """Surligne une région sur l'écran (OpenCV overlay)."""
        if not self._cv2_ok:
            return
        import cv2, numpy as np
        img   = self.capture()
        arr   = np.array(img)
        cv2.rectangle(arr, (x, y), (x+w, y+h), color, 3)
        cv2.imshow("CHARAMOU Vision", arr)
        cv2.waitKey(1500)
        cv2.destroyAllWindows()

    # ── Analyse d'image avancée ───────────────────────────────────────────────

    def get_screen_summary(self, region=None) -> str:
        """Retourne un résumé textuel du contenu visible."""
        try:
            text = self.read_screen(region)
            if not text:
                return "Aucun texte lisible à l'écran."
            lines = [l for l in text.split("\n") if len(l) > 3][:8]
            return "Contenu écran : " + " | ".join(lines[:5])
        except Exception as e:
            return f"Impossible de lire l'écran : {e}"

    def compare_screenshots(self, img1_path: str, img2_path: str) -> float:
        """
        Compare deux captures d'écran.
        Retourne un score de similarité entre 0 (différent) et 1 (identique).
        """
        if not (self._cv2_ok and self._pil_ok):
            return 0.0
        import cv2, numpy as np
        img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None:
            return 0.0
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        diff = cv2.absdiff(img1, img2)
        score = 1.0 - (diff.mean() / 255.0)
        return round(score, 3)

    # ── Lecture de documents ──────────────────────────────────────────────────

    def read_document(self, path: str) -> str:
        """Délègue la lecture au KnowledgeManager selon l'extension."""
        ext = Path(path).suffix.lower()
        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
            return self.read_image_file(path)
        return f"Extension '{ext}' non supportée par VisionManager. Utilisez KnowledgeManager."

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            "screen_capture":  self._pil_ok,
            "ocr_tesseract":   self._tess_ok,
            "ocr_easyocr":     self._easy_ok,
            "computer_vision": self._cv2_ok,
            "button_detection": self._cv2_ok and self._tess_ok,
            "click_by_text":   self._tess_ok,
        }


class OCR:
    """Raccourci OCR."""
    def __init__(self): self._r = ScreenReader()
    def read_image(self, p): return self._r.read_image_file(p)
    def read_screen(self):   return self._r.read_screen()
