#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void live_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_9(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_12(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_35(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_32(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_33(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_H(double *in_vec, double *out_2593343145205020541);
void live_err_fun(double *nom_x, double *delta_x, double *out_7504120204062332182);
void live_inv_err_fun(double *nom_x, double *true_x, double *out_799584965649553580);
void live_H_mod_fun(double *state, double *out_2987753237005163188);
void live_f_fun(double *state, double dt, double *out_4104939217975999522);
void live_F_fun(double *state, double dt, double *out_4234435984206919276);
void live_h_4(double *state, double *unused, double *out_7375245092911737973);
void live_H_4(double *state, double *unused, double *out_3097336837876051277);
void live_h_9(double *state, double *unused, double *out_3311059932937072956);
void live_H_9(double *state, double *unused, double *out_4189882097388396193);
void live_h_10(double *state, double *unused, double *out_7083887690215279968);
void live_H_10(double *state, double *unused, double *out_8650940723781484287);
void live_h_12(double *state, double *unused, double *out_3040065669884163812);
void live_H_12(double *state, double *unused, double *out_8968148858790767343);
void live_h_35(double *state, double *unused, double *out_3189941471514975756);
void live_H_35(double *state, double *unused, double *out_269325219496556099);
void live_h_32(double *state, double *unused, double *out_537375349993052601);
void live_H_32(double *state, double *unused, double *out_400490004437296568);
void live_h_13(double *state, double *unused, double *out_1029927715484265184);
void live_H_13(double *state, double *unused, double *out_2331632424501202539);
void live_h_14(double *state, double *unused, double *out_3311059932937072956);
void live_H_14(double *state, double *unused, double *out_4189882097388396193);
void live_h_33(double *state, double *unused, double *out_8707570340604437159);
void live_H_33(double *state, double *unused, double *out_7980832560939281088);
void live_predict(double *in_x, double *in_P, double *in_Q, double dt);
}