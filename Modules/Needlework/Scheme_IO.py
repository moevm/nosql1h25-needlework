import Scheme
import json
from typing import Dict, Any

class SchemeIO:
    @staticmethod
    def save_to_json(scheme: Scheme, file_path: str) -> None:
        """Сохраняет схему в JSON в сжатом формате."""
        data = {
            "scheme_type": scheme.get_scheme_type(),
            "encoded_pattern": scheme.encode()
        }
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file)

    @staticmethod
    def load_from_json(file_path: str) -> Scheme:
        """Загружает схему из JSON и декодирует её."""
        with open(file_path, 'r', encoding='utf-8') as file:
            data: Dict[str, Any] = json.load(file)
            return Scheme.decode(
                encoded_str=data["encoded_pattern"],
                scheme_type=data["scheme_type"]
            )