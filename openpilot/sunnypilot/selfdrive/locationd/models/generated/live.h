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
void live_H(double *in_vec, double *out_864957111876489384);
void live_err_fun(double *nom_x, double *delta_x, double *out_2156391055302009084);
void live_inv_err_fun(double *nom_x, double *true_x, double *out_2366600283620487076);
void live_H_mod_fun(double *state, double *out_2726745954246492569);
void live_f_fun(double *state, double dt, double *out_5796288261586595925);
void live_F_fun(double *state, double dt, double *out_1499115455432324064);
void live_h_4(double *state, double *unused, double *out_6722557097389631218);
void live_H_4(double *state, double *unused, double *out_7866766380055337928);
void live_h_9(double *state, double *unused, double *out_3928031354920851994);
void live_H_9(double *state, double *unused, double *out_579547444790890458);
void live_h_10(double *state, double *unused, double *out_4331898301268905940);
void live_H_10(double *state, double *unused, double *out_6846937498605480163);
void live_h_12(double *state, double *unused, double *out_2665882836434391735);
void live_H_12(double *state, double *unused, double *out_2847309972023376133);
void live_h_35(double *state, double *unused, double *out_7244484114866105057);
void live_H_35(double *state, double *unused, double *out_101746939698362424);
void live_h_32(double *state, double *unused, double *out_2695690764271339610);
void live_H_32(double *state, double *unused, double *out_3127297624604435189);
void live_h_13(double *state, double *unused, double *out_3077112608455320788);
void live_H_13(double *state, double *unused, double *out_7352795914662114757);
void live_h_14(double *state, double *unused, double *out_3928031354920851994);
void live_H_14(double *state, double *unused, double *out_579547444790890458);
void live_h_33(double *state, double *unused, double *out_3966452940137280554);
void live_H_33(double *state, double *unused, double *out_3048810064940495180);
void live_predict(double *in_x, double *in_P, double *in_Q, double dt);
}