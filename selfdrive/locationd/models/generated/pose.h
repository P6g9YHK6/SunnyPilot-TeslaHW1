#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_208995533761529617);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5913231907866039975);
void pose_H_mod_fun(double *state, double *out_8938143914427276213);
void pose_f_fun(double *state, double dt, double *out_6822525905221779246);
void pose_F_fun(double *state, double dt, double *out_5615665915161385624);
void pose_h_4(double *state, double *unused, double *out_127652883904790585);
void pose_H_4(double *state, double *unused, double *out_6234378080491326150);
void pose_h_10(double *state, double *unused, double *out_8738502854513622739);
void pose_H_10(double *state, double *unused, double *out_8210870549941027059);
void pose_h_13(double *state, double *unused, double *out_4878353631523312513);
void pose_H_13(double *state, double *unused, double *out_9000092167885892665);
void pose_h_14(double *state, double *unused, double *out_3045142269729245966);
void pose_H_14(double *state, double *unused, double *out_8249125136878740937);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}