import re
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

gamma, beta = 1.0, 0.5

with open("mis_qaoa.qasm") as f:
    qasm_str = f.read()

qasm_str = re.sub(r"input float\[64\] _theta_0_;\n", "", qasm_str)
qasm_str = re.sub(r"input float\[64\] _theta_1_;\n", "", qasm_str)
qasm_str = qasm_str.replace("_theta_0_", str(gamma))
qasm_str = qasm_str.replace("_theta_1_", str(beta))

qc = qasm3.loads(qasm_str)
print(qc.draw(output='text', fold=-1))
