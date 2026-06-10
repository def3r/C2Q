"""
VQE simulation for MaxCut using only the QASM files exported from C2|Q>.

Run from this directory after generating the QASM files:
    c2q-json --input maxcut_01.json --export-qasm --qasm-output-dir .
Then:
    python vqe_sim.py

Two QASM files are used:
  max_cut_qaoa.qasm  — source of the Hamiltonian: each rzz(theta) q[i], q[j]
                       gate encodes one graph edge (i, j)
  max_cut_vqe.qasm   — the variational ansatz to optimize

On a real QPU the same split applies: the Hamiltonian specifies which
expectation values to measure, the ansatz is the circuit to run.
"""
import re
import numpy as np
from collections import Counter
from scipy.optimize import minimize
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

# ── Extract Hamiltonian (edges) from QAOA QASM ────────────────────────────────
# Each "rzz(...) q[i], q[j]" encodes one edge of the MaxCut graph.

with open("max_cut_qaoa.qasm") as f:
    qaoa_src = f.read()

edges = [
    (int(a), int(b))
    for a, b in re.findall(r"rzz\([^)]+\)\s+q\[(\d+)\],\s*q\[(\d+)\]", qaoa_src)
]
num_qubits = max(n for e in edges for n in e) + 1

print(f"Hamiltonian: {num_qubits} qubits, {len(edges)} edges {edges}")
print(f"Edge-count upper bound: {len(edges)}\n")

# ── Load VQE ansatz ───────────────────────────────────────────────────────────

with open("max_cut_vqe.qasm") as f:
    vqe_src = f.read()

num_params = len(re.findall(r"input float\[64\] _θ_\d+_;", vqe_src))
print(f"VQE ansatz: {num_params} variational parameters\n")

# ── Cost function ─────────────────────────────────────────────────────────────

backend = AerSimulator()

def bind_params(params):
    s = vqe_src
    for i, p in enumerate(params):
        s = s.replace(f"input float[64] _θ_{i}_;\n", "")
        s = s.replace(f"_θ_{i}_", str(p))
    return s

def expected_cut(params, shots=1024):
    """
    E[C] = Σ_{(i,j) ∈ edges} Pr[bit_i ≠ bit_j]

    Computed purely from Z-basis measurement counts — the same
    measurement a QPU would return.
    """
    qc = qasm3.loads(bind_params(params))
    counts = backend.run(transpile(qc, backend), shots=shots).result().get_counts()
    total = sum(counts.values())
    energy = 0.0
    for bitstr, cnt in counts.items():
        bits = bitstr.replace(" ", "")
        energy += cnt * sum(1 for i, j in edges if bits[i] != bits[j])
    return energy / total

def neg_cut(params):
    return -expected_cut(params, shots=512)

# ── Optimization ──────────────────────────────────────────────────────────────

print("Running VQE optimization (5 random restarts × COBYLA)...")
print(f"{'Restart':>7}  {'E[cut]':>8}  params[:3]")

best_params, best_energy = None, -np.inf
np.random.seed(0)

for restart in range(5):
    x0 = np.random.uniform(0, 2 * np.pi, num_params)
    res = minimize(neg_cut, x0, method="COBYLA", options={"maxiter": 300, "rhobeg": 0.5})
    energy = -res.fun
    marker = " ← best" if energy > best_energy else ""
    print(f"  {restart + 1:>5}    {energy:>7.3f}  {[round(p, 2) for p in res.x[:3]]}...{marker}")
    if energy > best_energy:
        best_energy = energy
        best_params = res.x

print(f"\nConverged — E[cut] = {best_energy:.4f} (edge-count upper bound: {len(edges)})\n")

# ── Final sample ──────────────────────────────────────────────────────────────

print("Sampling final circuit (4096 shots)...")
qc_final = qasm3.loads(bind_params(best_params))
counts = backend.run(transpile(qc_final, backend), shots=4096).result().get_counts()

def cut_value(bits):
    return sum(1 for i, j in edges if bits[i] != bits[j])

# Best cut found across all observed bitstrings — no ground-truth needed.
best_cut = max(cut_value(b.replace(" ", "")) for b in counts)

top = Counter(counts).most_common(6)
print(f"\n{'Bitstring':>10}  {'Shots':>6}  {'Cut':>4}  Partition")
print("-" * 52)
for bitstr, cnt in top:
    bits = bitstr.replace(" ", "")
    cut = cut_value(bits)
    s0 = [i for i, b in enumerate(bits) if b == "0"]
    s1 = [i for i, b in enumerate(bits) if b == "1"]
    flag = "  ← best found" if cut == best_cut else ""
    print(f"  |{bits}>  {cnt:>6}  {cut:>4}  S0={s0} S1={s1}{flag}")

best_shots = sum(cnt for bits, cnt in counts.items() if cut_value(bits.replace(" ", "")) == best_cut)
print(f"\nBest cut found: {best_cut}  ({best_shots}/4096 = {best_shots/4096:.1%} of shots)")
