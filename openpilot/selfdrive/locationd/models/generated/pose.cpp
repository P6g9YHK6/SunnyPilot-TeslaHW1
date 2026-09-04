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
void err_fun(double *nom_x, double *delta_x, double *out_8102601374041299900) {
   out_8102601374041299900[0] = delta_x[0] + nom_x[0];
   out_8102601374041299900[1] = delta_x[1] + nom_x[1];
   out_8102601374041299900[2] = delta_x[2] + nom_x[2];
   out_8102601374041299900[3] = delta_x[3] + nom_x[3];
   out_8102601374041299900[4] = delta_x[4] + nom_x[4];
   out_8102601374041299900[5] = delta_x[5] + nom_x[5];
   out_8102601374041299900[6] = delta_x[6] + nom_x[6];
   out_8102601374041299900[7] = delta_x[7] + nom_x[7];
   out_8102601374041299900[8] = delta_x[8] + nom_x[8];
   out_8102601374041299900[9] = delta_x[9] + nom_x[9];
   out_8102601374041299900[10] = delta_x[10] + nom_x[10];
   out_8102601374041299900[11] = delta_x[11] + nom_x[11];
   out_8102601374041299900[12] = delta_x[12] + nom_x[12];
   out_8102601374041299900[13] = delta_x[13] + nom_x[13];
   out_8102601374041299900[14] = delta_x[14] + nom_x[14];
   out_8102601374041299900[15] = delta_x[15] + nom_x[15];
   out_8102601374041299900[16] = delta_x[16] + nom_x[16];
   out_8102601374041299900[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3419876428506429302) {
   out_3419876428506429302[0] = -nom_x[0] + true_x[0];
   out_3419876428506429302[1] = -nom_x[1] + true_x[1];
   out_3419876428506429302[2] = -nom_x[2] + true_x[2];
   out_3419876428506429302[3] = -nom_x[3] + true_x[3];
   out_3419876428506429302[4] = -nom_x[4] + true_x[4];
   out_3419876428506429302[5] = -nom_x[5] + true_x[5];
   out_3419876428506429302[6] = -nom_x[6] + true_x[6];
   out_3419876428506429302[7] = -nom_x[7] + true_x[7];
   out_3419876428506429302[8] = -nom_x[8] + true_x[8];
   out_3419876428506429302[9] = -nom_x[9] + true_x[9];
   out_3419876428506429302[10] = -nom_x[10] + true_x[10];
   out_3419876428506429302[11] = -nom_x[11] + true_x[11];
   out_3419876428506429302[12] = -nom_x[12] + true_x[12];
   out_3419876428506429302[13] = -nom_x[13] + true_x[13];
   out_3419876428506429302[14] = -nom_x[14] + true_x[14];
   out_3419876428506429302[15] = -nom_x[15] + true_x[15];
   out_3419876428506429302[16] = -nom_x[16] + true_x[16];
   out_3419876428506429302[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_4546444682940926041) {
   out_4546444682940926041[0] = 1.0;
   out_4546444682940926041[1] = 0.0;
   out_4546444682940926041[2] = 0.0;
   out_4546444682940926041[3] = 0.0;
   out_4546444682940926041[4] = 0.0;
   out_4546444682940926041[5] = 0.0;
   out_4546444682940926041[6] = 0.0;
   out_4546444682940926041[7] = 0.0;
   out_4546444682940926041[8] = 0.0;
   out_4546444682940926041[9] = 0.0;
   out_4546444682940926041[10] = 0.0;
   out_4546444682940926041[11] = 0.0;
   out_4546444682940926041[12] = 0.0;
   out_4546444682940926041[13] = 0.0;
   out_4546444682940926041[14] = 0.0;
   out_4546444682940926041[15] = 0.0;
   out_4546444682940926041[16] = 0.0;
   out_4546444682940926041[17] = 0.0;
   out_4546444682940926041[18] = 0.0;
   out_4546444682940926041[19] = 1.0;
   out_4546444682940926041[20] = 0.0;
   out_4546444682940926041[21] = 0.0;
   out_4546444682940926041[22] = 0.0;
   out_4546444682940926041[23] = 0.0;
   out_4546444682940926041[24] = 0.0;
   out_4546444682940926041[25] = 0.0;
   out_4546444682940926041[26] = 0.0;
   out_4546444682940926041[27] = 0.0;
   out_4546444682940926041[28] = 0.0;
   out_4546444682940926041[29] = 0.0;
   out_4546444682940926041[30] = 0.0;
   out_4546444682940926041[31] = 0.0;
   out_4546444682940926041[32] = 0.0;
   out_4546444682940926041[33] = 0.0;
   out_4546444682940926041[34] = 0.0;
   out_4546444682940926041[35] = 0.0;
   out_4546444682940926041[36] = 0.0;
   out_4546444682940926041[37] = 0.0;
   out_4546444682940926041[38] = 1.0;
   out_4546444682940926041[39] = 0.0;
   out_4546444682940926041[40] = 0.0;
   out_4546444682940926041[41] = 0.0;
   out_4546444682940926041[42] = 0.0;
   out_4546444682940926041[43] = 0.0;
   out_4546444682940926041[44] = 0.0;
   out_4546444682940926041[45] = 0.0;
   out_4546444682940926041[46] = 0.0;
   out_4546444682940926041[47] = 0.0;
   out_4546444682940926041[48] = 0.0;
   out_4546444682940926041[49] = 0.0;
   out_4546444682940926041[50] = 0.0;
   out_4546444682940926041[51] = 0.0;
   out_4546444682940926041[52] = 0.0;
   out_4546444682940926041[53] = 0.0;
   out_4546444682940926041[54] = 0.0;
   out_4546444682940926041[55] = 0.0;
   out_4546444682940926041[56] = 0.0;
   out_4546444682940926041[57] = 1.0;
   out_4546444682940926041[58] = 0.0;
   out_4546444682940926041[59] = 0.0;
   out_4546444682940926041[60] = 0.0;
   out_4546444682940926041[61] = 0.0;
   out_4546444682940926041[62] = 0.0;
   out_4546444682940926041[63] = 0.0;
   out_4546444682940926041[64] = 0.0;
   out_4546444682940926041[65] = 0.0;
   out_4546444682940926041[66] = 0.0;
   out_4546444682940926041[67] = 0.0;
   out_4546444682940926041[68] = 0.0;
   out_4546444682940926041[69] = 0.0;
   out_4546444682940926041[70] = 0.0;
   out_4546444682940926041[71] = 0.0;
   out_4546444682940926041[72] = 0.0;
   out_4546444682940926041[73] = 0.0;
   out_4546444682940926041[74] = 0.0;
   out_4546444682940926041[75] = 0.0;
   out_4546444682940926041[76] = 1.0;
   out_4546444682940926041[77] = 0.0;
   out_4546444682940926041[78] = 0.0;
   out_4546444682940926041[79] = 0.0;
   out_4546444682940926041[80] = 0.0;
   out_4546444682940926041[81] = 0.0;
   out_4546444682940926041[82] = 0.0;
   out_4546444682940926041[83] = 0.0;
   out_4546444682940926041[84] = 0.0;
   out_4546444682940926041[85] = 0.0;
   out_4546444682940926041[86] = 0.0;
   out_4546444682940926041[87] = 0.0;
   out_4546444682940926041[88] = 0.0;
   out_4546444682940926041[89] = 0.0;
   out_4546444682940926041[90] = 0.0;
   out_4546444682940926041[91] = 0.0;
   out_4546444682940926041[92] = 0.0;
   out_4546444682940926041[93] = 0.0;
   out_4546444682940926041[94] = 0.0;
   out_4546444682940926041[95] = 1.0;
   out_4546444682940926041[96] = 0.0;
   out_4546444682940926041[97] = 0.0;
   out_4546444682940926041[98] = 0.0;
   out_4546444682940926041[99] = 0.0;
   out_4546444682940926041[100] = 0.0;
   out_4546444682940926041[101] = 0.0;
   out_4546444682940926041[102] = 0.0;
   out_4546444682940926041[103] = 0.0;
   out_4546444682940926041[104] = 0.0;
   out_4546444682940926041[105] = 0.0;
   out_4546444682940926041[106] = 0.0;
   out_4546444682940926041[107] = 0.0;
   out_4546444682940926041[108] = 0.0;
   out_4546444682940926041[109] = 0.0;
   out_4546444682940926041[110] = 0.0;
   out_4546444682940926041[111] = 0.0;
   out_4546444682940926041[112] = 0.0;
   out_4546444682940926041[113] = 0.0;
   out_4546444682940926041[114] = 1.0;
   out_4546444682940926041[115] = 0.0;
   out_4546444682940926041[116] = 0.0;
   out_4546444682940926041[117] = 0.0;
   out_4546444682940926041[118] = 0.0;
   out_4546444682940926041[119] = 0.0;
   out_4546444682940926041[120] = 0.0;
   out_4546444682940926041[121] = 0.0;
   out_4546444682940926041[122] = 0.0;
   out_4546444682940926041[123] = 0.0;
   out_4546444682940926041[124] = 0.0;
   out_4546444682940926041[125] = 0.0;
   out_4546444682940926041[126] = 0.0;
   out_4546444682940926041[127] = 0.0;
   out_4546444682940926041[128] = 0.0;
   out_4546444682940926041[129] = 0.0;
   out_4546444682940926041[130] = 0.0;
   out_4546444682940926041[131] = 0.0;
   out_4546444682940926041[132] = 0.0;
   out_4546444682940926041[133] = 1.0;
   out_4546444682940926041[134] = 0.0;
   out_4546444682940926041[135] = 0.0;
   out_4546444682940926041[136] = 0.0;
   out_4546444682940926041[137] = 0.0;
   out_4546444682940926041[138] = 0.0;
   out_4546444682940926041[139] = 0.0;
   out_4546444682940926041[140] = 0.0;
   out_4546444682940926041[141] = 0.0;
   out_4546444682940926041[142] = 0.0;
   out_4546444682940926041[143] = 0.0;
   out_4546444682940926041[144] = 0.0;
   out_4546444682940926041[145] = 0.0;
   out_4546444682940926041[146] = 0.0;
   out_4546444682940926041[147] = 0.0;
   out_4546444682940926041[148] = 0.0;
   out_4546444682940926041[149] = 0.0;
   out_4546444682940926041[150] = 0.0;
   out_4546444682940926041[151] = 0.0;
   out_4546444682940926041[152] = 1.0;
   out_4546444682940926041[153] = 0.0;
   out_4546444682940926041[154] = 0.0;
   out_4546444682940926041[155] = 0.0;
   out_4546444682940926041[156] = 0.0;
   out_4546444682940926041[157] = 0.0;
   out_4546444682940926041[158] = 0.0;
   out_4546444682940926041[159] = 0.0;
   out_4546444682940926041[160] = 0.0;
   out_4546444682940926041[161] = 0.0;
   out_4546444682940926041[162] = 0.0;
   out_4546444682940926041[163] = 0.0;
   out_4546444682940926041[164] = 0.0;
   out_4546444682940926041[165] = 0.0;
   out_4546444682940926041[166] = 0.0;
   out_4546444682940926041[167] = 0.0;
   out_4546444682940926041[168] = 0.0;
   out_4546444682940926041[169] = 0.0;
   out_4546444682940926041[170] = 0.0;
   out_4546444682940926041[171] = 1.0;
   out_4546444682940926041[172] = 0.0;
   out_4546444682940926041[173] = 0.0;
   out_4546444682940926041[174] = 0.0;
   out_4546444682940926041[175] = 0.0;
   out_4546444682940926041[176] = 0.0;
   out_4546444682940926041[177] = 0.0;
   out_4546444682940926041[178] = 0.0;
   out_4546444682940926041[179] = 0.0;
   out_4546444682940926041[180] = 0.0;
   out_4546444682940926041[181] = 0.0;
   out_4546444682940926041[182] = 0.0;
   out_4546444682940926041[183] = 0.0;
   out_4546444682940926041[184] = 0.0;
   out_4546444682940926041[185] = 0.0;
   out_4546444682940926041[186] = 0.0;
   out_4546444682940926041[187] = 0.0;
   out_4546444682940926041[188] = 0.0;
   out_4546444682940926041[189] = 0.0;
   out_4546444682940926041[190] = 1.0;
   out_4546444682940926041[191] = 0.0;
   out_4546444682940926041[192] = 0.0;
   out_4546444682940926041[193] = 0.0;
   out_4546444682940926041[194] = 0.0;
   out_4546444682940926041[195] = 0.0;
   out_4546444682940926041[196] = 0.0;
   out_4546444682940926041[197] = 0.0;
   out_4546444682940926041[198] = 0.0;
   out_4546444682940926041[199] = 0.0;
   out_4546444682940926041[200] = 0.0;
   out_4546444682940926041[201] = 0.0;
   out_4546444682940926041[202] = 0.0;
   out_4546444682940926041[203] = 0.0;
   out_4546444682940926041[204] = 0.0;
   out_4546444682940926041[205] = 0.0;
   out_4546444682940926041[206] = 0.0;
   out_4546444682940926041[207] = 0.0;
   out_4546444682940926041[208] = 0.0;
   out_4546444682940926041[209] = 1.0;
   out_4546444682940926041[210] = 0.0;
   out_4546444682940926041[211] = 0.0;
   out_4546444682940926041[212] = 0.0;
   out_4546444682940926041[213] = 0.0;
   out_4546444682940926041[214] = 0.0;
   out_4546444682940926041[215] = 0.0;
   out_4546444682940926041[216] = 0.0;
   out_4546444682940926041[217] = 0.0;
   out_4546444682940926041[218] = 0.0;
   out_4546444682940926041[219] = 0.0;
   out_4546444682940926041[220] = 0.0;
   out_4546444682940926041[221] = 0.0;
   out_4546444682940926041[222] = 0.0;
   out_4546444682940926041[223] = 0.0;
   out_4546444682940926041[224] = 0.0;
   out_4546444682940926041[225] = 0.0;
   out_4546444682940926041[226] = 0.0;
   out_4546444682940926041[227] = 0.0;
   out_4546444682940926041[228] = 1.0;
   out_4546444682940926041[229] = 0.0;
   out_4546444682940926041[230] = 0.0;
   out_4546444682940926041[231] = 0.0;
   out_4546444682940926041[232] = 0.0;
   out_4546444682940926041[233] = 0.0;
   out_4546444682940926041[234] = 0.0;
   out_4546444682940926041[235] = 0.0;
   out_4546444682940926041[236] = 0.0;
   out_4546444682940926041[237] = 0.0;
   out_4546444682940926041[238] = 0.0;
   out_4546444682940926041[239] = 0.0;
   out_4546444682940926041[240] = 0.0;
   out_4546444682940926041[241] = 0.0;
   out_4546444682940926041[242] = 0.0;
   out_4546444682940926041[243] = 0.0;
   out_4546444682940926041[244] = 0.0;
   out_4546444682940926041[245] = 0.0;
   out_4546444682940926041[246] = 0.0;
   out_4546444682940926041[247] = 1.0;
   out_4546444682940926041[248] = 0.0;
   out_4546444682940926041[249] = 0.0;
   out_4546444682940926041[250] = 0.0;
   out_4546444682940926041[251] = 0.0;
   out_4546444682940926041[252] = 0.0;
   out_4546444682940926041[253] = 0.0;
   out_4546444682940926041[254] = 0.0;
   out_4546444682940926041[255] = 0.0;
   out_4546444682940926041[256] = 0.0;
   out_4546444682940926041[257] = 0.0;
   out_4546444682940926041[258] = 0.0;
   out_4546444682940926041[259] = 0.0;
   out_4546444682940926041[260] = 0.0;
   out_4546444682940926041[261] = 0.0;
   out_4546444682940926041[262] = 0.0;
   out_4546444682940926041[263] = 0.0;
   out_4546444682940926041[264] = 0.0;
   out_4546444682940926041[265] = 0.0;
   out_4546444682940926041[266] = 1.0;
   out_4546444682940926041[267] = 0.0;
   out_4546444682940926041[268] = 0.0;
   out_4546444682940926041[269] = 0.0;
   out_4546444682940926041[270] = 0.0;
   out_4546444682940926041[271] = 0.0;
   out_4546444682940926041[272] = 0.0;
   out_4546444682940926041[273] = 0.0;
   out_4546444682940926041[274] = 0.0;
   out_4546444682940926041[275] = 0.0;
   out_4546444682940926041[276] = 0.0;
   out_4546444682940926041[277] = 0.0;
   out_4546444682940926041[278] = 0.0;
   out_4546444682940926041[279] = 0.0;
   out_4546444682940926041[280] = 0.0;
   out_4546444682940926041[281] = 0.0;
   out_4546444682940926041[282] = 0.0;
   out_4546444682940926041[283] = 0.0;
   out_4546444682940926041[284] = 0.0;
   out_4546444682940926041[285] = 1.0;
   out_4546444682940926041[286] = 0.0;
   out_4546444682940926041[287] = 0.0;
   out_4546444682940926041[288] = 0.0;
   out_4546444682940926041[289] = 0.0;
   out_4546444682940926041[290] = 0.0;
   out_4546444682940926041[291] = 0.0;
   out_4546444682940926041[292] = 0.0;
   out_4546444682940926041[293] = 0.0;
   out_4546444682940926041[294] = 0.0;
   out_4546444682940926041[295] = 0.0;
   out_4546444682940926041[296] = 0.0;
   out_4546444682940926041[297] = 0.0;
   out_4546444682940926041[298] = 0.0;
   out_4546444682940926041[299] = 0.0;
   out_4546444682940926041[300] = 0.0;
   out_4546444682940926041[301] = 0.0;
   out_4546444682940926041[302] = 0.0;
   out_4546444682940926041[303] = 0.0;
   out_4546444682940926041[304] = 1.0;
   out_4546444682940926041[305] = 0.0;
   out_4546444682940926041[306] = 0.0;
   out_4546444682940926041[307] = 0.0;
   out_4546444682940926041[308] = 0.0;
   out_4546444682940926041[309] = 0.0;
   out_4546444682940926041[310] = 0.0;
   out_4546444682940926041[311] = 0.0;
   out_4546444682940926041[312] = 0.0;
   out_4546444682940926041[313] = 0.0;
   out_4546444682940926041[314] = 0.0;
   out_4546444682940926041[315] = 0.0;
   out_4546444682940926041[316] = 0.0;
   out_4546444682940926041[317] = 0.0;
   out_4546444682940926041[318] = 0.0;
   out_4546444682940926041[319] = 0.0;
   out_4546444682940926041[320] = 0.0;
   out_4546444682940926041[321] = 0.0;
   out_4546444682940926041[322] = 0.0;
   out_4546444682940926041[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_1236460484987931538) {
   out_1236460484987931538[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_1236460484987931538[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_1236460484987931538[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_1236460484987931538[3] = dt*state[12] + state[3];
   out_1236460484987931538[4] = dt*state[13] + state[4];
   out_1236460484987931538[5] = dt*state[14] + state[5];
   out_1236460484987931538[6] = state[6];
   out_1236460484987931538[7] = state[7];
   out_1236460484987931538[8] = state[8];
   out_1236460484987931538[9] = state[9];
   out_1236460484987931538[10] = state[10];
   out_1236460484987931538[11] = state[11];
   out_1236460484987931538[12] = state[12];
   out_1236460484987931538[13] = state[13];
   out_1236460484987931538[14] = state[14];
   out_1236460484987931538[15] = state[15];
   out_1236460484987931538[16] = state[16];
   out_1236460484987931538[17] = state[17];
}
void F_fun(double *state, double dt, double *out_7321518554926371343) {
   out_7321518554926371343[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7321518554926371343[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7321518554926371343[2] = 0;
   out_7321518554926371343[3] = 0;
   out_7321518554926371343[4] = 0;
   out_7321518554926371343[5] = 0;
   out_7321518554926371343[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7321518554926371343[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7321518554926371343[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7321518554926371343[9] = 0;
   out_7321518554926371343[10] = 0;
   out_7321518554926371343[11] = 0;
   out_7321518554926371343[12] = 0;
   out_7321518554926371343[13] = 0;
   out_7321518554926371343[14] = 0;
   out_7321518554926371343[15] = 0;
   out_7321518554926371343[16] = 0;
   out_7321518554926371343[17] = 0;
   out_7321518554926371343[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7321518554926371343[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7321518554926371343[20] = 0;
   out_7321518554926371343[21] = 0;
   out_7321518554926371343[22] = 0;
   out_7321518554926371343[23] = 0;
   out_7321518554926371343[24] = 0;
   out_7321518554926371343[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7321518554926371343[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7321518554926371343[27] = 0;
   out_7321518554926371343[28] = 0;
   out_7321518554926371343[29] = 0;
   out_7321518554926371343[30] = 0;
   out_7321518554926371343[31] = 0;
   out_7321518554926371343[32] = 0;
   out_7321518554926371343[33] = 0;
   out_7321518554926371343[34] = 0;
   out_7321518554926371343[35] = 0;
   out_7321518554926371343[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7321518554926371343[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7321518554926371343[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7321518554926371343[39] = 0;
   out_7321518554926371343[40] = 0;
   out_7321518554926371343[41] = 0;
   out_7321518554926371343[42] = 0;
   out_7321518554926371343[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7321518554926371343[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7321518554926371343[45] = 0;
   out_7321518554926371343[46] = 0;
   out_7321518554926371343[47] = 0;
   out_7321518554926371343[48] = 0;
   out_7321518554926371343[49] = 0;
   out_7321518554926371343[50] = 0;
   out_7321518554926371343[51] = 0;
   out_7321518554926371343[52] = 0;
   out_7321518554926371343[53] = 0;
   out_7321518554926371343[54] = 0;
   out_7321518554926371343[55] = 0;
   out_7321518554926371343[56] = 0;
   out_7321518554926371343[57] = 1;
   out_7321518554926371343[58] = 0;
   out_7321518554926371343[59] = 0;
   out_7321518554926371343[60] = 0;
   out_7321518554926371343[61] = 0;
   out_7321518554926371343[62] = 0;
   out_7321518554926371343[63] = 0;
   out_7321518554926371343[64] = 0;
   out_7321518554926371343[65] = 0;
   out_7321518554926371343[66] = dt;
   out_7321518554926371343[67] = 0;
   out_7321518554926371343[68] = 0;
   out_7321518554926371343[69] = 0;
   out_7321518554926371343[70] = 0;
   out_7321518554926371343[71] = 0;
   out_7321518554926371343[72] = 0;
   out_7321518554926371343[73] = 0;
   out_7321518554926371343[74] = 0;
   out_7321518554926371343[75] = 0;
   out_7321518554926371343[76] = 1;
   out_7321518554926371343[77] = 0;
   out_7321518554926371343[78] = 0;
   out_7321518554926371343[79] = 0;
   out_7321518554926371343[80] = 0;
   out_7321518554926371343[81] = 0;
   out_7321518554926371343[82] = 0;
   out_7321518554926371343[83] = 0;
   out_7321518554926371343[84] = 0;
   out_7321518554926371343[85] = dt;
   out_7321518554926371343[86] = 0;
   out_7321518554926371343[87] = 0;
   out_7321518554926371343[88] = 0;
   out_7321518554926371343[89] = 0;
   out_7321518554926371343[90] = 0;
   out_7321518554926371343[91] = 0;
   out_7321518554926371343[92] = 0;
   out_7321518554926371343[93] = 0;
   out_7321518554926371343[94] = 0;
   out_7321518554926371343[95] = 1;
   out_7321518554926371343[96] = 0;
   out_7321518554926371343[97] = 0;
   out_7321518554926371343[98] = 0;
   out_7321518554926371343[99] = 0;
   out_7321518554926371343[100] = 0;
   out_7321518554926371343[101] = 0;
   out_7321518554926371343[102] = 0;
   out_7321518554926371343[103] = 0;
   out_7321518554926371343[104] = dt;
   out_7321518554926371343[105] = 0;
   out_7321518554926371343[106] = 0;
   out_7321518554926371343[107] = 0;
   out_7321518554926371343[108] = 0;
   out_7321518554926371343[109] = 0;
   out_7321518554926371343[110] = 0;
   out_7321518554926371343[111] = 0;
   out_7321518554926371343[112] = 0;
   out_7321518554926371343[113] = 0;
   out_7321518554926371343[114] = 1;
   out_7321518554926371343[115] = 0;
   out_7321518554926371343[116] = 0;
   out_7321518554926371343[117] = 0;
   out_7321518554926371343[118] = 0;
   out_7321518554926371343[119] = 0;
   out_7321518554926371343[120] = 0;
   out_7321518554926371343[121] = 0;
   out_7321518554926371343[122] = 0;
   out_7321518554926371343[123] = 0;
   out_7321518554926371343[124] = 0;
   out_7321518554926371343[125] = 0;
   out_7321518554926371343[126] = 0;
   out_7321518554926371343[127] = 0;
   out_7321518554926371343[128] = 0;
   out_7321518554926371343[129] = 0;
   out_7321518554926371343[130] = 0;
   out_7321518554926371343[131] = 0;
   out_7321518554926371343[132] = 0;
   out_7321518554926371343[133] = 1;
   out_7321518554926371343[134] = 0;
   out_7321518554926371343[135] = 0;
   out_7321518554926371343[136] = 0;
   out_7321518554926371343[137] = 0;
   out_7321518554926371343[138] = 0;
   out_7321518554926371343[139] = 0;
   out_7321518554926371343[140] = 0;
   out_7321518554926371343[141] = 0;
   out_7321518554926371343[142] = 0;
   out_7321518554926371343[143] = 0;
   out_7321518554926371343[144] = 0;
   out_7321518554926371343[145] = 0;
   out_7321518554926371343[146] = 0;
   out_7321518554926371343[147] = 0;
   out_7321518554926371343[148] = 0;
   out_7321518554926371343[149] = 0;
   out_7321518554926371343[150] = 0;
   out_7321518554926371343[151] = 0;
   out_7321518554926371343[152] = 1;
   out_7321518554926371343[153] = 0;
   out_7321518554926371343[154] = 0;
   out_7321518554926371343[155] = 0;
   out_7321518554926371343[156] = 0;
   out_7321518554926371343[157] = 0;
   out_7321518554926371343[158] = 0;
   out_7321518554926371343[159] = 0;
   out_7321518554926371343[160] = 0;
   out_7321518554926371343[161] = 0;
   out_7321518554926371343[162] = 0;
   out_7321518554926371343[163] = 0;
   out_7321518554926371343[164] = 0;
   out_7321518554926371343[165] = 0;
   out_7321518554926371343[166] = 0;
   out_7321518554926371343[167] = 0;
   out_7321518554926371343[168] = 0;
   out_7321518554926371343[169] = 0;
   out_7321518554926371343[170] = 0;
   out_7321518554926371343[171] = 1;
   out_7321518554926371343[172] = 0;
   out_7321518554926371343[173] = 0;
   out_7321518554926371343[174] = 0;
   out_7321518554926371343[175] = 0;
   out_7321518554926371343[176] = 0;
   out_7321518554926371343[177] = 0;
   out_7321518554926371343[178] = 0;
   out_7321518554926371343[179] = 0;
   out_7321518554926371343[180] = 0;
   out_7321518554926371343[181] = 0;
   out_7321518554926371343[182] = 0;
   out_7321518554926371343[183] = 0;
   out_7321518554926371343[184] = 0;
   out_7321518554926371343[185] = 0;
   out_7321518554926371343[186] = 0;
   out_7321518554926371343[187] = 0;
   out_7321518554926371343[188] = 0;
   out_7321518554926371343[189] = 0;
   out_7321518554926371343[190] = 1;
   out_7321518554926371343[191] = 0;
   out_7321518554926371343[192] = 0;
   out_7321518554926371343[193] = 0;
   out_7321518554926371343[194] = 0;
   out_7321518554926371343[195] = 0;
   out_7321518554926371343[196] = 0;
   out_7321518554926371343[197] = 0;
   out_7321518554926371343[198] = 0;
   out_7321518554926371343[199] = 0;
   out_7321518554926371343[200] = 0;
   out_7321518554926371343[201] = 0;
   out_7321518554926371343[202] = 0;
   out_7321518554926371343[203] = 0;
   out_7321518554926371343[204] = 0;
   out_7321518554926371343[205] = 0;
   out_7321518554926371343[206] = 0;
   out_7321518554926371343[207] = 0;
   out_7321518554926371343[208] = 0;
   out_7321518554926371343[209] = 1;
   out_7321518554926371343[210] = 0;
   out_7321518554926371343[211] = 0;
   out_7321518554926371343[212] = 0;
   out_7321518554926371343[213] = 0;
   out_7321518554926371343[214] = 0;
   out_7321518554926371343[215] = 0;
   out_7321518554926371343[216] = 0;
   out_7321518554926371343[217] = 0;
   out_7321518554926371343[218] = 0;
   out_7321518554926371343[219] = 0;
   out_7321518554926371343[220] = 0;
   out_7321518554926371343[221] = 0;
   out_7321518554926371343[222] = 0;
   out_7321518554926371343[223] = 0;
   out_7321518554926371343[224] = 0;
   out_7321518554926371343[225] = 0;
   out_7321518554926371343[226] = 0;
   out_7321518554926371343[227] = 0;
   out_7321518554926371343[228] = 1;
   out_7321518554926371343[229] = 0;
   out_7321518554926371343[230] = 0;
   out_7321518554926371343[231] = 0;
   out_7321518554926371343[232] = 0;
   out_7321518554926371343[233] = 0;
   out_7321518554926371343[234] = 0;
   out_7321518554926371343[235] = 0;
   out_7321518554926371343[236] = 0;
   out_7321518554926371343[237] = 0;
   out_7321518554926371343[238] = 0;
   out_7321518554926371343[239] = 0;
   out_7321518554926371343[240] = 0;
   out_7321518554926371343[241] = 0;
   out_7321518554926371343[242] = 0;
   out_7321518554926371343[243] = 0;
   out_7321518554926371343[244] = 0;
   out_7321518554926371343[245] = 0;
   out_7321518554926371343[246] = 0;
   out_7321518554926371343[247] = 1;
   out_7321518554926371343[248] = 0;
   out_7321518554926371343[249] = 0;
   out_7321518554926371343[250] = 0;
   out_7321518554926371343[251] = 0;
   out_7321518554926371343[252] = 0;
   out_7321518554926371343[253] = 0;
   out_7321518554926371343[254] = 0;
   out_7321518554926371343[255] = 0;
   out_7321518554926371343[256] = 0;
   out_7321518554926371343[257] = 0;
   out_7321518554926371343[258] = 0;
   out_7321518554926371343[259] = 0;
   out_7321518554926371343[260] = 0;
   out_7321518554926371343[261] = 0;
   out_7321518554926371343[262] = 0;
   out_7321518554926371343[263] = 0;
   out_7321518554926371343[264] = 0;
   out_7321518554926371343[265] = 0;
   out_7321518554926371343[266] = 1;
   out_7321518554926371343[267] = 0;
   out_7321518554926371343[268] = 0;
   out_7321518554926371343[269] = 0;
   out_7321518554926371343[270] = 0;
   out_7321518554926371343[271] = 0;
   out_7321518554926371343[272] = 0;
   out_7321518554926371343[273] = 0;
   out_7321518554926371343[274] = 0;
   out_7321518554926371343[275] = 0;
   out_7321518554926371343[276] = 0;
   out_7321518554926371343[277] = 0;
   out_7321518554926371343[278] = 0;
   out_7321518554926371343[279] = 0;
   out_7321518554926371343[280] = 0;
   out_7321518554926371343[281] = 0;
   out_7321518554926371343[282] = 0;
   out_7321518554926371343[283] = 0;
   out_7321518554926371343[284] = 0;
   out_7321518554926371343[285] = 1;
   out_7321518554926371343[286] = 0;
   out_7321518554926371343[287] = 0;
   out_7321518554926371343[288] = 0;
   out_7321518554926371343[289] = 0;
   out_7321518554926371343[290] = 0;
   out_7321518554926371343[291] = 0;
   out_7321518554926371343[292] = 0;
   out_7321518554926371343[293] = 0;
   out_7321518554926371343[294] = 0;
   out_7321518554926371343[295] = 0;
   out_7321518554926371343[296] = 0;
   out_7321518554926371343[297] = 0;
   out_7321518554926371343[298] = 0;
   out_7321518554926371343[299] = 0;
   out_7321518554926371343[300] = 0;
   out_7321518554926371343[301] = 0;
   out_7321518554926371343[302] = 0;
   out_7321518554926371343[303] = 0;
   out_7321518554926371343[304] = 1;
   out_7321518554926371343[305] = 0;
   out_7321518554926371343[306] = 0;
   out_7321518554926371343[307] = 0;
   out_7321518554926371343[308] = 0;
   out_7321518554926371343[309] = 0;
   out_7321518554926371343[310] = 0;
   out_7321518554926371343[311] = 0;
   out_7321518554926371343[312] = 0;
   out_7321518554926371343[313] = 0;
   out_7321518554926371343[314] = 0;
   out_7321518554926371343[315] = 0;
   out_7321518554926371343[316] = 0;
   out_7321518554926371343[317] = 0;
   out_7321518554926371343[318] = 0;
   out_7321518554926371343[319] = 0;
   out_7321518554926371343[320] = 0;
   out_7321518554926371343[321] = 0;
   out_7321518554926371343[322] = 0;
   out_7321518554926371343[323] = 1;
}
void h_4(double *state, double *unused, double *out_6863588878347655231) {
   out_6863588878347655231[0] = state[6] + state[9];
   out_6863588878347655231[1] = state[7] + state[10];
   out_6863588878347655231[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8052217584016666854) {
   out_8052217584016666854[0] = 0;
   out_8052217584016666854[1] = 0;
   out_8052217584016666854[2] = 0;
   out_8052217584016666854[3] = 0;
   out_8052217584016666854[4] = 0;
   out_8052217584016666854[5] = 0;
   out_8052217584016666854[6] = 1;
   out_8052217584016666854[7] = 0;
   out_8052217584016666854[8] = 0;
   out_8052217584016666854[9] = 1;
   out_8052217584016666854[10] = 0;
   out_8052217584016666854[11] = 0;
   out_8052217584016666854[12] = 0;
   out_8052217584016666854[13] = 0;
   out_8052217584016666854[14] = 0;
   out_8052217584016666854[15] = 0;
   out_8052217584016666854[16] = 0;
   out_8052217584016666854[17] = 0;
   out_8052217584016666854[18] = 0;
   out_8052217584016666854[19] = 0;
   out_8052217584016666854[20] = 0;
   out_8052217584016666854[21] = 0;
   out_8052217584016666854[22] = 0;
   out_8052217584016666854[23] = 0;
   out_8052217584016666854[24] = 0;
   out_8052217584016666854[25] = 1;
   out_8052217584016666854[26] = 0;
   out_8052217584016666854[27] = 0;
   out_8052217584016666854[28] = 1;
   out_8052217584016666854[29] = 0;
   out_8052217584016666854[30] = 0;
   out_8052217584016666854[31] = 0;
   out_8052217584016666854[32] = 0;
   out_8052217584016666854[33] = 0;
   out_8052217584016666854[34] = 0;
   out_8052217584016666854[35] = 0;
   out_8052217584016666854[36] = 0;
   out_8052217584016666854[37] = 0;
   out_8052217584016666854[38] = 0;
   out_8052217584016666854[39] = 0;
   out_8052217584016666854[40] = 0;
   out_8052217584016666854[41] = 0;
   out_8052217584016666854[42] = 0;
   out_8052217584016666854[43] = 0;
   out_8052217584016666854[44] = 1;
   out_8052217584016666854[45] = 0;
   out_8052217584016666854[46] = 0;
   out_8052217584016666854[47] = 1;
   out_8052217584016666854[48] = 0;
   out_8052217584016666854[49] = 0;
   out_8052217584016666854[50] = 0;
   out_8052217584016666854[51] = 0;
   out_8052217584016666854[52] = 0;
   out_8052217584016666854[53] = 0;
}
void h_10(double *state, double *unused, double *out_6900636003204482111) {
   out_6900636003204482111[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_6900636003204482111[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_6900636003204482111[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_2471496167978032264) {
   out_2471496167978032264[0] = 0;
   out_2471496167978032264[1] = 9.8100000000000005*cos(state[1]);
   out_2471496167978032264[2] = 0;
   out_2471496167978032264[3] = 0;
   out_2471496167978032264[4] = -state[8];
   out_2471496167978032264[5] = state[7];
   out_2471496167978032264[6] = 0;
   out_2471496167978032264[7] = state[5];
   out_2471496167978032264[8] = -state[4];
   out_2471496167978032264[9] = 0;
   out_2471496167978032264[10] = 0;
   out_2471496167978032264[11] = 0;
   out_2471496167978032264[12] = 1;
   out_2471496167978032264[13] = 0;
   out_2471496167978032264[14] = 0;
   out_2471496167978032264[15] = 1;
   out_2471496167978032264[16] = 0;
   out_2471496167978032264[17] = 0;
   out_2471496167978032264[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_2471496167978032264[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_2471496167978032264[20] = 0;
   out_2471496167978032264[21] = state[8];
   out_2471496167978032264[22] = 0;
   out_2471496167978032264[23] = -state[6];
   out_2471496167978032264[24] = -state[5];
   out_2471496167978032264[25] = 0;
   out_2471496167978032264[26] = state[3];
   out_2471496167978032264[27] = 0;
   out_2471496167978032264[28] = 0;
   out_2471496167978032264[29] = 0;
   out_2471496167978032264[30] = 0;
   out_2471496167978032264[31] = 1;
   out_2471496167978032264[32] = 0;
   out_2471496167978032264[33] = 0;
   out_2471496167978032264[34] = 1;
   out_2471496167978032264[35] = 0;
   out_2471496167978032264[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_2471496167978032264[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_2471496167978032264[38] = 0;
   out_2471496167978032264[39] = -state[7];
   out_2471496167978032264[40] = state[6];
   out_2471496167978032264[41] = 0;
   out_2471496167978032264[42] = state[4];
   out_2471496167978032264[43] = -state[3];
   out_2471496167978032264[44] = 0;
   out_2471496167978032264[45] = 0;
   out_2471496167978032264[46] = 0;
   out_2471496167978032264[47] = 0;
   out_2471496167978032264[48] = 0;
   out_2471496167978032264[49] = 0;
   out_2471496167978032264[50] = 1;
   out_2471496167978032264[51] = 0;
   out_2471496167978032264[52] = 0;
   out_2471496167978032264[53] = 1;
}
void h_13(double *state, double *unused, double *out_4045300312263703588) {
   out_4045300312263703588[0] = state[3];
   out_4045300312263703588[1] = state[4];
   out_4045300312263703588[2] = state[5];
}
void H_13(double *state, double *unused, double *out_7182252664360551961) {
   out_7182252664360551961[0] = 0;
   out_7182252664360551961[1] = 0;
   out_7182252664360551961[2] = 0;
   out_7182252664360551961[3] = 1;
   out_7182252664360551961[4] = 0;
   out_7182252664360551961[5] = 0;
   out_7182252664360551961[6] = 0;
   out_7182252664360551961[7] = 0;
   out_7182252664360551961[8] = 0;
   out_7182252664360551961[9] = 0;
   out_7182252664360551961[10] = 0;
   out_7182252664360551961[11] = 0;
   out_7182252664360551961[12] = 0;
   out_7182252664360551961[13] = 0;
   out_7182252664360551961[14] = 0;
   out_7182252664360551961[15] = 0;
   out_7182252664360551961[16] = 0;
   out_7182252664360551961[17] = 0;
   out_7182252664360551961[18] = 0;
   out_7182252664360551961[19] = 0;
   out_7182252664360551961[20] = 0;
   out_7182252664360551961[21] = 0;
   out_7182252664360551961[22] = 1;
   out_7182252664360551961[23] = 0;
   out_7182252664360551961[24] = 0;
   out_7182252664360551961[25] = 0;
   out_7182252664360551961[26] = 0;
   out_7182252664360551961[27] = 0;
   out_7182252664360551961[28] = 0;
   out_7182252664360551961[29] = 0;
   out_7182252664360551961[30] = 0;
   out_7182252664360551961[31] = 0;
   out_7182252664360551961[32] = 0;
   out_7182252664360551961[33] = 0;
   out_7182252664360551961[34] = 0;
   out_7182252664360551961[35] = 0;
   out_7182252664360551961[36] = 0;
   out_7182252664360551961[37] = 0;
   out_7182252664360551961[38] = 0;
   out_7182252664360551961[39] = 0;
   out_7182252664360551961[40] = 0;
   out_7182252664360551961[41] = 1;
   out_7182252664360551961[42] = 0;
   out_7182252664360551961[43] = 0;
   out_7182252664360551961[44] = 0;
   out_7182252664360551961[45] = 0;
   out_7182252664360551961[46] = 0;
   out_7182252664360551961[47] = 0;
   out_7182252664360551961[48] = 0;
   out_7182252664360551961[49] = 0;
   out_7182252664360551961[50] = 0;
   out_7182252664360551961[51] = 0;
   out_7182252664360551961[52] = 0;
   out_7182252664360551961[53] = 0;
}
void h_14(double *state, double *unused, double *out_7165376589744331811) {
   out_7165376589744331811[0] = state[6];
   out_7165376589744331811[1] = state[7];
   out_7165376589744331811[2] = state[8];
}
void H_14(double *state, double *unused, double *out_7617101057371783255) {
   out_7617101057371783255[0] = 0;
   out_7617101057371783255[1] = 0;
   out_7617101057371783255[2] = 0;
   out_7617101057371783255[3] = 0;
   out_7617101057371783255[4] = 0;
   out_7617101057371783255[5] = 0;
   out_7617101057371783255[6] = 1;
   out_7617101057371783255[7] = 0;
   out_7617101057371783255[8] = 0;
   out_7617101057371783255[9] = 0;
   out_7617101057371783255[10] = 0;
   out_7617101057371783255[11] = 0;
   out_7617101057371783255[12] = 0;
   out_7617101057371783255[13] = 0;
   out_7617101057371783255[14] = 0;
   out_7617101057371783255[15] = 0;
   out_7617101057371783255[16] = 0;
   out_7617101057371783255[17] = 0;
   out_7617101057371783255[18] = 0;
   out_7617101057371783255[19] = 0;
   out_7617101057371783255[20] = 0;
   out_7617101057371783255[21] = 0;
   out_7617101057371783255[22] = 0;
   out_7617101057371783255[23] = 0;
   out_7617101057371783255[24] = 0;
   out_7617101057371783255[25] = 1;
   out_7617101057371783255[26] = 0;
   out_7617101057371783255[27] = 0;
   out_7617101057371783255[28] = 0;
   out_7617101057371783255[29] = 0;
   out_7617101057371783255[30] = 0;
   out_7617101057371783255[31] = 0;
   out_7617101057371783255[32] = 0;
   out_7617101057371783255[33] = 0;
   out_7617101057371783255[34] = 0;
   out_7617101057371783255[35] = 0;
   out_7617101057371783255[36] = 0;
   out_7617101057371783255[37] = 0;
   out_7617101057371783255[38] = 0;
   out_7617101057371783255[39] = 0;
   out_7617101057371783255[40] = 0;
   out_7617101057371783255[41] = 0;
   out_7617101057371783255[42] = 0;
   out_7617101057371783255[43] = 0;
   out_7617101057371783255[44] = 1;
   out_7617101057371783255[45] = 0;
   out_7617101057371783255[46] = 0;
   out_7617101057371783255[47] = 0;
   out_7617101057371783255[48] = 0;
   out_7617101057371783255[49] = 0;
   out_7617101057371783255[50] = 0;
   out_7617101057371783255[51] = 0;
   out_7617101057371783255[52] = 0;
   out_7617101057371783255[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8102601374041299900) {
  err_fun(nom_x, delta_x, out_8102601374041299900);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3419876428506429302) {
  inv_err_fun(nom_x, true_x, out_3419876428506429302);
}
void pose_H_mod_fun(double *state, double *out_4546444682940926041) {
  H_mod_fun(state, out_4546444682940926041);
}
void pose_f_fun(double *state, double dt, double *out_1236460484987931538) {
  f_fun(state,  dt, out_1236460484987931538);
}
void pose_F_fun(double *state, double dt, double *out_7321518554926371343) {
  F_fun(state,  dt, out_7321518554926371343);
}
void pose_h_4(double *state, double *unused, double *out_6863588878347655231) {
  h_4(state, unused, out_6863588878347655231);
}
void pose_H_4(double *state, double *unused, double *out_8052217584016666854) {
  H_4(state, unused, out_8052217584016666854);
}
void pose_h_10(double *state, double *unused, double *out_6900636003204482111) {
  h_10(state, unused, out_6900636003204482111);
}
void pose_H_10(double *state, double *unused, double *out_2471496167978032264) {
  H_10(state, unused, out_2471496167978032264);
}
void pose_h_13(double *state, double *unused, double *out_4045300312263703588) {
  h_13(state, unused, out_4045300312263703588);
}
void pose_H_13(double *state, double *unused, double *out_7182252664360551961) {
  H_13(state, unused, out_7182252664360551961);
}
void pose_h_14(double *state, double *unused, double *out_7165376589744331811) {
  h_14(state, unused, out_7165376589744331811);
}
void pose_H_14(double *state, double *unused, double *out_7617101057371783255) {
  H_14(state, unused, out_7617101057371783255);
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
