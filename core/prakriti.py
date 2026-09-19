"""Prakriti Diagnostic Engine on 2-Simplex Vector Space with 30-Parameter Matrix."""
from typing import Any, Dict, List, Tuple
import numpy as np

# Dirichlet smoothing boundary to prevent log(0) in KL divergence calculations
DIRICHLET_EPSILON = 1e-4

PRAKRITI_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "Q01",
        "category": "Sharirika (Anatomical)",
        "question": "Body Frame and Physical Build",
        "options": {
            "A": {"desc": "Thin, slender, prominent veins/bones, difficulty gaining weight", "dosha": "V"},
            "B": {"desc": "Medium build, athletic, symmetrical musculature", "dosha": "P"},
            "C": {"desc": "Large, broad, well-developed chest, tendency to gain weight easily", "dosha": "K"}
        }
    },
    {
        "id": "Q02",
        "category": "Sharirika (Anatomical)",
        "question": "Skin Texture, Moisture and Complexion",
        "options": {
            "A": {"desc": "Dry, rough, darkish tone, prone to cracking, cold to touch", "dosha": "V"},
            "B": {"desc": "Warm, soft, reddish/pinkish, prone to freckles/moles/acne", "dosha": "P"},
            "C": {"desc": "Thick, smooth, oily, lustrous, cool, radiant", "dosha": "K"}
        }
    },
    {
        "id": "Q03",
        "category": "Sharirika (Anatomical)",
        "question": "Hair Characteristics",
        "options": {
            "A": {"desc": "Dry, brittle, frizzy, split ends, coarse", "dosha": "V"},
            "B": {"desc": "Soft, thin, straight, early greying or early balding", "dosha": "P"},
            "C": {"desc": "Thick, lustrous, dark, wavy, deeply rooted, oily", "dosha": "K"}
        }
    },
    {
        "id": "Q04",
        "category": "Sharirika (Anatomical)",
        "question": "Eye Features and Gaze",
        "options": {
            "A": {"desc": "Small, dry, blinking frequently, restless gaze", "dosha": "V"},
            "B": {"desc": "Medium, sharp, penetrating, sensitive to bright sunlight", "dosha": "P"},
            "C": {"desc": "Large, calm, attractive, prominent eyelashes, white sclera", "dosha": "K"}
        }
    },
    {
        "id": "Q05",
        "category": "Sharirika (Anatomical)",
        "question": "Teeth and Gums",
        "options": {
            "A": {"desc": "Irregular, crooked, protruding, dry gums, brittle", "dosha": "V"},
            "B": {"desc": "Medium, yellowish tint, soft gums prone to bleeding", "dosha": "P"},
            "C": {"desc": "Large, white, symmetrical, strong healthy gums", "dosha": "K"}
        }
    },
    {
        "id": "Q06",
        "category": "Sharirika (Anatomical)",
        "question": "Joint Structure and Cracking Sounds",
        "options": {
            "A": {"desc": "Prominent joints, popping/cracking sounds upon movement", "dosha": "V"},
            "B": {"desc": "Moderate, flexible, supple joints", "dosha": "P"},
            "C": {"desc": "Hidden joints, well-lubricated, firm, robust ligaments", "dosha": "K"}
        }
    },
    {
        "id": "Q07",
        "category": "Sharira Kriya (Physiological)",
        "question": "Appetite and Digestive Fire (Agni)",
        "options": {
            "A": {"desc": "Irregular, variable appetite; bloating; Vishamagni", "dosha": "V"},
            "B": {"desc": "Sharp, intense hunger, irritable if meal delayed; Tikshnagni", "dosha": "P"},
            "C": {"desc": "Slow, steady appetite, can skip meals without discomfort; Mandagni", "dosha": "K"}
        }
    },
    {
        "id": "Q08",
        "category": "Sharira Kriya (Physiological)",
        "question": "Thirst and Fluid Preference",
        "options": {
            "A": {"desc": "Variable thirst, preference for warm beverages", "dosha": "V"},
            "B": {"desc": "Excessive, intense thirst, preference for chilled/cold drinks", "dosha": "P"},
            "C": {"desc": "Low or mild thirst, minimal water intake sufficient", "dosha": "K"}
        }
    },
    {
        "id": "Q09",
        "category": "Sharira Kriya (Physiological)",
        "question": "Bowel Habits and Koshta (Gastrointestinal Motility)",
        "options": {
            "A": {"desc": "Hard, dry stools, prone to constipation and gas; Krura Koshta", "dosha": "V"},
            "B": {"desc": "Loose, soft, frequent stools, yellow; Mridu Koshta", "dosha": "P"},
            "C": {"desc": "Formed, heavy, regular once-daily evacuation; Madhyama Koshta", "dosha": "K"}
        }
    },
    {
        "id": "Q10",
        "category": "Sharira Kriya (Physiological)",
        "question": "Physical Stamina and Work Capacity (Bala)",
        "options": {
            "A": {"desc": "Quick bursts of energy followed by rapid fatigue", "dosha": "V"},
            "B": {"desc": "Moderate, goal-driven physical endurance", "dosha": "P"},
            "C": {"desc": "High sustained stamina, methodical endurance, slow to tire", "dosha": "K"}
        }
    },
    {
        "id": "Q11",
        "category": "Sharira Kriya (Physiological)",
        "question": "Sleep Quality and Duration (Nidra)",
        "options": {
            "A": {"desc": "Light, interrupted sleep, difficulty falling asleep (5-6h)", "dosha": "V"},
            "B": {"desc": "Sound, moderate sleep, wakes up alert and refreshed (6-7h)", "dosha": "P"},
            "C": {"desc": "Deep, heavy sleep, difficulty waking up, loves long sleep (8-10h)", "dosha": "K"}
        }
    },
    {
        "id": "Q12",
        "category": "Sharira Kriya (Physiological)",
        "question": "Dream Patterns (Svapna)",
        "options": {
            "A": {"desc": "Flying in sky, running, falling, anxiety, fast motion", "dosha": "V"},
            "B": {"desc": "Fire, light, lightning, conflicts, ambitious achievements", "dosha": "P"},
            "C": {"desc": "Water bodies, lakes, swans, romantic scenes, serene landscapes", "dosha": "K"}
        }
    },
    {
        "id": "Q13",
        "category": "Sharira Kriya (Physiological)",
        "question": "Perspiration and Body Odor (Sveda)",
        "options": {
            "A": {"desc": "Scanty perspiration, odorless, minimal sweating even in heat", "dosha": "V"},
            "B": {"desc": "Profuse, warm sweating, strong body odor, easily sweats", "dosha": "P"},
            "C": {"desc": "Moderate, slow onset of sweating, sweet or pleasant odor", "dosha": "K"}
        }
    },
    {
        "id": "Q14",
        "category": "Sharira Kriya (Physiological)",
        "question": "Weather Sensitivity and Thermal Preference",
        "options": {
            "A": {"desc": "Aversion to cold, dry wind, and winter; loves sunny warmth", "dosha": "V"},
            "B": {"desc": "Aversion to intense heat, humidity, and summer; loves cool places", "dosha": "P"},
            "C": {"desc": "Aversion to cold, damp, cloudy weather; thrives in dry warm climates", "dosha": "K"}
        }
    },
    {
        "id": "Q15",
        "category": "Sharira Kriya (Physiological)",
        "question": "Speech Characteristics and Voice (Shabda)",
        "options": {
            "A": {"desc": "Fast, talkative, high-pitched, sometimes rambling or hoarse", "dosha": "V"},
            "B": {"desc": "Sharp, articulate, convincing, authoritative, loud", "dosha": "P"},
            "C": {"desc": "Deep, melodious, calm, resonant, measured pace", "dosha": "K"}
        }
    },
    {
        "id": "Q16",
        "category": "Sharira Kriya (Physiological)",
        "question": "Gait and Movement Style (Gati)",
        "options": {
            "A": {"desc": "Fast, hasty, unsteady steps, constantly in motion", "dosha": "V"},
            "B": {"desc": "Medium, purposeful, determined, energetic steps", "dosha": "P"},
            "C": {"desc": "Slow, graceful, stable, steady stride", "dosha": "K"}
        }
    },
    {
        "id": "Q17",
        "category": "Sharira Kriya (Physiological)",
        "question": "Radial Pulse Quality (Nadi)",
        "options": {
            "A": {"desc": "Quick, thready, serpentine (Sarpa Gati)", "dosha": "V"},
            "B": {"desc": "Bounding, sharp, leaping (Manduka Gati)", "dosha": "P"},
            "C": {"desc": "Slow, broad, steady, swan-like (Hamsa Gati)", "dosha": "K"}
        }
    },
    {
        "id": "Q18",
        "category": "Sharira Kriya (Physiological)",
        "question": "Weight Fluctuations and Metabolism",
        "options": {
            "A": {"desc": "Difficulty gaining weight; loses weight rapidly under stress", "dosha": "V"},
            "B": {"desc": "Maintains weight easily; burns calories effectively", "dosha": "P"},
            "C": {"desc": "Gains weight easily; difficulty losing weight despite diets", "dosha": "K"}
        }
    },
    {
        "id": "Q19",
        "category": "Sharira Kriya (Physiological)",
        "question": "Tongue Coating Propensity (Jihwa)",
        "options": {
            "A": {"desc": "Dry, cracked tongue, rough, thin or absent coating", "dosha": "V"},
            "B": {"desc": "Reddish margins, yellowish or oily coating in center", "dosha": "P"},
            "C": {"desc": "Thick, white, moist mucus coating, smooth pale surface", "dosha": "K"}
        }
    },
    {
        "id": "Q20",
        "category": "Sharira Kriya (Physiological)",
        "question": "Body Temperature to Touch (Sparsha)",
        "options": {
            "A": {"desc": "Hands and feet chronically cold to touch", "dosha": "V"},
            "B": {"desc": "Consistently warm palms and soles", "dosha": "P"},
            "C": {"desc": "Cool and mildly moist or clammy to touch", "dosha": "K"}
        }
    },
    {
        "id": "Q21",
        "category": "Manasika (Psychological)",
        "question": "Memory and Learning Pattern (Medha / Smriti)",
        "options": {
            "A": {"desc": "Learns quickly, forgets quickly; short-term retention strong", "dosha": "V"},
            "B": {"desc": "Sharp intellect, analytical comprehension, photographic recall", "dosha": "P"},
            "C": {"desc": "Slow to grasp new concepts, but once learned, never forgets", "dosha": "K"}
        }
    },
    {
        "id": "Q22",
        "category": "Manasika (Psychological)",
        "question": "Emotional Reaction to Anger and Irritation (Krodha)",
        "options": {
            "A": {"desc": "Quick to get frightened or anxious; avoids confrontation", "dosha": "V"},
            "B": {"desc": "Quick to get angry, irritable, sharp-tongued, but cools down", "dosha": "P"},
            "C": {"desc": "Rarely gets angry, patient, forgiving, slow to take offense", "dosha": "K"}
        }
    },
    {
        "id": "Q23",
        "category": "Manasika (Psychological)",
        "question": "Decision Making and Mental Stability (Dhee / Dhriti)",
        "options": {
            "A": {"desc": "Hesitant, doubts decisions, changes mind frequently", "dosha": "V"},
            "B": {"desc": "Decisive, confident, structured, outcome-oriented", "dosha": "P"},
            "C": {"desc": "Deliberate, careful, once decided remains firmly committed", "dosha": "K"}
        }
    },
    {
        "id": "Q24",
        "category": "Manasika (Psychological)",
        "question": "Financial Spending and Resource Management",
        "options": {
            "A": {"desc": "Impulsive spending on small items; difficulty accumulating wealth", "dosha": "V"},
            "B": {"desc": "Spends money purposefully on luxury, quality, or ambition", "dosha": "P"},
            "C": {"desc": "Natural saver, frugal, cautious, accumulates long-term wealth", "dosha": "K"}
        }
    },
    {
        "id": "Q25",
        "category": "Manasika (Psychological)",
        "question": "Response Under Acute Stress or Pressure",
        "options": {
            "A": {"desc": "Anxiety, worry, racing thoughts, panic, insomnia", "dosha": "V"},
            "B": {"desc": "Aggression, irritation, critical nature, urgency", "dosha": "P"},
            "C": {"desc": "Withdrawal, silence, denial, slow stubbornness, comfort eating", "dosha": "K"}
        }
    },
    {
        "id": "Q26",
        "category": "Manasika (Psychological)",
        "question": "Loyalty, Faith and Conviction (Shraddha)",
        "options": {
            "A": {"desc": "Fickle convictions, easily swayed by new ideas or peers", "dosha": "V"},
            "B": {"desc": "Intellectual conviction, loyal to principles and logic", "dosha": "P"},
            "C": {"desc": "Deep, unshakable emotional loyalty and devotion", "dosha": "K"}
        }
    },
    {
        "id": "Q27",
        "category": "Manasika (Psychological)",
        "question": "Social Dynamics and Communication",
        "options": {
            "A": {"desc": "Loves socializing, initiates conversations, large transient circle", "dosha": "V"},
            "B": {"desc": "Leader in social groups, charismatic, argumentative, competitive", "dosha": "P"},
            "C": {"desc": "Introverted or calm in groups, prefers few deep lifelong friends", "dosha": "K"}
        }
    },
    {
        "id": "Q28",
        "category": "Manasika (Psychological)",
        "question": "Dietary Flavor Preference (Rasa Satmya)",
        "options": {
            "A": {"desc": "Strongly craves sweet, sour, and salty warm comfort foods", "dosha": "V"},
            "B": {"desc": "Strongly craves sweet, bitter, and astringent refreshing foods", "dosha": "P"},
            "C": {"desc": "Strongly craves pungent, bitter, and astringent light warm foods", "dosha": "K"}
        }
    },
    {
        "id": "Q29",
        "category": "Manasika (Psychological)",
        "question": "Mental Resilience and Courage (Sattva Bala)",
        "options": {
            "A": {"desc": "Avara (Low resilience, easily demoralized by minor setbacks)", "dosha": "V"},
            "B": {"desc": "Madhyama (Moderate resilience, determined to overcome obstacles)", "dosha": "P"},
            "C": {"desc": "Pravara (High enduring resilience, unshakable fortitude)", "dosha": "K"}
        }
    },
    {
        "id": "Q30",
        "category": "Manasika (Psychological)",
        "question": "Sexual Vigor and Reproductive Energy (Shukra)",
        "options": {
            "A": {"desc": "Variable desire, easily depleted vitality", "dosha": "V"},
            "B": {"desc": "Moderate, passionate, fiery interest", "dosha": "P"},
            "C": {"desc": "High, steady endurance, deep enduring reproductive vitality", "dosha": "K"}
        }
    }
]


def compute_prakriti_simplex(answers: Dict[str, str]) -> Tuple[float, float, float, str, str]:
    """
    Compute normalized Barycentric coordinates (v, p, k) on the 2-simplex Delta^2.
    Enforces sum(v, p, k) == 1.0 and min(v, p, k) >= DIRICHLET_EPSILON.
    Returns (vata, pitta, kapha, primary_dosha, classification).
    """
    count_v = 0.0
    count_p = 0.0
    count_k = 0.0

    for q in PRAKRITI_QUESTIONS:
        qid = q["id"]
        chosen = answers.get(qid, "").upper()
        if chosen in q["options"]:
            dosha = q["options"][chosen]["dosha"]
            if dosha == "V":
                count_v += 1.0
            elif dosha == "P":
                count_p += 1.0
            elif dosha == "K":
                count_k += 1.0

    total_answered = count_v + count_p + count_k
    if total_answered == 0:
        return 0.3333, 0.3333, 0.3334, "TRIDOSHA", "SAMA_TRIDOSHA"

    # Convex combination with centroid to strictly enforce min(v, p, k) >= DIRICHLET_EPSILON
    raw_v = count_v / total_answered
    raw_p = count_p / total_answered
    raw_k = count_k / total_answered

    eps = DIRICHLET_EPSILON
    v = float((1.0 - 3.0 * eps) * raw_v + eps)
    p = float((1.0 - 3.0 * eps) * raw_p + eps)
    k = float(1.0 - (v + p))

    # Guard precision to 4 decimal places while maintaining >= eps
    v = max(round(v, 4), eps)
    p = max(round(p, 4), eps)
    k = round(1.0 - (v + p), 4)
    if k < eps:
        k = eps
        # Adjust top coordinate
        if v >= p:
            v = round(1.0 - (p + k), 4)
        else:
            p = round(1.0 - (v + k), 4)

    scores = [("VATA", v), ("PITTA", p), ("KAPHA", k)]
    canonical_order = {"VATA": 0, "PITTA": 1, "KAPHA": 2}
    # Sort primarily by score descending; break near-ties within 0.005 by classical order
    scores.sort(key=lambda x: (-round(x[1], 2), canonical_order[x[0]]))

    top_dosha, top_score = scores[0]
    second_dosha, second_score = scores[1]
    third_dosha, third_score = scores[2]

    # Classification logic based on Charaka Samhita guidelines
    # Check for Samadosha (all three doshas balanced within +/- 0.06 of 0.333)
    if all(abs(score - 0.3333) <= 0.06 for _, score in scores):
        classification = "SAMA_TRIDOSHA"
        primary_dosha = "TRIDOSHA"
    # Ekadoshaja: dominant dosha >= 0.48 and difference to 2nd is >= 0.12
    elif top_score >= 0.48 and (top_score - second_score) >= 0.12:
        classification = f"{top_dosha}_PRADHAN"
        primary_dosha = top_dosha
    # Dvandvaja: two dominant doshas
    else:
        classification = f"{top_dosha}_{second_dosha}"
        primary_dosha = top_dosha

    return round(v, 4), round(p, 4), round(k, 4), primary_dosha, classification
