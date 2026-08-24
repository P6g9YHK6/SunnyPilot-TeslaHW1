#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_208995533761529617) {
   out_208995533761529617[0] = delta_x[0] + nom_x[0];
   out_208995533761529617[1] = delta_x[1] + nom_x[1];
   out_208995533761529617[2] = delta_x[2] + nom_x[2];
   out_208995533761529617[3] = delta_x[3] + nom_x[3];
   out_208995533761529617[4] = delta_x[4] + nom_x[4];
   out_208995533761529617[5] = delta_x[5] + nom_x[5];
   out_208995533761529617[6] = delta_x[6] + nom_x[6];
   out_208995533761529617[7] = delta_x[7] + nom_x[7];
   out_208995533761529617[8] = delta_x[8] + nom_x[8];
   out_208995533761529617[9] = delta_x[9] + nom_x[9];
   out_208995533761529617[10] = delta_x[10] + nom_x[10];
   out_208995533761529617[11] = delta_x[11] + nom_x[11];
   out_208995533761529617[12] = delta_x[12] + nom_x[12];
   out_208995533761529617[13] = delta_x[13] + nom_x[13];
   out_208995533761529617[14] = delta_x[14] + nom_x[14];
   out_208995533761529617[15] = delta_x[15] + nom_x[15];
   out_208995533761529617[16] = delta_x[16] + nom_x[16];
   out_208995533761529617[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5913231907866039975) {
   out_5913231907866039975[0] = -nom_x[0] + true_x[0];
   out_5913231907866039975[1] = -nom_x[1] + true_x[1];
   out_5913231907866039975[2] = -nom_x[2] + true_x[2];
   out_5913231907866039975[3] = -nom_x[3] + true_x[3];
   out_5913231907866039975[4] = -nom_x[4] + true_x[4];
   out_5913231907866039975[5] = -nom_x[5] + true_x[5];
   out_5913231907866039975[6] = -nom_x[6] + true_x[6];
   out_5913231907866039975[7] = -nom_x[7] + true_x[7];
   out_5913231907866039975[8] = -nom_x[8] + true_x[8];
   out_5913231907866039975[9] = -nom_x[9] + true_x[9];
   out_5913231907866039975[10] = -nom_x[10] + true_x[10];
   out_5913231907866039975[11] = -nom_x[11] + true_x[11];
   out_5913231907866039975[12] = -nom_x[12] + true_x[12];
   out_5913231907866039975[13] = -nom_x[13] + true_x[13];
   out_5913231907866039975[14] = -nom_x[14] + true_x[14];
   out_5913231907866039975[15] = -nom_x[15] + true_x[15];
   out_5913231907866039975[16] = -nom_x[16] + true_x[16];
   out_5913231907866039975[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8938143914427276213) {
   out_8938143914427276213[0] = 1.0;
   out_8938143914427276213[1] = 0.0;
   out_8938143914427276213[2] = 0.0;
   out_8938143914427276213[3] = 0.0;
   out_8938143914427276213[4] = 0.0;
   out_8938143914427276213[5] = 0.0;
   out_8938143914427276213[6] = 0.0;
   out_8938143914427276213[7] = 0.0;
   out_8938143914427276213[8] = 0.0;
   out_8938143914427276213[9] = 0.0;
   out_8938143914427276213[10] = 0.0;
   out_8938143914427276213[11] = 0.0;
   out_8938143914427276213[12] = 0.0;
   out_8938143914427276213[13] = 0.0;
   out_8938143914427276213[14] = 0.0;
   out_8938143914427276213[15] = 0.0;
   out_8938143914427276213[16] = 0.0;
   out_8938143914427276213[17] = 0.0;
   out_8938143914427276213[18] = 0.0;
   out_8938143914427276213[19] = 1.0;
   out_8938143914427276213[20] = 0.0;
   out_8938143914427276213[21] = 0.0;
   out_8938143914427276213[22] = 0.0;
   out_8938143914427276213[23] = 0.0;
   out_8938143914427276213[24] = 0.0;
   out_8938143914427276213[25] = 0.0;
   out_8938143914427276213[26] = 0.0;
   out_8938143914427276213[27] = 0.0;
   out_8938143914427276213[28] = 0.0;
   out_8938143914427276213[29] = 0.0;
   out_8938143914427276213[30] = 0.0;
   out_8938143914427276213[31] = 0.0;
   out_8938143914427276213[32] = 0.0;
   out_8938143914427276213[33] = 0.0;
   out_8938143914427276213[34] = 0.0;
   out_8938143914427276213[35] = 0.0;
   out_8938143914427276213[36] = 0.0;
   out_8938143914427276213[37] = 0.0;
   out_8938143914427276213[38] = 1.0;
   out_8938143914427276213[39] = 0.0;
   out_8938143914427276213[40] = 0.0;
   out_8938143914427276213[41] = 0.0;
   out_8938143914427276213[42] = 0.0;
   out_8938143914427276213[43] = 0.0;
   out_8938143914427276213[44] = 0.0;
   out_8938143914427276213[45] = 0.0;
   out_8938143914427276213[46] = 0.0;
   out_8938143914427276213[47] = 0.0;
   out_8938143914427276213[48] = 0.0;
   out_8938143914427276213[49] = 0.0;
   out_8938143914427276213[50] = 0.0;
   out_8938143914427276213[51] = 0.0;
   out_8938143914427276213[52] = 0.0;
   out_8938143914427276213[53] = 0.0;
   out_8938143914427276213[54] = 0.0;
   out_8938143914427276213[55] = 0.0;
   out_8938143914427276213[56] = 0.0;
   out_8938143914427276213[57] = 1.0;
   out_8938143914427276213[58] = 0.0;
   out_8938143914427276213[59] = 0.0;
   out_8938143914427276213[60] = 0.0;
   out_8938143914427276213[61] = 0.0;
   out_8938143914427276213[62] = 0.0;
   out_8938143914427276213[63] = 0.0;
   out_8938143914427276213[64] = 0.0;
   out_8938143914427276213[65] = 0.0;
   out_8938143914427276213[66] = 0.0;
   out_8938143914427276213[67] = 0.0;
   out_8938143914427276213[68] = 0.0;
   out_8938143914427276213[69] = 0.0;
   out_8938143914427276213[70] = 0.0;
   out_8938143914427276213[71] = 0.0;
   out_8938143914427276213[72] = 0.0;
   out_8938143914427276213[73] = 0.0;
   out_8938143914427276213[74] = 0.0;
   out_8938143914427276213[75] = 0.0;
   out_8938143914427276213[76] = 1.0;
   out_8938143914427276213[77] = 0.0;
   out_8938143914427276213[78] = 0.0;
   out_8938143914427276213[79] = 0.0;
   out_8938143914427276213[80] = 0.0;
   out_8938143914427276213[81] = 0.0;
   out_8938143914427276213[82] = 0.0;
   out_8938143914427276213[83] = 0.0;
   out_8938143914427276213[84] = 0.0;
   out_8938143914427276213[85] = 0.0;
   out_8938143914427276213[86] = 0.0;
   out_8938143914427276213[87] = 0.0;
   out_8938143914427276213[88] = 0.0;
   out_8938143914427276213[89] = 0.0;
   out_8938143914427276213[90] = 0.0;
   out_8938143914427276213[91] = 0.0;
   out_8938143914427276213[92] = 0.0;
   out_8938143914427276213[93] = 0.0;
   out_8938143914427276213[94] = 0.0;
   out_8938143914427276213[95] = 1.0;
   out_8938143914427276213[96] = 0.0;
   out_8938143914427276213[97] = 0.0;
   out_8938143914427276213[98] = 0.0;
   out_8938143914427276213[99] = 0.0;
   out_8938143914427276213[100] = 0.0;
   out_8938143914427276213[101] = 0.0;
   out_8938143914427276213[102] = 0.0;
   out_8938143914427276213[103] = 0.0;
   out_8938143914427276213[104] = 0.0;
   out_8938143914427276213[105] = 0.0;
   out_8938143914427276213[106] = 0.0;
   out_8938143914427276213[107] = 0.0;
   out_8938143914427276213[108] = 0.0;
   out_8938143914427276213[109] = 0.0;
   out_8938143914427276213[110] = 0.0;
   out_8938143914427276213[111] = 0.0;
   out_8938143914427276213[112] = 0.0;
   out_8938143914427276213[113] = 0.0;
   out_8938143914427276213[114] = 1.0;
   out_8938143914427276213[115] = 0.0;
   out_8938143914427276213[116] = 0.0;
   out_8938143914427276213[117] = 0.0;
   out_8938143914427276213[118] = 0.0;
   out_8938143914427276213[119] = 0.0;
   out_8938143914427276213[120] = 0.0;
   out_8938143914427276213[121] = 0.0;
   out_8938143914427276213[122] = 0.0;
   out_8938143914427276213[123] = 0.0;
   out_8938143914427276213[124] = 0.0;
   out_8938143914427276213[125] = 0.0;
   out_8938143914427276213[126] = 0.0;
   out_8938143914427276213[127] = 0.0;
   out_8938143914427276213[128] = 0.0;
   out_8938143914427276213[129] = 0.0;
   out_8938143914427276213[130] = 0.0;
   out_8938143914427276213[131] = 0.0;
   out_8938143914427276213[132] = 0.0;
   out_8938143914427276213[133] = 1.0;
   out_8938143914427276213[134] = 0.0;
   out_8938143914427276213[135] = 0.0;
   out_8938143914427276213[136] = 0.0;
   out_8938143914427276213[137] = 0.0;
   out_8938143914427276213[138] = 0.0;
   out_8938143914427276213[139] = 0.0;
   out_8938143914427276213[140] = 0.0;
   out_8938143914427276213[141] = 0.0;
   out_8938143914427276213[142] = 0.0;
   out_8938143914427276213[143] = 0.0;
   out_8938143914427276213[144] = 0.0;
   out_8938143914427276213[145] = 0.0;
   out_8938143914427276213[146] = 0.0;
   out_8938143914427276213[147] = 0.0;
   out_8938143914427276213[148] = 0.0;
   out_8938143914427276213[149] = 0.0;
   out_8938143914427276213[150] = 0.0;
   out_8938143914427276213[151] = 0.0;
   out_8938143914427276213[152] = 1.0;
   out_8938143914427276213[153] = 0.0;
   out_8938143914427276213[154] = 0.0;
   out_8938143914427276213[155] = 0.0;
   out_8938143914427276213[156] = 0.0;
   out_8938143914427276213[157] = 0.0;
   out_8938143914427276213[158] = 0.0;
   out_8938143914427276213[159] = 0.0;
   out_8938143914427276213[160] = 0.0;
   out_8938143914427276213[161] = 0.0;
   out_8938143914427276213[162] = 0.0;
   out_8938143914427276213[163] = 0.0;
   out_8938143914427276213[164] = 0.0;
   out_8938143914427276213[165] = 0.0;
   out_8938143914427276213[166] = 0.0;
   out_8938143914427276213[167] = 0.0;
   out_8938143914427276213[168] = 0.0;
   out_8938143914427276213[169] = 0.0;
   out_8938143914427276213[170] = 0.0;
   out_8938143914427276213[171] = 1.0;
   out_8938143914427276213[172] = 0.0;
   out_8938143914427276213[173] = 0.0;
   out_8938143914427276213[174] = 0.0;
   out_8938143914427276213[175] = 0.0;
   out_8938143914427276213[176] = 0.0;
   out_8938143914427276213[177] = 0.0;
   out_8938143914427276213[178] = 0.0;
   out_8938143914427276213[179] = 0.0;
   out_8938143914427276213[180] = 0.0;
   out_8938143914427276213[181] = 0.0;
   out_8938143914427276213[182] = 0.0;
   out_8938143914427276213[183] = 0.0;
   out_8938143914427276213[184] = 0.0;
   out_8938143914427276213[185] = 0.0;
   out_8938143914427276213[186] = 0.0;
   out_8938143914427276213[187] = 0.0;
   out_8938143914427276213[188] = 0.0;
   out_8938143914427276213[189] = 0.0;
   out_8938143914427276213[190] = 1.0;
   out_8938143914427276213[191] = 0.0;
   out_8938143914427276213[192] = 0.0;
   out_8938143914427276213[193] = 0.0;
   out_8938143914427276213[194] = 0.0;
   out_8938143914427276213[195] = 0.0;
   out_8938143914427276213[196] = 0.0;
   out_8938143914427276213[197] = 0.0;
   out_8938143914427276213[198] = 0.0;
   out_8938143914427276213[199] = 0.0;
   out_8938143914427276213[200] = 0.0;
   out_8938143914427276213[201] = 0.0;
   out_8938143914427276213[202] = 0.0;
   out_8938143914427276213[203] = 0.0;
   out_8938143914427276213[204] = 0.0;
   out_8938143914427276213[205] = 0.0;
   out_8938143914427276213[206] = 0.0;
   out_8938143914427276213[207] = 0.0;
   out_8938143914427276213[208] = 0.0;
   out_8938143914427276213[209] = 1.0;
   out_8938143914427276213[210] = 0.0;
   out_8938143914427276213[211] = 0.0;
   out_8938143914427276213[212] = 0.0;
   out_8938143914427276213[213] = 0.0;
   out_8938143914427276213[214] = 0.0;
   out_8938143914427276213[215] = 0.0;
   out_8938143914427276213[216] = 0.0;
   out_8938143914427276213[217] = 0.0;
   out_8938143914427276213[218] = 0.0;
   out_8938143914427276213[219] = 0.0;
   out_8938143914427276213[220] = 0.0;
   out_8938143914427276213[221] = 0.0;
   out_8938143914427276213[222] = 0.0;
   out_8938143914427276213[223] = 0.0;
   out_8938143914427276213[224] = 0.0;
   out_8938143914427276213[225] = 0.0;
   out_8938143914427276213[226] = 0.0;
   out_8938143914427276213[227] = 0.0;
   out_8938143914427276213[228] = 1.0;
   out_8938143914427276213[229] = 0.0;
   out_8938143914427276213[230] = 0.0;
   out_8938143914427276213[231] = 0.0;
   out_8938143914427276213[232] = 0.0;
   out_8938143914427276213[233] = 0.0;
   out_8938143914427276213[234] = 0.0;
   out_8938143914427276213[235] = 0.0;
   out_8938143914427276213[236] = 0.0;
   out_8938143914427276213[237] = 0.0;
   out_8938143914427276213[238] = 0.0;
   out_8938143914427276213[239] = 0.0;
   out_8938143914427276213[240] = 0.0;
   out_8938143914427276213[241] = 0.0;
   out_8938143914427276213[242] = 0.0;
   out_8938143914427276213[243] = 0.0;
   out_8938143914427276213[244] = 0.0;
   out_8938143914427276213[245] = 0.0;
   out_8938143914427276213[246] = 0.0;
   out_8938143914427276213[247] = 1.0;
   out_8938143914427276213[248] = 0.0;
   out_8938143914427276213[249] = 0.0;
   out_8938143914427276213[250] = 0.0;
   out_8938143914427276213[251] = 0.0;
   out_8938143914427276213[252] = 0.0;
   out_8938143914427276213[253] = 0.0;
   out_8938143914427276213[254] = 0.0;
   out_8938143914427276213[255] = 0.0;
   out_8938143914427276213[256] = 0.0;
   out_8938143914427276213[257] = 0.0;
   out_8938143914427276213[258] = 0.0;
   out_8938143914427276213[259] = 0.0;
   out_8938143914427276213[260] = 0.0;
   out_8938143914427276213[261] = 0.0;
   out_8938143914427276213[262] = 0.0;
   out_8938143914427276213[263] = 0.0;
   out_8938143914427276213[264] = 0.0;
   out_8938143914427276213[265] = 0.0;
   out_8938143914427276213[266] = 1.0;
   out_8938143914427276213[267] = 0.0;
   out_8938143914427276213[268] = 0.0;
   out_8938143914427276213[269] = 0.0;
   out_8938143914427276213[270] = 0.0;
   out_8938143914427276213[271] = 0.0;
   out_8938143914427276213[272] = 0.0;
   out_8938143914427276213[273] = 0.0;
   out_8938143914427276213[274] = 0.0;
   out_8938143914427276213[275] = 0.0;
   out_8938143914427276213[276] = 0.0;
   out_8938143914427276213[277] = 0.0;
   out_8938143914427276213[278] = 0.0;
   out_8938143914427276213[279] = 0.0;
   out_8938143914427276213[280] = 0.0;
   out_8938143914427276213[281] = 0.0;
   out_8938143914427276213[282] = 0.0;
   out_8938143914427276213[283] = 0.0;
   out_8938143914427276213[284] = 0.0;
   out_8938143914427276213[285] = 1.0;
   out_8938143914427276213[286] = 0.0;
   out_8938143914427276213[287] = 0.0;
   out_8938143914427276213[288] = 0.0;
   out_8938143914427276213[289] = 0.0;
   out_8938143914427276213[290] = 0.0;
   out_8938143914427276213[291] = 0.0;
   out_8938143914427276213[292] = 0.0;
   out_8938143914427276213[293] = 0.0;
   out_8938143914427276213[294] = 0.0;
   out_8938143914427276213[295] = 0.0;
   out_8938143914427276213[296] = 0.0;
   out_8938143914427276213[297] = 0.0;
   out_8938143914427276213[298] = 0.0;
   out_8938143914427276213[299] = 0.0;
   out_8938143914427276213[300] = 0.0;
   out_8938143914427276213[301] = 0.0;
   out_8938143914427276213[302] = 0.0;
   out_8938143914427276213[303] = 0.0;
   out_8938143914427276213[304] = 1.0;
   out_8938143914427276213[305] = 0.0;
   out_8938143914427276213[306] = 0.0;
   out_8938143914427276213[307] = 0.0;
   out_8938143914427276213[308] = 0.0;
   out_8938143914427276213[309] = 0.0;
   out_8938143914427276213[310] = 0.0;
   out_8938143914427276213[311] = 0.0;
   out_8938143914427276213[312] = 0.0;
   out_8938143914427276213[313] = 0.0;
   out_8938143914427276213[314] = 0.0;
   out_8938143914427276213[315] = 0.0;
   out_8938143914427276213[316] = 0.0;
   out_8938143914427276213[317] = 0.0;
   out_8938143914427276213[318] = 0.0;
   out_8938143914427276213[319] = 0.0;
   out_8938143914427276213[320] = 0.0;
   out_8938143914427276213[321] = 0.0;
   out_8938143914427276213[322] = 0.0;
   out_8938143914427276213[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6822525905221779246) {
   out_6822525905221779246[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6822525905221779246[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6822525905221779246[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6822525905221779246[3] = dt*state[12] + state[3];
   out_6822525905221779246[4] = dt*state[13] + state[4];
   out_6822525905221779246[5] = dt*state[14] + state[5];
   out_6822525905221779246[6] = state[6];
   out_6822525905221779246[7] = state[7];
   out_6822525905221779246[8] = state[8];
   out_6822525905221779246[9] = state[9];
   out_6822525905221779246[10] = state[10];
   out_6822525905221779246[11] = state[11];
   out_6822525905221779246[12] = state[12];
   out_6822525905221779246[13] = state[13];
   out_6822525905221779246[14] = state[14];
   out_6822525905221779246[15] = state[15];
   out_6822525905221779246[16] = state[16];
   out_6822525905221779246[17] = state[17];
}
void F_fun(double *state, double dt, double *out_5615665915161385624) {
   out_5615665915161385624[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5615665915161385624[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5615665915161385624[2] = 0;
   out_5615665915161385624[3] = 0;
   out_5615665915161385624[4] = 0;
   out_5615665915161385624[5] = 0;
   out_5615665915161385624[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5615665915161385624[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5615665915161385624[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5615665915161385624[9] = 0;
   out_5615665915161385624[10] = 0;
   out_5615665915161385624[11] = 0;
   out_5615665915161385624[12] = 0;
   out_5615665915161385624[13] = 0;
   out_5615665915161385624[14] = 0;
   out_5615665915161385624[15] = 0;
   out_5615665915161385624[16] = 0;
   out_5615665915161385624[17] = 0;
   out_5615665915161385624[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5615665915161385624[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5615665915161385624[20] = 0;
   out_5615665915161385624[21] = 0;
   out_5615665915161385624[22] = 0;
   out_5615665915161385624[23] = 0;
   out_5615665915161385624[24] = 0;
   out_5615665915161385624[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5615665915161385624[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5615665915161385624[27] = 0;
   out_5615665915161385624[28] = 0;
   out_5615665915161385624[29] = 0;
   out_5615665915161385624[30] = 0;
   out_5615665915161385624[31] = 0;
   out_5615665915161385624[32] = 0;
   out_5615665915161385624[33] = 0;
   out_5615665915161385624[34] = 0;
   out_5615665915161385624[35] = 0;
   out_5615665915161385624[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5615665915161385624[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5615665915161385624[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5615665915161385624[39] = 0;
   out_5615665915161385624[40] = 0;
   out_5615665915161385624[41] = 0;
   out_5615665915161385624[42] = 0;
   out_5615665915161385624[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5615665915161385624[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5615665915161385624[45] = 0;
   out_5615665915161385624[46] = 0;
   out_5615665915161385624[47] = 0;
   out_5615665915161385624[48] = 0;
   out_5615665915161385624[49] = 0;
   out_5615665915161385624[50] = 0;
   out_5615665915161385624[51] = 0;
   out_5615665915161385624[52] = 0;
   out_5615665915161385624[53] = 0;
   out_5615665915161385624[54] = 0;
   out_5615665915161385624[55] = 0;
   out_5615665915161385624[56] = 0;
   out_5615665915161385624[57] = 1;
   out_5615665915161385624[58] = 0;
   out_5615665915161385624[59] = 0;
   out_5615665915161385624[60] = 0;
   out_5615665915161385624[61] = 0;
   out_5615665915161385624[62] = 0;
   out_5615665915161385624[63] = 0;
   out_5615665915161385624[64] = 0;
   out_5615665915161385624[65] = 0;
   out_5615665915161385624[66] = dt;
   out_5615665915161385624[67] = 0;
   out_5615665915161385624[68] = 0;
   out_5615665915161385624[69] = 0;
   out_5615665915161385624[70] = 0;
   out_5615665915161385624[71] = 0;
   out_5615665915161385624[72] = 0;
   out_5615665915161385624[73] = 0;
   out_5615665915161385624[74] = 0;
   out_5615665915161385624[75] = 0;
   out_5615665915161385624[76] = 1;
   out_5615665915161385624[77] = 0;
   out_5615665915161385624[78] = 0;
   out_5615665915161385624[79] = 0;
   out_5615665915161385624[80] = 0;
   out_5615665915161385624[81] = 0;
   out_5615665915161385624[82] = 0;
   out_5615665915161385624[83] = 0;
   out_5615665915161385624[84] = 0;
   out_5615665915161385624[85] = dt;
   out_5615665915161385624[86] = 0;
   out_5615665915161385624[87] = 0;
   out_5615665915161385624[88] = 0;
   out_5615665915161385624[89] = 0;
   out_5615665915161385624[90] = 0;
   out_5615665915161385624[91] = 0;
   out_5615665915161385624[92] = 0;
   out_5615665915161385624[93] = 0;
   out_5615665915161385624[94] = 0;
   out_5615665915161385624[95] = 1;
   out_5615665915161385624[96] = 0;
   out_5615665915161385624[97] = 0;
   out_5615665915161385624[98] = 0;
   out_5615665915161385624[99] = 0;
   out_5615665915161385624[100] = 0;
   out_5615665915161385624[101] = 0;
   out_5615665915161385624[102] = 0;
   out_5615665915161385624[103] = 0;
   out_5615665915161385624[104] = dt;
   out_5615665915161385624[105] = 0;
   out_5615665915161385624[106] = 0;
   out_5615665915161385624[107] = 0;
   out_5615665915161385624[108] = 0;
   out_5615665915161385624[109] = 0;
   out_5615665915161385624[110] = 0;
   out_5615665915161385624[111] = 0;
   out_5615665915161385624[112] = 0;
   out_5615665915161385624[113] = 0;
   out_5615665915161385624[114] = 1;
   out_5615665915161385624[115] = 0;
   out_5615665915161385624[116] = 0;
   out_5615665915161385624[117] = 0;
   out_5615665915161385624[118] = 0;
   out_5615665915161385624[119] = 0;
   out_5615665915161385624[120] = 0;
   out_5615665915161385624[121] = 0;
   out_5615665915161385624[122] = 0;
   out_5615665915161385624[123] = 0;
   out_5615665915161385624[124] = 0;
   out_5615665915161385624[125] = 0;
   out_5615665915161385624[126] = 0;
   out_5615665915161385624[127] = 0;
   out_5615665915161385624[128] = 0;
   out_5615665915161385624[129] = 0;
   out_5615665915161385624[130] = 0;
   out_5615665915161385624[131] = 0;
   out_5615665915161385624[132] = 0;
   out_5615665915161385624[133] = 1;
   out_5615665915161385624[134] = 0;
   out_5615665915161385624[135] = 0;
   out_5615665915161385624[136] = 0;
   out_5615665915161385624[137] = 0;
   out_5615665915161385624[138] = 0;
   out_5615665915161385624[139] = 0;
   out_5615665915161385624[140] = 0;
   out_5615665915161385624[141] = 0;
   out_5615665915161385624[142] = 0;
   out_5615665915161385624[143] = 0;
   out_5615665915161385624[144] = 0;
   out_5615665915161385624[145] = 0;
   out_5615665915161385624[146] = 0;
   out_5615665915161385624[147] = 0;
   out_5615665915161385624[148] = 0;
   out_5615665915161385624[149] = 0;
   out_5615665915161385624[150] = 0;
   out_5615665915161385624[151] = 0;
   out_5615665915161385624[152] = 1;
   out_5615665915161385624[153] = 0;
   out_5615665915161385624[154] = 0;
   out_5615665915161385624[155] = 0;
   out_5615665915161385624[156] = 0;
   out_5615665915161385624[157] = 0;
   out_5615665915161385624[158] = 0;
   out_5615665915161385624[159] = 0;
   out_5615665915161385624[160] = 0;
   out_5615665915161385624[161] = 0;
   out_5615665915161385624[162] = 0;
   out_5615665915161385624[163] = 0;
   out_5615665915161385624[164] = 0;
   out_5615665915161385624[165] = 0;
   out_5615665915161385624[166] = 0;
   out_5615665915161385624[167] = 0;
   out_5615665915161385624[168] = 0;
   out_5615665915161385624[169] = 0;
   out_5615665915161385624[170] = 0;
   out_5615665915161385624[171] = 1;
   out_5615665915161385624[172] = 0;
   out_5615665915161385624[173] = 0;
   out_5615665915161385624[174] = 0;
   out_5615665915161385624[175] = 0;
   out_5615665915161385624[176] = 0;
   out_5615665915161385624[177] = 0;
   out_5615665915161385624[178] = 0;
   out_5615665915161385624[179] = 0;
   out_5615665915161385624[180] = 0;
   out_5615665915161385624[181] = 0;
   out_5615665915161385624[182] = 0;
   out_5615665915161385624[183] = 0;
   out_5615665915161385624[184] = 0;
   out_5615665915161385624[185] = 0;
   out_5615665915161385624[186] = 0;
   out_5615665915161385624[187] = 0;
   out_5615665915161385624[188] = 0;
   out_5615665915161385624[189] = 0;
   out_5615665915161385624[190] = 1;
   out_5615665915161385624[191] = 0;
   out_5615665915161385624[192] = 0;
   out_5615665915161385624[193] = 0;
   out_5615665915161385624[194] = 0;
   out_5615665915161385624[195] = 0;
   out_5615665915161385624[196] = 0;
   out_5615665915161385624[197] = 0;
   out_5615665915161385624[198] = 0;
   out_5615665915161385624[199] = 0;
   out_5615665915161385624[200] = 0;
   out_5615665915161385624[201] = 0;
   out_5615665915161385624[202] = 0;
   out_5615665915161385624[203] = 0;
   out_5615665915161385624[204] = 0;
   out_5615665915161385624[205] = 0;
   out_5615665915161385624[206] = 0;
   out_5615665915161385624[207] = 0;
   out_5615665915161385624[208] = 0;
   out_5615665915161385624[209] = 1;
   out_5615665915161385624[210] = 0;
   out_5615665915161385624[211] = 0;
   out_5615665915161385624[212] = 0;
   out_5615665915161385624[213] = 0;
   out_5615665915161385624[214] = 0;
   out_5615665915161385624[215] = 0;
   out_5615665915161385624[216] = 0;
   out_5615665915161385624[217] = 0;
   out_5615665915161385624[218] = 0;
   out_5615665915161385624[219] = 0;
   out_5615665915161385624[220] = 0;
   out_5615665915161385624[221] = 0;
   out_5615665915161385624[222] = 0;
   out_5615665915161385624[223] = 0;
   out_5615665915161385624[224] = 0;
   out_5615665915161385624[225] = 0;
   out_5615665915161385624[226] = 0;
   out_5615665915161385624[227] = 0;
   out_5615665915161385624[228] = 1;
   out_5615665915161385624[229] = 0;
   out_5615665915161385624[230] = 0;
   out_5615665915161385624[231] = 0;
   out_5615665915161385624[232] = 0;
   out_5615665915161385624[233] = 0;
   out_5615665915161385624[234] = 0;
   out_5615665915161385624[235] = 0;
   out_5615665915161385624[236] = 0;
   out_5615665915161385624[237] = 0;
   out_5615665915161385624[238] = 0;
   out_5615665915161385624[239] = 0;
   out_5615665915161385624[240] = 0;
   out_5615665915161385624[241] = 0;
   out_5615665915161385624[242] = 0;
   out_5615665915161385624[243] = 0;
   out_5615665915161385624[244] = 0;
   out_5615665915161385624[245] = 0;
   out_5615665915161385624[246] = 0;
   out_5615665915161385624[247] = 1;
   out_5615665915161385624[248] = 0;
   out_5615665915161385624[249] = 0;
   out_5615665915161385624[250] = 0;
   out_5615665915161385624[251] = 0;
   out_5615665915161385624[252] = 0;
   out_5615665915161385624[253] = 0;
   out_5615665915161385624[254] = 0;
   out_5615665915161385624[255] = 0;
   out_5615665915161385624[256] = 0;
   out_5615665915161385624[257] = 0;
   out_5615665915161385624[258] = 0;
   out_5615665915161385624[259] = 0;
   out_5615665915161385624[260] = 0;
   out_5615665915161385624[261] = 0;
   out_5615665915161385624[262] = 0;
   out_5615665915161385624[263] = 0;
   out_5615665915161385624[264] = 0;
   out_5615665915161385624[265] = 0;
   out_5615665915161385624[266] = 1;
   out_5615665915161385624[267] = 0;
   out_5615665915161385624[268] = 0;
   out_5615665915161385624[269] = 0;
   out_5615665915161385624[270] = 0;
   out_5615665915161385624[271] = 0;
   out_5615665915161385624[272] = 0;
   out_5615665915161385624[273] = 0;
   out_5615665915161385624[274] = 0;
   out_5615665915161385624[275] = 0;
   out_5615665915161385624[276] = 0;
   out_5615665915161385624[277] = 0;
   out_5615665915161385624[278] = 0;
   out_5615665915161385624[279] = 0;
   out_5615665915161385624[280] = 0;
   out_5615665915161385624[281] = 0;
   out_5615665915161385624[282] = 0;
   out_5615665915161385624[283] = 0;
   out_5615665915161385624[284] = 0;
   out_5615665915161385624[285] = 1;
   out_5615665915161385624[286] = 0;
   out_5615665915161385624[287] = 0;
   out_5615665915161385624[288] = 0;
   out_5615665915161385624[289] = 0;
   out_5615665915161385624[290] = 0;
   out_5615665915161385624[291] = 0;
   out_5615665915161385624[292] = 0;
   out_5615665915161385624[293] = 0;
   out_5615665915161385624[294] = 0;
   out_5615665915161385624[295] = 0;
   out_5615665915161385624[296] = 0;
   out_5615665915161385624[297] = 0;
   out_5615665915161385624[298] = 0;
   out_5615665915161385624[299] = 0;
   out_5615665915161385624[300] = 0;
   out_5615665915161385624[301] = 0;
   out_5615665915161385624[302] = 0;
   out_5615665915161385624[303] = 0;
   out_5615665915161385624[304] = 1;
   out_5615665915161385624[305] = 0;
   out_5615665915161385624[306] = 0;
   out_5615665915161385624[307] = 0;
   out_5615665915161385624[308] = 0;
   out_5615665915161385624[309] = 0;
   out_5615665915161385624[310] = 0;
   out_5615665915161385624[311] = 0;
   out_5615665915161385624[312] = 0;
   out_5615665915161385624[313] = 0;
   out_5615665915161385624[314] = 0;
   out_5615665915161385624[315] = 0;
   out_5615665915161385624[316] = 0;
   out_5615665915161385624[317] = 0;
   out_5615665915161385624[318] = 0;
   out_5615665915161385624[319] = 0;
   out_5615665915161385624[320] = 0;
   out_5615665915161385624[321] = 0;
   out_5615665915161385624[322] = 0;
   out_5615665915161385624[323] = 1;
}
void h_4(double *state, double *unused, double *out_127652883904790585) {
   out_127652883904790585[0] = state[6] + state[9];
   out_127652883904790585[1] = state[7] + state[10];
   out_127652883904790585[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_6234378080491326150) {
   out_6234378080491326150[0] = 0;
   out_6234378080491326150[1] = 0;
   out_6234378080491326150[2] = 0;
   out_6234378080491326150[3] = 0;
   out_6234378080491326150[4] = 0;
   out_6234378080491326150[5] = 0;
   out_6234378080491326150[6] = 1;
   out_6234378080491326150[7] = 0;
   out_6234378080491326150[8] = 0;
   out_6234378080491326150[9] = 1;
   out_6234378080491326150[10] = 0;
   out_6234378080491326150[11] = 0;
   out_6234378080491326150[12] = 0;
   out_6234378080491326150[13] = 0;
   out_6234378080491326150[14] = 0;
   out_6234378080491326150[15] = 0;
   out_6234378080491326150[16] = 0;
   out_6234378080491326150[17] = 0;
   out_6234378080491326150[18] = 0;
   out_6234378080491326150[19] = 0;
   out_6234378080491326150[20] = 0;
   out_6234378080491326150[21] = 0;
   out_6234378080491326150[22] = 0;
   out_6234378080491326150[23] = 0;
   out_6234378080491326150[24] = 0;
   out_6234378080491326150[25] = 1;
   out_6234378080491326150[26] = 0;
   out_6234378080491326150[27] = 0;
   out_6234378080491326150[28] = 1;
   out_6234378080491326150[29] = 0;
   out_6234378080491326150[30] = 0;
   out_6234378080491326150[31] = 0;
   out_6234378080491326150[32] = 0;
   out_6234378080491326150[33] = 0;
   out_6234378080491326150[34] = 0;
   out_6234378080491326150[35] = 0;
   out_6234378080491326150[36] = 0;
   out_6234378080491326150[37] = 0;
   out_6234378080491326150[38] = 0;
   out_6234378080491326150[39] = 0;
   out_6234378080491326150[40] = 0;
   out_6234378080491326150[41] = 0;
   out_6234378080491326150[42] = 0;
   out_6234378080491326150[43] = 0;
   out_6234378080491326150[44] = 1;
   out_6234378080491326150[45] = 0;
   out_6234378080491326150[46] = 0;
   out_6234378080491326150[47] = 1;
   out_6234378080491326150[48] = 0;
   out_6234378080491326150[49] = 0;
   out_6234378080491326150[50] = 0;
   out_6234378080491326150[51] = 0;
   out_6234378080491326150[52] = 0;
   out_6234378080491326150[53] = 0;
}
void h_10(double *state, double *unused, double *out_8738502854513622739) {
   out_8738502854513622739[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_8738502854513622739[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_8738502854513622739[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8210870549941027059) {
   out_8210870549941027059[0] = 0;
   out_8210870549941027059[1] = 9.8100000000000005*cos(state[1]);
   out_8210870549941027059[2] = 0;
   out_8210870549941027059[3] = 0;
   out_8210870549941027059[4] = -state[8];
   out_8210870549941027059[5] = state[7];
   out_8210870549941027059[6] = 0;
   out_8210870549941027059[7] = state[5];
   out_8210870549941027059[8] = -state[4];
   out_8210870549941027059[9] = 0;
   out_8210870549941027059[10] = 0;
   out_8210870549941027059[11] = 0;
   out_8210870549941027059[12] = 1;
   out_8210870549941027059[13] = 0;
   out_8210870549941027059[14] = 0;
   out_8210870549941027059[15] = 1;
   out_8210870549941027059[16] = 0;
   out_8210870549941027059[17] = 0;
   out_8210870549941027059[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8210870549941027059[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8210870549941027059[20] = 0;
   out_8210870549941027059[21] = state[8];
   out_8210870549941027059[22] = 0;
   out_8210870549941027059[23] = -state[6];
   out_8210870549941027059[24] = -state[5];
   out_8210870549941027059[25] = 0;
   out_8210870549941027059[26] = state[3];
   out_8210870549941027059[27] = 0;
   out_8210870549941027059[28] = 0;
   out_8210870549941027059[29] = 0;
   out_8210870549941027059[30] = 0;
   out_8210870549941027059[31] = 1;
   out_8210870549941027059[32] = 0;
   out_8210870549941027059[33] = 0;
   out_8210870549941027059[34] = 1;
   out_8210870549941027059[35] = 0;
   out_8210870549941027059[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8210870549941027059[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8210870549941027059[38] = 0;
   out_8210870549941027059[39] = -state[7];
   out_8210870549941027059[40] = state[6];
   out_8210870549941027059[41] = 0;
   out_8210870549941027059[42] = state[4];
   out_8210870549941027059[43] = -state[3];
   out_8210870549941027059[44] = 0;
   out_8210870549941027059[45] = 0;
   out_8210870549941027059[46] = 0;
   out_8210870549941027059[47] = 0;
   out_8210870549941027059[48] = 0;
   out_8210870549941027059[49] = 0;
   out_8210870549941027059[50] = 1;
   out_8210870549941027059[51] = 0;
   out_8210870549941027059[52] = 0;
   out_8210870549941027059[53] = 1;
}
void h_13(double *state, double *unused, double *out_4878353631523312513) {
   out_4878353631523312513[0] = state[3];
   out_4878353631523312513[1] = state[4];
   out_4878353631523312513[2] = state[5];
}
void H_13(double *state, double *unused, double *out_9000092167885892665) {
   out_9000092167885892665[0] = 0;
   out_9000092167885892665[1] = 0;
   out_9000092167885892665[2] = 0;
   out_9000092167885892665[3] = 1;
   out_9000092167885892665[4] = 0;
   out_9000092167885892665[5] = 0;
   out_9000092167885892665[6] = 0;
   out_9000092167885892665[7] = 0;
   out_9000092167885892665[8] = 0;
   out_9000092167885892665[9] = 0;
   out_9000092167885892665[10] = 0;
   out_9000092167885892665[11] = 0;
   out_9000092167885892665[12] = 0;
   out_9000092167885892665[13] = 0;
   out_9000092167885892665[14] = 0;
   out_9000092167885892665[15] = 0;
   out_9000092167885892665[16] = 0;
   out_9000092167885892665[17] = 0;
   out_9000092167885892665[18] = 0;
   out_9000092167885892665[19] = 0;
   out_9000092167885892665[20] = 0;
   out_9000092167885892665[21] = 0;
   out_9000092167885892665[22] = 1;
   out_9000092167885892665[23] = 0;
   out_9000092167885892665[24] = 0;
   out_9000092167885892665[25] = 0;
   out_9000092167885892665[26] = 0;
   out_9000092167885892665[27] = 0;
   out_9000092167885892665[28] = 0;
   out_9000092167885892665[29] = 0;
   out_9000092167885892665[30] = 0;
   out_9000092167885892665[31] = 0;
   out_9000092167885892665[32] = 0;
   out_9000092167885892665[33] = 0;
   out_9000092167885892665[34] = 0;
   out_9000092167885892665[35] = 0;
   out_9000092167885892665[36] = 0;
   out_9000092167885892665[37] = 0;
   out_9000092167885892665[38] = 0;
   out_9000092167885892665[39] = 0;
   out_9000092167885892665[40] = 0;
   out_9000092167885892665[41] = 1;
   out_9000092167885892665[42] = 0;
   out_9000092167885892665[43] = 0;
   out_9000092167885892665[44] = 0;
   out_9000092167885892665[45] = 0;
   out_9000092167885892665[46] = 0;
   out_9000092167885892665[47] = 0;
   out_9000092167885892665[48] = 0;
   out_9000092167885892665[49] = 0;
   out_9000092167885892665[50] = 0;
   out_9000092167885892665[51] = 0;
   out_9000092167885892665[52] = 0;
   out_9000092167885892665[53] = 0;
}
void h_14(double *state, double *unused, double *out_3045142269729245966) {
   out_3045142269729245966[0] = state[6];
   out_3045142269729245966[1] = state[7];
   out_3045142269729245966[2] = state[8];
}
void H_14(double *state, double *unused, double *out_8249125136878740937) {
   out_8249125136878740937[0] = 0;
   out_8249125136878740937[1] = 0;
   out_8249125136878740937[2] = 0;
   out_8249125136878740937[3] = 0;
   out_8249125136878740937[4] = 0;
   out_8249125136878740937[5] = 0;
   out_8249125136878740937[6] = 1;
   out_8249125136878740937[7] = 0;
   out_8249125136878740937[8] = 0;
   out_8249125136878740937[9] = 0;
   out_8249125136878740937[10] = 0;
   out_8249125136878740937[11] = 0;
   out_8249125136878740937[12] = 0;
   out_8249125136878740937[13] = 0;
   out_8249125136878740937[14] = 0;
   out_8249125136878740937[15] = 0;
   out_8249125136878740937[16] = 0;
   out_8249125136878740937[17] = 0;
   out_8249125136878740937[18] = 0;
   out_8249125136878740937[19] = 0;
   out_8249125136878740937[20] = 0;
   out_8249125136878740937[21] = 0;
   out_8249125136878740937[22] = 0;
   out_8249125136878740937[23] = 0;
   out_8249125136878740937[24] = 0;
   out_8249125136878740937[25] = 1;
   out_8249125136878740937[26] = 0;
   out_8249125136878740937[27] = 0;
   out_8249125136878740937[28] = 0;
   out_8249125136878740937[29] = 0;
   out_8249125136878740937[30] = 0;
   out_8249125136878740937[31] = 0;
   out_8249125136878740937[32] = 0;
   out_8249125136878740937[33] = 0;
   out_8249125136878740937[34] = 0;
   out_8249125136878740937[35] = 0;
   out_8249125136878740937[36] = 0;
   out_8249125136878740937[37] = 0;
   out_8249125136878740937[38] = 0;
   out_8249125136878740937[39] = 0;
   out_8249125136878740937[40] = 0;
   out_8249125136878740937[41] = 0;
   out_8249125136878740937[42] = 0;
   out_8249125136878740937[43] = 0;
   out_8249125136878740937[44] = 1;
   out_8249125136878740937[45] = 0;
   out_8249125136878740937[46] = 0;
   out_8249125136878740937[47] = 0;
   out_8249125136878740937[48] = 0;
   out_8249125136878740937[49] = 0;
   out_8249125136878740937[50] = 0;
   out_8249125136878740937[51] = 0;
   out_8249125136878740937[52] = 0;
   out_8249125136878740937[53] = 0;
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

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_208995533761529617) {
  err_fun(nom_x, delta_x, out_208995533761529617);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5913231907866039975) {
  inv_err_fun(nom_x, true_x, out_5913231907866039975);
}
void pose_H_mod_fun(double *state, double *out_8938143914427276213) {
  H_mod_fun(state, out_8938143914427276213);
}
void pose_f_fun(double *state, double dt, double *out_6822525905221779246) {
  f_fun(state,  dt, out_6822525905221779246);
}
void pose_F_fun(double *state, double dt, double *out_5615665915161385624) {
  F_fun(state,  dt, out_5615665915161385624);
}
void pose_h_4(double *state, double *unused, double *out_127652883904790585) {
  h_4(state, unused, out_127652883904790585);
}
void pose_H_4(double *state, double *unused, double *out_6234378080491326150) {
  H_4(state, unused, out_6234378080491326150);
}
void pose_h_10(double *state, double *unused, double *out_8738502854513622739) {
  h_10(state, unused, out_8738502854513622739);
}
void pose_H_10(double *state, double *unused, double *out_8210870549941027059) {
  H_10(state, unused, out_8210870549941027059);
}
void pose_h_13(double *state, double *unused, double *out_4878353631523312513) {
  h_13(state, unused, out_4878353631523312513);
}
void pose_H_13(double *state, double *unused, double *out_9000092167885892665) {
  H_13(state, unused, out_9000092167885892665);
}
void pose_h_14(double *state, double *unused, double *out_3045142269729245966) {
  h_14(state, unused, out_3045142269729245966);
}
void pose_H_14(double *state, double *unused, double *out_8249125136878740937) {
  H_14(state, unused, out_8249125136878740937);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
