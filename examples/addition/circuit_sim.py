"""
Simulate the ADD quantum ripple-carry circuit exported from C2|Q>.

Run from this directory after generating the QASM file:
    c2q-json --input add_01.json --export-qasm --qasm-output-dir .
Then:
    python circuit_sim.py

The circuit computes 3 + 5 = 8.  The most probable measurement outcome
should decode to 8 in the result register.
"""
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator
from collections import Counter

OPERAND_A = 113
OPERAND_B = 5

with open("add_circuit.qasm") as f:
    qasm_str = f.read()

qc = qasm3.loads(qasm_str)
print(f"=== ADD quantum circuit ({OPERAND_A} + {OPERAND_B}) ===")
print(qc.draw(output="text", fold=-1))
print(f"\nCircuit depth : {qc.depth()}")
print(f"Circuit qubits: {qc.num_qubits}")

backend = AerSimulator()
transpiled = transpile(qc, backend)
counts = backend.run(transpiled, shots=4096).result().get_counts()
top = Counter(counts).most_common(4)

print(f"\nTop measurement outcomes (expected result = {OPERAND_A + OPERAND_B}):")
for bitstr, count in top:
    bits = bitstr.replace(" ", "")
    # Qiskit big-endian: bits[0] = c[n-1] = carry-out, bits[-1] = c[0] = sum LSB
    overflow  = int(bits[0])     # carry-out is the MSB of the bitstring
    sum_bits  = bits[1:]         # remaining bits are sum, already big-endian
    result    = int(sum_bits, 2)
    print(f"  |{bits}> : {count:4d}   result={result}  overflow={overflow}")

#for bitstr, count in top:
#    bits = bitstr.replace(" ", "")
##    val = int(bits, 2)
##    print(f"  |{bits}> : {count:4d}   decimal={val}")
##
#    bits = bits.replace(" ", "")
#
#    print(f"Full bitstring ({len(bits)} bits): {bits}")
#    print(f"Qiskit order: rightmost = q0\n")
#
#    # Reverse once to get q0 on the left for easier reading
#    q_order = bits[::-1]
#    print(f"Qubit order (q0→q12): {q_order}")
#    print()
#
#    # Slide a 4-bit window across ALL positions
#    for start in range(len(q_order) - 3):
#        window = q_order[start:start+4]
#        val = int(window, 2)
#        print(f"  q[{start}:{start+4}] = {window} = {val}")
#
#    q_order = bits[::-1]          # flip: q0 on left
#    sum_bits = q_order[11:15]     # sum register lives at q11–q14
#    result = int(sum_bits, 2)
#    print(f"Result = {result}")   # 8 ✓
