#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_6365619221141532795) {
   out_6365619221141532795[0] = delta_x[0] + nom_x[0];
   out_6365619221141532795[1] = delta_x[1] + nom_x[1];
   out_6365619221141532795[2] = delta_x[2] + nom_x[2];
   out_6365619221141532795[3] = delta_x[3] + nom_x[3];
   out_6365619221141532795[4] = delta_x[4] + nom_x[4];
   out_6365619221141532795[5] = delta_x[5] + nom_x[5];
   out_6365619221141532795[6] = delta_x[6] + nom_x[6];
   out_6365619221141532795[7] = delta_x[7] + nom_x[7];
   out_6365619221141532795[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6783137646475149206) {
   out_6783137646475149206[0] = -nom_x[0] + true_x[0];
   out_6783137646475149206[1] = -nom_x[1] + true_x[1];
   out_6783137646475149206[2] = -nom_x[2] + true_x[2];
   out_6783137646475149206[3] = -nom_x[3] + true_x[3];
   out_6783137646475149206[4] = -nom_x[4] + true_x[4];
   out_6783137646475149206[5] = -nom_x[5] + true_x[5];
   out_6783137646475149206[6] = -nom_x[6] + true_x[6];
   out_6783137646475149206[7] = -nom_x[7] + true_x[7];
   out_6783137646475149206[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6526450026318439938) {
   out_6526450026318439938[0] = 1.0;
   out_6526450026318439938[1] = 0.0;
   out_6526450026318439938[2] = 0.0;
   out_6526450026318439938[3] = 0.0;
   out_6526450026318439938[4] = 0.0;
   out_6526450026318439938[5] = 0.0;
   out_6526450026318439938[6] = 0.0;
   out_6526450026318439938[7] = 0.0;
   out_6526450026318439938[8] = 0.0;
   out_6526450026318439938[9] = 0.0;
   out_6526450026318439938[10] = 1.0;
   out_6526450026318439938[11] = 0.0;
   out_6526450026318439938[12] = 0.0;
   out_6526450026318439938[13] = 0.0;
   out_6526450026318439938[14] = 0.0;
   out_6526450026318439938[15] = 0.0;
   out_6526450026318439938[16] = 0.0;
   out_6526450026318439938[17] = 0.0;
   out_6526450026318439938[18] = 0.0;
   out_6526450026318439938[19] = 0.0;
   out_6526450026318439938[20] = 1.0;
   out_6526450026318439938[21] = 0.0;
   out_6526450026318439938[22] = 0.0;
   out_6526450026318439938[23] = 0.0;
   out_6526450026318439938[24] = 0.0;
   out_6526450026318439938[25] = 0.0;
   out_6526450026318439938[26] = 0.0;
   out_6526450026318439938[27] = 0.0;
   out_6526450026318439938[28] = 0.0;
   out_6526450026318439938[29] = 0.0;
   out_6526450026318439938[30] = 1.0;
   out_6526450026318439938[31] = 0.0;
   out_6526450026318439938[32] = 0.0;
   out_6526450026318439938[33] = 0.0;
   out_6526450026318439938[34] = 0.0;
   out_6526450026318439938[35] = 0.0;
   out_6526450026318439938[36] = 0.0;
   out_6526450026318439938[37] = 0.0;
   out_6526450026318439938[38] = 0.0;
   out_6526450026318439938[39] = 0.0;
   out_6526450026318439938[40] = 1.0;
   out_6526450026318439938[41] = 0.0;
   out_6526450026318439938[42] = 0.0;
   out_6526450026318439938[43] = 0.0;
   out_6526450026318439938[44] = 0.0;
   out_6526450026318439938[45] = 0.0;
   out_6526450026318439938[46] = 0.0;
   out_6526450026318439938[47] = 0.0;
   out_6526450026318439938[48] = 0.0;
   out_6526450026318439938[49] = 0.0;
   out_6526450026318439938[50] = 1.0;
   out_6526450026318439938[51] = 0.0;
   out_6526450026318439938[52] = 0.0;
   out_6526450026318439938[53] = 0.0;
   out_6526450026318439938[54] = 0.0;
   out_6526450026318439938[55] = 0.0;
   out_6526450026318439938[56] = 0.0;
   out_6526450026318439938[57] = 0.0;
   out_6526450026318439938[58] = 0.0;
   out_6526450026318439938[59] = 0.0;
   out_6526450026318439938[60] = 1.0;
   out_6526450026318439938[61] = 0.0;
   out_6526450026318439938[62] = 0.0;
   out_6526450026318439938[63] = 0.0;
   out_6526450026318439938[64] = 0.0;
   out_6526450026318439938[65] = 0.0;
   out_6526450026318439938[66] = 0.0;
   out_6526450026318439938[67] = 0.0;
   out_6526450026318439938[68] = 0.0;
   out_6526450026318439938[69] = 0.0;
   out_6526450026318439938[70] = 1.0;
   out_6526450026318439938[71] = 0.0;
   out_6526450026318439938[72] = 0.0;
   out_6526450026318439938[73] = 0.0;
   out_6526450026318439938[74] = 0.0;
   out_6526450026318439938[75] = 0.0;
   out_6526450026318439938[76] = 0.0;
   out_6526450026318439938[77] = 0.0;
   out_6526450026318439938[78] = 0.0;
   out_6526450026318439938[79] = 0.0;
   out_6526450026318439938[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_4272954226105081029) {
   out_4272954226105081029[0] = state[0];
   out_4272954226105081029[1] = state[1];
   out_4272954226105081029[2] = state[2];
   out_4272954226105081029[3] = state[3];
   out_4272954226105081029[4] = state[4];
   out_4272954226105081029[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_4272954226105081029[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_4272954226105081029[7] = state[7];
   out_4272954226105081029[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6970595147060431095) {
   out_6970595147060431095[0] = 1;
   out_6970595147060431095[1] = 0;
   out_6970595147060431095[2] = 0;
   out_6970595147060431095[3] = 0;
   out_6970595147060431095[4] = 0;
   out_6970595147060431095[5] = 0;
   out_6970595147060431095[6] = 0;
   out_6970595147060431095[7] = 0;
   out_6970595147060431095[8] = 0;
   out_6970595147060431095[9] = 0;
   out_6970595147060431095[10] = 1;
   out_6970595147060431095[11] = 0;
   out_6970595147060431095[12] = 0;
   out_6970595147060431095[13] = 0;
   out_6970595147060431095[14] = 0;
   out_6970595147060431095[15] = 0;
   out_6970595147060431095[16] = 0;
   out_6970595147060431095[17] = 0;
   out_6970595147060431095[18] = 0;
   out_6970595147060431095[19] = 0;
   out_6970595147060431095[20] = 1;
   out_6970595147060431095[21] = 0;
   out_6970595147060431095[22] = 0;
   out_6970595147060431095[23] = 0;
   out_6970595147060431095[24] = 0;
   out_6970595147060431095[25] = 0;
   out_6970595147060431095[26] = 0;
   out_6970595147060431095[27] = 0;
   out_6970595147060431095[28] = 0;
   out_6970595147060431095[29] = 0;
   out_6970595147060431095[30] = 1;
   out_6970595147060431095[31] = 0;
   out_6970595147060431095[32] = 0;
   out_6970595147060431095[33] = 0;
   out_6970595147060431095[34] = 0;
   out_6970595147060431095[35] = 0;
   out_6970595147060431095[36] = 0;
   out_6970595147060431095[37] = 0;
   out_6970595147060431095[38] = 0;
   out_6970595147060431095[39] = 0;
   out_6970595147060431095[40] = 1;
   out_6970595147060431095[41] = 0;
   out_6970595147060431095[42] = 0;
   out_6970595147060431095[43] = 0;
   out_6970595147060431095[44] = 0;
   out_6970595147060431095[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6970595147060431095[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6970595147060431095[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6970595147060431095[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6970595147060431095[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6970595147060431095[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6970595147060431095[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6970595147060431095[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6970595147060431095[53] = -9.8100000000000005*dt;
   out_6970595147060431095[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6970595147060431095[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6970595147060431095[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6970595147060431095[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6970595147060431095[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6970595147060431095[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6970595147060431095[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6970595147060431095[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6970595147060431095[62] = 0;
   out_6970595147060431095[63] = 0;
   out_6970595147060431095[64] = 0;
   out_6970595147060431095[65] = 0;
   out_6970595147060431095[66] = 0;
   out_6970595147060431095[67] = 0;
   out_6970595147060431095[68] = 0;
   out_6970595147060431095[69] = 0;
   out_6970595147060431095[70] = 1;
   out_6970595147060431095[71] = 0;
   out_6970595147060431095[72] = 0;
   out_6970595147060431095[73] = 0;
   out_6970595147060431095[74] = 0;
   out_6970595147060431095[75] = 0;
   out_6970595147060431095[76] = 0;
   out_6970595147060431095[77] = 0;
   out_6970595147060431095[78] = 0;
   out_6970595147060431095[79] = 0;
   out_6970595147060431095[80] = 1;
}
void h_25(double *state, double *unused, double *out_6651248986441369956) {
   out_6651248986441369956[0] = state[6];
}
void H_25(double *state, double *unused, double *out_429541659712065322) {
   out_429541659712065322[0] = 0;
   out_429541659712065322[1] = 0;
   out_429541659712065322[2] = 0;
   out_429541659712065322[3] = 0;
   out_429541659712065322[4] = 0;
   out_429541659712065322[5] = 0;
   out_429541659712065322[6] = 1;
   out_429541659712065322[7] = 0;
   out_429541659712065322[8] = 0;
}
void h_24(double *state, double *unused, double *out_6146750454880001026) {
   out_6146750454880001026[0] = state[4];
   out_6146750454880001026[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1743107939293434244) {
   out_1743107939293434244[0] = 0;
   out_1743107939293434244[1] = 0;
   out_1743107939293434244[2] = 0;
   out_1743107939293434244[3] = 0;
   out_1743107939293434244[4] = 1;
   out_1743107939293434244[5] = 0;
   out_1743107939293434244[6] = 0;
   out_1743107939293434244[7] = 0;
   out_1743107939293434244[8] = 0;
   out_1743107939293434244[9] = 0;
   out_1743107939293434244[10] = 0;
   out_1743107939293434244[11] = 0;
   out_1743107939293434244[12] = 0;
   out_1743107939293434244[13] = 0;
   out_1743107939293434244[14] = 1;
   out_1743107939293434244[15] = 0;
   out_1743107939293434244[16] = 0;
   out_1743107939293434244[17] = 0;
}
void h_30(double *state, double *unused, double *out_809309777807518369) {
   out_809309777807518369[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2947874618219313949) {
   out_2947874618219313949[0] = 0;
   out_2947874618219313949[1] = 0;
   out_2947874618219313949[2] = 0;
   out_2947874618219313949[3] = 0;
   out_2947874618219313949[4] = 1;
   out_2947874618219313949[5] = 0;
   out_2947874618219313949[6] = 0;
   out_2947874618219313949[7] = 0;
   out_2947874618219313949[8] = 0;
}
void h_26(double *state, double *unused, double *out_1795095543001179282) {
   out_1795095543001179282[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3734067629472865923) {
   out_3734067629472865923[0] = 0;
   out_3734067629472865923[1] = 0;
   out_3734067629472865923[2] = 0;
   out_3734067629472865923[3] = 0;
   out_3734067629472865923[4] = 0;
   out_3734067629472865923[5] = 0;
   out_3734067629472865923[6] = 0;
   out_3734067629472865923[7] = 1;
   out_3734067629472865923[8] = 0;
}
void h_27(double *state, double *unused, double *out_6793821819607336015) {
   out_6793821819607336015[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5171468689403257166) {
   out_5171468689403257166[0] = 0;
   out_5171468689403257166[1] = 0;
   out_5171468689403257166[2] = 0;
   out_5171468689403257166[3] = 1;
   out_5171468689403257166[4] = 0;
   out_5171468689403257166[5] = 0;
   out_5171468689403257166[6] = 0;
   out_5171468689403257166[7] = 0;
   out_5171468689403257166[8] = 0;
}
void h_29(double *state, double *unused, double *out_205993893131040852) {
   out_205993893131040852[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3458105962533706133) {
   out_3458105962533706133[0] = 0;
   out_3458105962533706133[1] = 1;
   out_3458105962533706133[2] = 0;
   out_3458105962533706133[3] = 0;
   out_3458105962533706133[4] = 0;
   out_3458105962533706133[5] = 0;
   out_3458105962533706133[6] = 0;
   out_3458105962533706133[7] = 0;
   out_3458105962533706133[8] = 0;
}
void h_28(double *state, double *unused, double *out_7737331672508998450) {
   out_7737331672508998450[0] = state[0];
}
void H_28(double *state, double *unused, double *out_1624293054535824441) {
   out_1624293054535824441[0] = 1;
   out_1624293054535824441[1] = 0;
   out_1624293054535824441[2] = 0;
   out_1624293054535824441[3] = 0;
   out_1624293054535824441[4] = 0;
   out_1624293054535824441[5] = 0;
   out_1624293054535824441[6] = 0;
   out_1624293054535824441[7] = 0;
   out_1624293054535824441[8] = 0;
}
void h_31(double *state, double *unused, double *out_3013799458187347606) {
   out_3013799458187347606[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3107859527239514447) {
   out_3107859527239514447[0] = 0;
   out_3107859527239514447[1] = 0;
   out_3107859527239514447[2] = 0;
   out_3107859527239514447[3] = 0;
   out_3107859527239514447[4] = 0;
   out_3107859527239514447[5] = 0;
   out_3107859527239514447[6] = 0;
   out_3107859527239514447[7] = 0;
   out_3107859527239514447[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_6365619221141532795) {
  err_fun(nom_x, delta_x, out_6365619221141532795);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6783137646475149206) {
  inv_err_fun(nom_x, true_x, out_6783137646475149206);
}
void car_H_mod_fun(double *state, double *out_6526450026318439938) {
  H_mod_fun(state, out_6526450026318439938);
}
void car_f_fun(double *state, double dt, double *out_4272954226105081029) {
  f_fun(state,  dt, out_4272954226105081029);
}
void car_F_fun(double *state, double dt, double *out_6970595147060431095) {
  F_fun(state,  dt, out_6970595147060431095);
}
void car_h_25(double *state, double *unused, double *out_6651248986441369956) {
  h_25(state, unused, out_6651248986441369956);
}
void car_H_25(double *state, double *unused, double *out_429541659712065322) {
  H_25(state, unused, out_429541659712065322);
}
void car_h_24(double *state, double *unused, double *out_6146750454880001026) {
  h_24(state, unused, out_6146750454880001026);
}
void car_H_24(double *state, double *unused, double *out_1743107939293434244) {
  H_24(state, unused, out_1743107939293434244);
}
void car_h_30(double *state, double *unused, double *out_809309777807518369) {
  h_30(state, unused, out_809309777807518369);
}
void car_H_30(double *state, double *unused, double *out_2947874618219313949) {
  H_30(state, unused, out_2947874618219313949);
}
void car_h_26(double *state, double *unused, double *out_1795095543001179282) {
  h_26(state, unused, out_1795095543001179282);
}
void car_H_26(double *state, double *unused, double *out_3734067629472865923) {
  H_26(state, unused, out_3734067629472865923);
}
void car_h_27(double *state, double *unused, double *out_6793821819607336015) {
  h_27(state, unused, out_6793821819607336015);
}
void car_H_27(double *state, double *unused, double *out_5171468689403257166) {
  H_27(state, unused, out_5171468689403257166);
}
void car_h_29(double *state, double *unused, double *out_205993893131040852) {
  h_29(state, unused, out_205993893131040852);
}
void car_H_29(double *state, double *unused, double *out_3458105962533706133) {
  H_29(state, unused, out_3458105962533706133);
}
void car_h_28(double *state, double *unused, double *out_7737331672508998450) {
  h_28(state, unused, out_7737331672508998450);
}
void car_H_28(double *state, double *unused, double *out_1624293054535824441) {
  H_28(state, unused, out_1624293054535824441);
}
void car_h_31(double *state, double *unused, double *out_3013799458187347606) {
  h_31(state, unused, out_3013799458187347606);
}
void car_H_31(double *state, double *unused, double *out_3107859527239514447) {
  H_31(state, unused, out_3107859527239514447);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
