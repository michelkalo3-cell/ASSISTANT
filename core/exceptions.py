"""CHARAMOU AI - Exceptions personnalisées v2"""

class CharamouBaseError(Exception):
    def __init__(self, message: str = "", recoverable: bool = True):
        super().__init__(message)
        self.recoverable = recoverable

class EngineError(CharamouBaseError): pass
class ConfigurationError(CharamouBaseError): pass
class PermissionDeniedError(CharamouBaseError):
    def __init__(self, action: str = ""):
        super().__init__(f"Permission refusée : '{action}'", recoverable=True)
        self.action = action
class ModuleLoadError(CharamouBaseError): pass
class RecoveryError(CharamouBaseError): pass
class SpeechRecognitionError(CharamouBaseError): pass
class SynthesisError(CharamouBaseError): pass
class MicrophoneError(CharamouBaseError): pass
class WakeWordError(CharamouBaseError): pass
class IntentDetectionError(CharamouBaseError): pass
class CommandParseError(CharamouBaseError): pass
class ServiceError(CharamouBaseError): pass
class WeatherServiceError(ServiceError): pass
class CalendarServiceError(ServiceError): pass
class EmailServiceError(ServiceError): pass
class SearchServiceError(ServiceError): pass
class ServiceUnavailableError(ServiceError):
    def __init__(self, service: str):
        super().__init__(f"Service '{service}' indisponible.", recoverable=True)
class AutomationError(CharamouBaseError): pass
class ApplicationNotFoundError(AutomationError): pass
class BrowserError(AutomationError): pass
class ValidationError(AutomationError): pass
class AIError(CharamouBaseError): pass
class APIKeyMissingError(AIError): pass
class ModelNotAvailableError(AIError): pass
class OllamaError(AIError): pass
class MemoryError(CharamouBaseError): pass
class DatabaseError(CharamouBaseError): pass
class EmbeddingError(CharamouBaseError): pass
class SecurityError(CharamouBaseError):
    def __init__(self, message: str = ""):
        super().__init__(message, recoverable=False)
class CommandBlockedError(SecurityError): pass
class AuditError(SecurityError): pass
