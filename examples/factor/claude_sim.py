from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator
from collections import Counter
from math import gcd

N = 15
# C2Q picks a base 'a' coprime to N — need to know which one
# Common choices for N=15: a=7 or a=11
# Check the RGQFTMultiplier angle params to confirm, but try 7 first
A = 7
QPE_BITS = 2  # q1[0], q1[1]

def continued_fraction_period(phase_int, qpe_bits, N):
    """
    Convert measured integer m to phase m/2^qpe_bits,
    then find period r via continued fractions.
    """
    from fractions import Fraction
    phase = Fraction(phase_int, 2 ** qpe_bits)
    # convergents of the continued fraction
    frac = phase.limit_denominator(N)
    return frac.denominator

def shor_factors(a, r, N):
    if r % 2 != 0:
        return None, None
    x = pow(a, r // 2, N)
    if x == N - 1:
        return None, None
    f1 = gcd(x + 1, N)
    f2 = gcd(x - 1, N)
    return f1, f2

with open("factor_grover.qasm") as f:
    qasm_str = f.read()

# Patch reserved gate name
qasm_str = qasm_str.replace("gate unitary ", "gate unitary_id ")
qasm_str = qasm_str.replace("unitary ", "unitary_id ")
qasm_str = qasm_str.replace("gate unitary_0 ", "gate unitary_x0 ")
qasm_str = qasm_str.replace("unitary_0 ", "unitary_x0 ")
qasm_str = qasm_str.replace("gate unitary_1 ", "gate unitary_x1 ")
qasm_str = qasm_str.replace("unitary_1 ", "unitary_x1 ")

qc = qasm3.loads(qasm_str)
print(f"=== Shor's algorithm  N={N}, a={A} ===")
print(f"Circuit depth : {qc.depth()}")
print(f"Circuit qubits: {qc.num_qubits}  (QPE={QPE_BITS}, work={qc.num_qubits - QPE_BITS})")

backend = AerSimulator()
transpiled = transpile(qc, backend)
counts = backend.run(transpiled, shots=4096).result().get_counts()
top = Counter(counts).most_common(4)

print(f"\nRaw QPE outcomes:")
print(f"{'bitstr':>8}  {'count':>5}  {'m':>3}  {'phase':>8}  {'r':>4}  {'factors'}")
print("-" * 55)

found = set()
for bitstr, count in top:
    bits = bitstr.replace(" ", "")
    m = int(bits, 2)                          # measured integer
    phase = m / (2 ** QPE_BITS)              # estimated phase s/r

    r = continued_fraction_period(m, QPE_BITS, N)
    f1, f2 = shor_factors(A, r, N)

    factor_str = f"{f1} × {f2}" if f1 and f2 and f1 * f2 == N else "—"
    if f1 and f2 and f1 * f2 == N:
        found.add((min(f1,f2), max(f1,f2)))

    print(f"  |{bits}> : {count:4d}   m={m}  φ={phase:.4f}  r={r}  {factor_str}")

if found:
    for p, q in found:
        print(f"\n  ✓ {N} = {p} × {q}")
else:
    print(f"\n  ✗ No factors found — try A=11 or A=13")
