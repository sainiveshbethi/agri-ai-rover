import json
import os
from typing import Dict, Any, Optional, List

class CropDatabaseService:
    def __init__(self, json_path: Optional[str] = None):
        if not json_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, "data", "crops.json")
        self.json_path = json_path
        self.crops: List[Dict[str, Any]] = []
        self.load_database()

    def load_database(self) -> None:
        """Loads crop database from JSON file."""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.crops = json.load(f)
            except Exception as e:
                print(f"[CropDatabaseService] Error loading crops.json: {e}")
                self.crops = []
        else:
            print(f"[CropDatabaseService] File not found: {self.json_path}")
            self.crops = []

    def get_crop(self, crop_name_or_alias: str) -> Optional[Dict[str, Any]]:
        """Finds crop profile by name, scientific name, or alias (case-insensitive)."""
        if not crop_name_or_alias or crop_name_or_alias.strip() in ["-", "—", "Unknown", "Not a crop/seed or unable to identify", "Unknown / Low confidence"]:
            return None

        query = crop_name_or_alias.strip().lower()

        # 1. Direct exact or substring match on crop_name or scientific_name
        for crop in self.crops:
            c_name = crop.get("crop_name", "").lower()
            s_name = crop.get("scientific_name", "").lower()
            if query == c_name or query == s_name:
                return crop

        # 2. Check aliases
        for crop in self.crops:
            aliases = [a.lower() for a in crop.get("aliases", [])]
            if query in aliases:
                return crop

        # 3. Substring match
        for crop in self.crops:
            c_name = crop.get("crop_name", "").lower()
            s_name = crop.get("scientific_name", "").lower()
            aliases = [a.lower() for a in crop.get("aliases", [])]
            if query in c_name or c_name in query or query in s_name or s_name in query:
                return crop
            for alias in aliases:
                if query in alias or alias in query:
                    return crop

        return None

    def get_all_crop_names(self) -> List[str]:
        """Returns list of all available crop names in database."""
        return [crop.get("crop_name", "") for crop in self.crops]
