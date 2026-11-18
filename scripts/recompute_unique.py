import json
import re
import math
import numpy as np
from collections import Counter
from scipy.stats import chi2 as chi2_dist

cp = json.load(open('tests/data/eval_checkpoint_1000.json', 'r', encoding='utf-8'))

def clean_claim_text(text):
    return re.sub(r'\s*\((Observation|Myth variant|Hypothesis)\s*#\d+\)', '', text).strip()

# Deduplicate: first occurrence of each unique base proposition
unique_claims = {}
cluster_map = {} # base_text -> list of evaluated items

for cid, item in cp.items():
    if len(item.get('evaluations', {})) != 3:
        continue
    base = clean_claim_text(item['claim'])
    if base not in unique_claims:
        unique_claims[base] = item
        cluster_map[base] = []
    cluster_map[base].append(item)

n_u = len(unique_claims)
print(f"=== 1. Deduplicated Unique Dataset (N = {n_u}) ===")

classes = ['True', 'False', 'Unverifiable']
class_counts = {c: sum(1 for item in unique_claims.values() if item['expected'] == c) for c in classes}
print(f"Class distribution: True={class_counts['True']}, False={class_counts['False']}, Unverifiable={class_counts['Unverifiable']}")

systems = ['factguard_full', 'baseline_raw_search', 'baseline_ungrounded']
system_names = {
    'factguard_full': 'FactGuard AI',
    'baseline_raw_search': 'Raw Web Search + LLM',
    'baseline_ungrounded': 'Ungrounded Zero-Shot'
}

matrices = {}
accuracies = {}
per_class_recalls = {}
decisive_stats = {}

for sys in systems:
    mat = {exp: {pred: 0 for pred in classes} for exp in classes}
    for item in unique_claims.values():
        exp = item['expected']
        pred = item['evaluations'][sys].get('verdict')
        if pred in classes:
            mat[exp][pred] += 1
    matrices[sys] = mat

    correct = sum(mat[c][c] for c in classes)
    accuracies[sys] = correct / n_u
    
    recalls = {c: mat[c][c] / class_counts[c] for c in classes}
    per_class_recalls[sys] = recalls
    
    decisive_n = sum(mat[exp]['True'] + mat[exp]['False'] for exp in classes)
    decisive_corr = mat['True']['True'] + mat['False']['False']
    decisive_stats[sys] = {
        'decisive_n': decisive_n,
        'decisive_corr': decisive_corr,
        'coverage': decisive_n / n_u,
        'precision': decisive_corr / decisive_n if decisive_n > 0 else 0
    }

print("\n=== 2. Overall Performance on Deduplicated Claims (N = 564) ===")
for sys in systems:
    print(f"{system_names[sys]}:")
    print(f"  Accuracy: {accuracies[sys]*100:.2f}% ({sum(matrices[sys][c][c] for c in classes)}/{n_u})")
    print(f"  Coverage: {decisive_stats[sys]['coverage']*100:.2f}% ({decisive_stats[sys]['decisive_n']}/{n_u})")
    print(f"  Selective Precision: {decisive_stats[sys]['precision']*100:.2f}% ({decisive_stats[sys]['decisive_corr']}/{decisive_stats[sys]['decisive_n']})")
    print(f"  Recall by class: True={per_class_recalls[sys]['True']*100:.1f}%, False={per_class_recalls[sys]['False']*100:.1f}%, Unverifiable={per_class_recalls[sys]['Unverifiable']*100:.1f}%")

print("\n=== 3. Confusion Matrices (N = 564) ===")
for sys in systems:
    print(f"Matrix: {system_names[sys]}")
    print("Exp \\ Pred     |  True | False | Unverifiable | Total")
    for exp in classes:
        t = matrices[sys][exp]['True']
        f = matrices[sys][exp]['False']
        u = matrices[sys][exp]['Unverifiable']
        print(f"{exp:14} | {t:5} | {f:5} | {u:12} | {t+f+u}")
    print()

# McNemar tests on deduplicated N=564
def calc_mcnemar_paired(sys_a, sys_b):
    b = 0
    c = 0
    both_correct = 0
    both_wrong = 0
    for item in unique_claims.values():
        exp = item['expected']
        a_corr = (item['evaluations'][sys_a].get('verdict') == exp)
        b_corr = (item['evaluations'][sys_b].get('verdict') == exp)
        if a_corr and b_corr:
            both_correct += 1
        elif a_corr and not b_corr:
            b += 1
        elif not a_corr and b_corr:
            c += 1
        else:
            both_wrong += 1
    
    diff = (b - c) / n_u
    se = math.sqrt((b + c) - ((b - c)**2) / n_u) / n_u
    ci_low = diff - 1.95996 * se
    ci_high = diff + 1.95996 * se
    
    discordant = b + c
    if discordant > 0:
        chi2 = (abs(b - c) - 1.0)**2 / discordant
        p_val = chi2_dist.sf(chi2, 1)
    else:
        chi2, p_val = 0.0, 1.0
        
    return {
        'both_correct': both_correct,
        'b': b,
        'c': c,
        'both_wrong': both_wrong,
        'diff': diff,
        'ci': (ci_low, ci_high),
        'chi2': chi2,
        'p_val': p_val
    }

m_raw = calc_mcnemar_paired('factguard_full', 'baseline_raw_search')
m_zs = calc_mcnemar_paired('factguard_full', 'baseline_ungrounded')

print("=== 4. Paired Differences on Unique Claims (N = 564) ===")
print("FactGuard vs Raw Search:")
print(f"  FactGuard won alone (b): {m_raw['b']}, Raw Search won alone (c): {m_raw['c']} (Lead: {m_raw['b'] - m_raw['c']})")
print(f"  Paired accuracy difference: {m_raw['diff']*100:.2f}% [95% CI: {m_raw['ci'][0]*100:.2f}% to {m_raw['ci'][1]*100:.2f}%]")
print(f"  McNemar chi2 = {m_raw['chi2']:.4f}, p-value = {m_raw['p_val']:.4f}")

print("\nFactGuard vs Zero-Shot:")
print(f"  FactGuard won alone (b): {m_zs['b']}, Zero-Shot won alone (c): {m_zs['c']} (Lead: {m_zs['b'] - m_zs['c']})")
print(f"  Paired accuracy difference: {m_zs['diff']*100:.2f}% [95% CI: {m_zs['ci'][0]*100:.2f}% to {m_zs['ci'][1]*100:.2f}%]")
print(f"  McNemar chi2 = {m_zs['chi2']:.4f}, p-value = {m_zs['p_val']:.6f}")

# === 5. Cluster Bootstrap on Full 1,000 Dataset ===
# Resample the 564 clusters with replacement (10,000 iterations)
np.random.seed(42)
cluster_keys = list(cluster_map.keys())
n_clusters = len(cluster_keys)

n_boot = 10000
boot_diffs_raw = []
boot_diffs_zs = []

for _ in range(n_boot):
    sampled_indices = np.random.choice(n_clusters, size=n_clusters, replace=True)
    fg_corr = 0
    raw_corr = 0
    zs_corr = 0
    total_items = 0
    
    for idx in sampled_indices:
        items = cluster_map[cluster_keys[idx]]
        for item in items:
            exp = item['expected']
            total_items += 1
            if item['evaluations']['factguard_full'].get('verdict') == exp:
                fg_corr += 1
            if item['evaluations']['baseline_raw_search'].get('verdict') == exp:
                raw_corr += 1
            if item['evaluations']['baseline_ungrounded'].get('verdict') == exp:
                zs_corr += 1
                
    diff_raw = (fg_corr - raw_corr) / total_items
    diff_zs = (fg_corr - zs_corr) / total_items
    boot_diffs_raw.append(diff_raw)
    boot_diffs_zs.append(diff_zs)

boot_diffs_raw = np.array(boot_diffs_raw)
boot_diffs_zs = np.array(boot_diffs_zs)

raw_ci_boot = (np.percentile(boot_diffs_raw, 2.5), np.percentile(boot_diffs_raw, 97.5))
raw_p_boot = np.mean(boot_diffs_raw <= 0) * 2 # two-sided bootstrap p

zs_ci_boot = (np.percentile(boot_diffs_zs, 2.5), np.percentile(boot_diffs_zs, 97.5))
zs_p_boot = np.mean(boot_diffs_zs <= 0) * 2

print("\n=== 5. Cluster Bootstrap (10,000 resamples of clusters) ===")
print("FactGuard vs Raw Search (Cluster Bootstrap):")
print(f"  Mean paired diff: {np.mean(boot_diffs_raw)*100:.2f}%")
print(f"  Cluster-robust 95% CI: [{raw_ci_boot[0]*100:.2f}% to {raw_ci_boot[1]*100:.2f}%]")
print(f"  Cluster bootstrap p-value: p = {raw_p_boot:.4f}")

print("\nFactGuard vs Zero-Shot (Cluster Bootstrap):")
print(f"  Mean paired diff: {np.mean(boot_diffs_zs)*100:.2f}%")
print(f"  Cluster-robust 95% CI: [{zs_ci_boot[0]*100:.2f}% to {zs_ci_boot[1]*100:.2f}%]")
print(f"  Cluster bootstrap p-value: p = {zs_p_boot:.6f}")
