from typing import List, Dict
import json
from pathlib import Path

JSON_DIR = Path('notebooks/qa_json/geoffrey_json_PS_P02_AAP03_08092025.json')
GT_DIR = Path('notebooks/qa_json/ground_truth_ps_p02_aap03.json')

def count_keys_question(dicts : List[Dict]) -> int:
    """check automatisé pour compter le nombre de questions extraites"""
    return sum(1 for q in dicts if "question" in q)

def count_keys_gt(dicts : List[Dict]) -> int:
    """Compte le nombre de questions dans le ground truth."""
    return sum(1 for q in dicts if "question" in q)

def diff_vs_gt(dicts : List[Dict], ground_truth : List[Dict]) -> int:
    """Calcule la différence entre le nombre de questions et le ground truth."""
    difference = count_keys_gt(ground_truth) - count_keys_question(dicts)
    return difference

if __name__ == "__main__":
    with open(JSON_DIR,"r", encoding="utf-8") as f:
        data = json.load(f)
    with open(GT_DIR,"r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    print("Nombre total de questions extraites :", count_keys_question(data))
    print("Nombre total de questions (ground_truth) :", count_keys_gt(ground_truth))
    print("Différence avec le ground truth :", diff_vs_gt(data, ground_truth))
