import math
import re
from typing import List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth in meters using the Haversine formula.
    """
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def clean_and_tokenize(text: str) -> str:
    """
    Lowercase, strip punctuation, and perform lightweight suffix normalization
    without requiring heavy external corpus downloads.
    """
    text = text.lower()
    words = re.findall(r"\b[a-z]{3,}\b", text)
    # Lightweight rule-based suffix normalization (ing, ed, s, es)
    normalized = []
    for w in words:
        if w.endswith("ing") and len(w) > 5:
            w = w[:-3]
        elif w.endswith("ies") and len(w) > 5:
            w = w[:-3] + "y"
        elif w.endswith("es") and len(w) > 4:
            w = w[:-2]
        elif w.endswith("ed") and len(w) > 4:
            w = w[:-2]
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        normalized.append(w)
    return " ".join(normalized)


class GrievanceTriageEngine:
    """
    Classical ML & Heuristic Triage Engine:
    1. Spatial-Semantic Duplicate Detection
    2. Category & Department Routing
    3. Urgency & Priority Scoring
    """

    CRITICAL_KEYWORDS = {
        "spark", "sparks", "fire", "live wire", "shock", "explosion",
        "collapse", "collapsed", "gas leak", "burst", "sinkhole", "danger"
    }

    HIGH_KEYWORDS = {
        "flood", "flooding", "overflow", "accident", "open manhole",
        "contamination", "sewage leak", "deep pothole", "severe"
    }

    CATEGORY_KEYWORD_MAP = {
        "Electricity & Power": [
            "wire", "transformer", "spark", "blackout", "pole", "fuse",
            "meter", "voltage", "current", "streetlight", "light"
        ],
        "Water Supply": [
            "water", "pipeline", "leakage", "leak", "pipe", "tap",
            "sewage", "drainage", "contamination", "pressure", "muddy"
        ],
        "Roads & Infrastructure": [
            "road", "pothole", "asphalt", "junction", "pavement",
            "traffic light", "divider", "footpath", "speed breaker", "bridge"
        ],
        "Sanitation & Waste": [
            "garbage", "dump", "trash", "waste", "bin", "smell",
            "cleanliness", "debris", "dead animal", "sweeping"
        ]
    }

    @classmethod
    def evaluate_priority(cls, title: str, description: str) -> str:
        text = f"{title} {description}".lower()
        for kw in cls.CRITICAL_KEYWORDS:
            if kw in text:
                return "critical"
        for kw in cls.HIGH_KEYWORDS:
            if kw in text:
                return "high"
        return "medium"

    @classmethod
    def predict_category(cls, title: str, description: str) -> str:
        text = f"{title} {description}".lower()
        scores = {}
        for category, keywords in cls.CATEGORY_KEYWORD_MAP.items():
            count = sum(1 for kw in keywords if kw in text)
            scores[category] = count

        best_category = max(scores, key=scores.get)
        if scores[best_category] > 0:
            return best_category
        return "General Civic Issue"

    @staticmethod
    def detect_duplicate(
        new_title: str,
        new_desc: str,
        new_lat: Optional[float],
        new_lon: Optional[float],
        active_complaints: List[dict]
    ) -> Tuple[bool, Optional[int], float, Optional[float]]:
        """
        Evaluates active complaints for duplicates using:
        1. Haversine distance calculation
        2. Normalized TF-IDF Cosine text similarity
        3. Dynamic spatial-semantic thresholding

        Returns: (is_duplicate, matched_complaint_id, similarity_score, distance_in_meters)
        """
        if not active_complaints:
            return False, None, 0.0, None

        candidates = []
        for c in active_complaints:
            dist = None
            if (
                new_lat is not None
                and new_lon is not None
                and c.get("latitude") is not None
                and c.get("longitude") is not None
            ):
                dist = haversine_distance(new_lat, new_lon, float(c["latitude"]), float(c["longitude"]))
                if dist <= 300.0:  # Candidates within 300m
                    candidates.append((c, dist))
            else:
                candidates.append((c, None))

        if not candidates:
            return False, None, 0.0, None

        query_cleaned = clean_and_tokenize(f"{new_title} {new_desc}")
        candidate_texts = [
            clean_and_tokenize(f"{item[0]['title']} {item[0]['description']}")
            for item in candidates
        ]

        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([query_cleaned] + candidate_texts)

        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

        best_idx = similarities.argmax()
        max_score = float(similarities[best_idx])
        matched_complaint, matched_dist = candidates[best_idx]

        # Multi-tiered civic thresholding logic:
        # 1. Hyper-local (<= 50 meters): moderate text overlap (>= 0.20) flags duplicate
        # 2. Local vicinity (51 to 150 meters): requires >= 0.35 similarity
        # 3. Ward vicinity (151 to 300 meters): requires >= 0.50 similarity
        # 4. Unknown location / Coordinate-free: requires >= 0.65 similarity
        if matched_dist is not None:
            if matched_dist <= 50.0:
                is_duplicate = max_score >= 0.20
            elif matched_dist <= 150.0:
                is_duplicate = max_score >= 0.35
            elif matched_dist <= 300.0:
                is_duplicate = max_score >= 0.50
            else:
                is_duplicate = False
        else:
            is_duplicate = max_score >= 0.65

        if is_duplicate:
            return True, matched_complaint["id"], max_score, matched_dist

        return False, None, max_score, matched_dist