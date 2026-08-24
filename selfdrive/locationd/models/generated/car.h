#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_6365619221141532795);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6783137646475149206);
void car_H_mod_fun(double *state, double *out_6526450026318439938);
void car_f_fun(double *state, double dt, double *out_4272954226105081029);
void car_F_fun(double *state, double dt, double *out_6970595147060431095);
void car_h_25(double *state, double *unused, double *out_6651248986441369956);
void car_H_25(double *state, double *unused, double *out_429541659712065322);
void car_h_24(double *state, double *unused, double *out_6146750454880001026);
void car_H_24(double *state, double *unused, double *out_1743107939293434244);
void car_h_30(double *state, double *unused, double *out_809309777807518369);
void car_H_30(double *state, double *unused, double *out_2947874618219313949);
void car_h_26(double *state, double *unused, double *out_1795095543001179282);
void car_H_26(double *state, double *unused, double *out_3734067629472865923);
void car_h_27(double *state, double *unused, double *out_6793821819607336015);
void car_H_27(double *state, double *unused, double *out_5171468689403257166);
void car_h_29(double *state, double *unused, double *out_205993893131040852);
void car_H_29(double *state, double *unused, double *out_3458105962533706133);
void car_h_28(double *state, double *unused, double *out_7737331672508998450);
void car_H_28(double *state, double *unused, double *out_1624293054535824441);
void car_h_31(double *state, double *unused, double *out_3013799458187347606);
void car_H_31(double *state, double *unused, double *out_3107859527239514447);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}