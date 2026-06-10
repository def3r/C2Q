"""
VQE simulation for Minimum Vertex Cover using only the QASM exported from C2|Q>.

Parses the Ising Hamiltonian directly from mvc_qaoa.qasm.
Hardware-efficient RY+CZ ansatz is loaded from mvc_vqe.qasm.
No JSON file dependency.

Instance: 4-node cycle graph, edges (0,1),(1,2),(2,3),(3,0).
Optimal cover size = 2: {0,2} or {1,3}.
"""
import re
import numpy as np
from collections import Counter
from scipy.optimize import minimize
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

# ── Parse Ising Hamiltonian from QAOA QASM ────────────────────────────────────
with open("mvc_qaoa.qasm") as f:
    qaoa_src = f.read()

h = {}   # qubit → linear coefficient
J = {}   # (i,j) → quadratic coefficient

for m in re.finditer(r"rz\(([^)]+)\)\s+q\[(\d+)\]", qaoa_src):
    expr, qi = m.group(1), int(m.group(2))
    nums = re.findall(r"[-+]?\d*\.?\d+", expr.split("*")[0])
    if nums:
        h[qi] = h.get(qi, 0.0) + float(nums[0]) / 2.0

for m in re.finditer(r"rzz\(([^)]+)\)\s+q\[(\d+)\],\s*q\[(\d+)\]", qaoa_src):
    expr, qi, qj = m.group(1), int(m.group(2)), int(m.group(3))
    nums = re.findall(r"[-+]?\d*\.?\d+", expr.split("*")[0])
    if nums:
        J[(qi, qj)] = J.get((qi, qj), 0.0) + float(nums[0]) / 2.0

N = max(max(h, default=-1), max((k for pair in J for k in pair), default=-1)) + 1
print(f"Ising Hamiltonian: {N} qubits, {len(h)} local terms, {len(J)} coupling terms")

def ising_energy(bits):
    """bits[i] in {0,1}; H(b)=Σhᵢ(1-2bᵢ)+ΣJᵢⱼ(1-2bᵢ)(1-2bⱼ)"""
    s = {i: 1 - 2 * bits[i] for i in range(N)}
    E = sum(h[i] * s[i] for i in h)
    E += sum(J[(i, j)] * s[i] * s[j] for (i, j) in J)
    return E

# ── Load VQE QASM ─────────────────────────────────────────────────────────────
with open("mvc_vqe.qasm") as f:
    vqe_src = f.read()

n_params = len(re.findall(r"input float\[64\]", vqe_src))
print(f"VQE ansatz: {n_params} parameters\n")

backend = AerSimulator()

def bind_vqe(src, params):
    s = src
    for i, p in enumerate(params):
        s = s.replace(f"input float[64] _θ_{i}_;\n", "")
        s = s.replace(f"_θ_{i}_", str(p))
    return s

def expected_energy(params, shots=512):
    qc = qasm3.loads(bind_vqe(vqe_src, params))
    counts = backend.run(transpile(qc, backend), shots=shots).result().get_counts()
    E = 0.0
    for bitstr, cnt in counts.items():
        bits = [int(x) for x in reversed(bitstr.replace(" ", ""))]
        E += cnt * ising_energy(bits)
    return E / shots

# ── Optimise ──────────────────────────────────────────────────────────────────
print("Optimising VQE (5 restarts)...")
best_params, best_E = None, np.inf
np.random.seed(42)
for trial in range(5):
    x0 = np.random.uniform(0, 2 * np.pi, n_params)
    res = minimize(expected_energy, x0, method="COBYLA",
                   options={"maxiter": 300, "rhobeg": 0.5})
    if res.fun < best_E:
        best_E, best_params = res.fun, res.x
    print(f"  Trial {trial+1}: E={res.fun:.4f}")

print(f"\nBest E[H] = {best_E:.4f}")

# ── Final sample ──────────────────────────────────────────────────────────────
qc = qasm3.loads(bind_vqe(vqe_src, best_params))
counts = backend.run(transpile(qc, backend), shots=2048).result().get_counts()

EDGES = [(0, 1), (1, 2), (2, 3), (3, 0)]

def is_valid_cover(nodes):
    node_set = set(nodes)
    return all(u in node_set or v in node_set for u, v in EDGES)

min_cover_size = min(
    (len([v for v in range(N) if int(b.replace(" ", "")[::-1][v]) == 1])
     for b in counts
     if is_valid_cover([v for v in range(N) if int(b.replace(" ", "")[::-1][v]) == 1])),
    default=N
)

top = Counter(counts).most_common(8)
print(f"\n{'Bitstring':<8} {'Shots':>6}  Nodes in cover    Valid?  Size")
print("-" * 52)
for bitstr, cnt in top:
    bits = [int(x) for x in reversed(bitstr.replace(" ", ""))]
    nodes = [v for v in range(N) if bits[v] == 1]
    valid = is_valid_cover(nodes)
    flag = "  ← min cover" if valid and len(nodes) == min_cover_size else ("  ← valid" if valid else "")
    print(f"  {bitstr.replace(' ','')}  {cnt:>5}  {nodes}   {'yes' if valid else 'no':>5}     {len(nodes)}{flag}")

valid_shots = sum(cnt for b, cnt in counts.items()
                  if is_valid_cover([v for v in range(N) if int(b.replace(" ", "")[::-1][v]) == 1]))
min_shots = sum(cnt for b, cnt in counts.items()
                if is_valid_cover([v for v in range(N) if int(b.replace(" ", "")[::-1][v]) == 1])
                and len([v for v in range(N) if int(b.replace(" ", "")[::-1][v]) == 1]) == min_cover_size)
print(f"\nValid covers  : {valid_shots}/2048 = {valid_shots/2048:.1%}")
print(f"Min covers (≤{min_cover_size}): {min_shots}/2048 = {min_shots/2048:.1%}")
