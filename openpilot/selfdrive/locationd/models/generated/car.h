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
void car_err_fun(double *nom_x, double *delta_x, double *out_3577027747959260781);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3860135801588453216);
void car_H_mod_fun(double *state, double *out_5362338058005053771);
void car_f_fun(double *state, double dt, double *out_2926665251834366623);
void car_F_fun(double *state, double dt, double *out_3050739536388542838);
void car_h_25(double *state, double *unused, double *out_6655556506237939461);
void car_H_25(double *state, double *unused, double *out_7643676794856990554);
void car_h_24(double *state, double *unused, double *out_4270017605603811542);
void car_H_24(double *state, double *unused, double *out_8577359494873692500);
void car_h_30(double *state, double *unused, double *out_6812743174589068606);
void car_H_30(double *state, double *unused, double *out_3886376937360944307);
void car_h_26(double *state, double *unused, double *out_398166311665152905);
void car_H_26(double *state, double *unused, double *out_3902173475982934330);
void car_h_27(double *state, double *unused, double *out_1653883238577093816);
void car_H_27(double *state, double *unused, double *out_6061140249161369218);
void car_h_29(double *state, double *unused, double *out_1983566289676928534);
void car_H_29(double *state, double *unused, double *out_3376145593046552123);
void car_h_28(double *state, double *unused, double *out_7810891663125617035);
void car_H_28(double *state, double *unused, double *out_8458544610116082697);
void car_h_31(double *state, double *unused, double *out_5203359640995316992);
void car_H_31(double *state, double *unused, double *out_7674322756733950982);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}