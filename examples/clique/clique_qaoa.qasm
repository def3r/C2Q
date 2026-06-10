OPENQASM 3.0;
include "stdgates.inc";
input float[64] _theta_0_;
input float[64] _theta_1_;
gate rzz(p0) _gate_q_0, _gate_q_1 {
  cx _gate_q_0, _gate_q_1;
  rz(p0) _gate_q_1;
  cx _gate_q_0, _gate_q_1;
}
gate r(p0, p1) _gate_q_0 {
  u3(p0, p1 - pi/2, pi/2 - p1) _gate_q_0;
}
bit[4] meas;
qubit[4] q;
u2(0, pi) q[0];
u2(0, pi) q[1];
u2(0, pi) q[2];
u2(0, pi) q[3];
barrier q[0], q[1], q[2], q[3];
rz(27.5*_theta_0_) q[3];
rzz(12.5*_theta_0_) q[2], q[3];
rzz(12.5*_theta_0_) q[1], q[3];
rzz(12.5*_theta_0_) q[0], q[3];
rz(27.5*_theta_0_) q[2];
rzz(12.5*_theta_0_) q[1], q[2];
rzz(12.5*_theta_0_) q[0], q[2];
rz(27.5*_theta_0_) q[1];
rzz(12.5*_theta_0_) q[0], q[1];
rz(27.5*_theta_0_) q[0];
barrier q[0], q[1], q[2], q[3];
r(2*_theta_1_, 0) q[0];
r(2*_theta_1_, 0) q[1];
r(2*_theta_1_, 0) q[2];
r(2*_theta_1_, 0) q[3];
barrier q[0], q[1], q[2], q[3];
meas[0] = measure q[0];
meas[1] = measure q[1];
meas[2] = measure q[2];
meas[3] = measure q[3];
