# -*- coding: utf-8 -*-
"""
Created on Wed Apr 30 13:24:17 2025

@author: yberton

Class of the evaporator
"""

# Imports
from math import pi, log
from flowStudy.thermodynamics import H, Psat, Tsat, rho, nu, Hl, Hv, Cp
from jouleHeatingSystems.current_passage_tube import CurrentPassageTube
from flowStudy.flow import G,Re 
from flowStudy.surface_finishes import f_blasius
import pandas as pd
import numpy as np

class Evaporator(CurrentPassageTube):
    
    def __init__(self,n:int,dL_clamps=125E-3,L_clamp_up=90E-3,L=270E-3, CHF = 10 - 1E-2):
        
        #Tube
        self.name = 'TS'
        self.n = n # Tube's number
        self.L = L # Tubes'length
        self.dL_clamps = dL_clamps # Distance between clamps
        self.L_clamp_up = L_clamp_up # Distance until the upstream clamp
        self.L_clamp_ds = self.L_clamp_up + self.dL_clamps # Distance to the downstream clamp
        self.rint = 1E-3 #m
        self.dint = self.rint*2 #m
        self.rext = 3E-3 #m
        self.dext = self.rext*2 #m
        self.Sint = 2*pi*self.L*self.rint #m²
        self.Sin_clamps = 2*pi*self.dL_clamps*self.rint #m²
        self.Sext = 2*pi*self.L*self.rext #m²
        self.Aint = pi*self.rint**2 #m²
        self.Aext = pi*self.rext**2 #m²
        self.V = self.Aint * self.L #m3
        self.LD = self.L/(self.rint*2)
        self.Lrf = self.L/self.rint
        self.z = {'1':40E-3, '2':62.5E-3, '3':85E-3, 'CHF':CHF}
        self.coeffs = [35.38864688, 0.79727201]
        self.roughness()
        self.add_funs()

    def add_funs(self):
        
        self.f_pow_ratio =lambda dt,Pelec : (1/(0.06325581772940454 - 1.149104767178758868))*(+(dt)/(Pelec) - 1.149104767178758868)
        self.f_Twall_in_z = lambda Two,qeff_TS : Two + qeff_TS/(16*13.4)*(self.dext**2 - self.dint**2) - qeff_TS*self.dext**2/(8*13.4)*log(self.dext/self.dint)
        self.nloss_mono = lambda h : self.coeffs[0]*h**(-self.coeffs[1])
        self.Pz = lambda dP_meas, dP_mono, Pin, z : (Pin - dP_mono) - ( (dP_meas - dP_mono)/(self.L) * (z + self.L_clamp_up))   
        
    def roughness(self):
        
        match self.n :
            
            case 11 : 
                self.Ra = 4.220689848*1E-6 # [-]
                
    def pow_ratio(self,dt,Pelec):
        return(self.f_pow_ratio(dt,Pelec))

        
    def pz_subcooled(self,dP,Pin,z):
        []
        
    def HTC_1f(self):
        
        if len(self.df) == 0 : raise NameError('No experimental data ')
        
        df_all = self.df
        
        #Mean temperatures of the test section
        df_all[r'Tfl_TS_mean [°C]'] = (df_all['218 - E_out_imm [°C]'] - df_all["202 - E_in_imm [°C]"])/2
        df_all[r'dT_amb_TS [°C]'] = df_all[r'Tfl_TS_mean [°C]'] - df_all['230 - Ambiant [°C]']
    
        #Thermal power TS
        df_all['I_in_TS [J/kg]'] = H( df_all['115 - P_reservoir [bars]'].values*1e5, df_all["202 - E_in_imm [°C]"].values+273.15, 'R245fa')
        df_all['I_out_TS [J/kg]'] = H(df_all['118 - P_TS_in [bars]'].values*1e5, df_all['218 - E_out_imm [°C]'].values+273.15, 'R245fa')
        df_all['Pth_TS [W]'] = df_all['105 - mass [kg/s]']*(df_all['I_out_TS [J/kg]'] - df_all['I_in_TS [J/kg]'])
        df_all['q"th [W/m2]'] = df_all['Pth_TS [W]']/self.Sin_clamps
    
        # Inner wall temperatures
        #First TC
        df_all['E1_in_bot [°C]'] = self.Twiz(df_all['206 - E_1_bot [°C]'],df_all['q"th [W/m2]'])
        df_all['E1_in_mid [°C]'] = self.Twiz(df_all['207 - E_1_mid [°C]'],df_all['q"th [W/m2]'])
        df_all['E1_in_top [°C]'] = self.Twiz(df_all['208 - E_1_top [°C]'],df_all['q"th [W/m2]'])
        df_all['Tw1_TS [°C]'] = (df_all['E1_in_bot [°C]'] + 2*df_all['E1_in_mid [°C]'])/3
        
        #Second TC
        df_all['E2_in_bot [°C]'] = self.Twiz(df_all['209 - E_2_bot [°C]'],df_all['q"th [W/m2]'])
        df_all['E2_in_mid [°C]'] = self.Twiz(df_all['210 - E_2_mid [°C]'],df_all['q"th [W/m2]'])
        df_all['E2_in_top [°C]'] = self.Twiz(df_all['212 - E_2_top [°C]'],df_all['q"th [W/m2]'])
        df_all['Tw2_TS [°C]'] = (df_all['E2_in_bot [°C]'] + 2*df_all['E2_in_mid [°C]'] + df_all['E2_in_top [°C]'])/4
        
        #Third TC
        df_all['E3_in_bot [°C]'] = self.Twiz(df_all['213 - E_3_bot [°C]'],df_all['q"th [W/m2]'])
        df_all['E3_in_mid [°C]'] = self.Twiz(df_all['214 - E_3_mid [°C]'],df_all['q"th [W/m2]'])
        df_all['E3_in_top [°C]'] = self.Twiz(df_all['215 - E_3_top [°C]'],df_all['q"th [W/m2]'])
        df_all['Tw3_TS [°C]'] = (df_all['E3_in_bot [°C]'] + 2*df_all['E3_in_mid [°C]'] + df_all['E3_in_top [°C]'])/4
    
        df_all['Cp_TS_mean [J/kg/k]'] = Cp( df_all["118 - P_TS_in [bars]"].values*1e5, df_all[r'Tfl_TS_mean [°C]'], 'R245fa')
        df_all['Tfl1_TS [°C]'] = self.Tflz_1f(df_all["202 - E_in_imm [°C]"],
                                         df_all['Cp_TS_mean [J/kg/k]'] ,
                                         df_all['q"th [W/m2]'], self.z['1'],
                                         df_all['105 - mass [kg/s]'])
    
        df_all['Tfl2_TS [°C]'] = self.Tflz_1f(df_all["202 - E_in_imm [°C]"],
                                         df_all['Cp_TS_mean [J/kg/k]'] ,
                                         df_all['q"th [W/m2]'], self.z['2'],
                                         df_all['105 - mass [kg/s]'])
    
        df_all['Tfl3_TS [°C]'] = self.Tflz_1f(df_all["202 - E_in_imm [°C]"],
                                         df_all['Cp_TS_mean [J/kg/k]'] ,
                                         df_all['q"th [W/m2]'], self.z['3'],
                                         df_all['105 - mass [kg/s]'])
    
        #HTC calculation
        df_all['h1_TS [W/m/K]'] = df_all['q"th [W/m2]']/(df_all['Tw1_TS [°C]'] - df_all['Tfl1_TS [°C]'])
        df_all['h2_TS [W/m/K]'] = df_all['q"th [W/m2]']/(df_all['Tw2_TS [°C]'] - df_all['Tfl2_TS [°C]'])
        df_all['h3_TS [W/m/K]'] = df_all['q"th [W/m2]']/(df_all['Tw3_TS [°C]'] - df_all['Tfl3_TS [°C]'])
        df_all['h_TS_mean [W/m/K]'] = (df_all['h1_TS [W/m/K]'] + df_all['h2_TS [W/m/K]'] + df_all['h3_TS [W/m/K]'])/3
        df_all['nloss'] = (df_all['P_el_TS (W)'] - df_all['Pth_TS [W]'])/df_all['P_el_TS (W)']

        self.df = df_all
        
    def Twi_mean(self, serie, qth):
        
        # Inner wall temperatures
        #First TC
        serie['E1_in_bot [°C]'] = self.Twiz(serie['206 - E_1_bot [°C]'],qth)
        serie['E1_in_mid [°C]'] = self.Twiz(serie['207 - E_1_mid [°C]'],qth)
        serie['E1_in_top [°C]'] = self.Twiz(serie['208 - E_1_top [°C]'],qth)
        serie['Tw1_TS [°C]'] = (serie['E1_in_bot [°C]'] + 2*serie['E1_in_mid [°C]'])/3
        
        #Second TC
        serie['E2_in_bot [°C]'] = self.Twiz(serie['209 - E_2_bot [°C]'],qth)
        serie['E2_in_mid [°C]'] = self.Twiz(serie['210 - E_2_mid [°C]'],qth)
        serie['E2_in_top [°C]'] = self.Twiz(serie['212 - E_2_top [°C]'],qth)
        serie['Tw2_TS [°C]'] = (serie['E2_in_bot [°C]'] + 2*serie['E2_in_mid [°C]'] + serie['E2_in_top [°C]'])/4
        
        #Third TC
        serie['E3_in_bot [°C]'] = self.Twiz(serie['213 - E_3_bot [°C]'],qth)
        serie['E3_in_mid [°C]'] = self.Twiz(serie['214 - E_3_mid [°C]'],qth)
        serie['E3_in_top [°C]'] = self.Twiz(serie['215 - E_3_top [°C]'],qth)
        serie['Tw3_TS [°C]'] = (serie['E3_in_bot [°C]'] + 2*serie['E3_in_mid [°C]'] + serie['E3_in_top [°C]'])/4
        
        serie['Tw_TS_mean [°C]'] = (serie['Tw1_TS [°C]'] + serie['Tw2_TS [°C]'] + serie['Tw3_TS [°C]'])/3
        
        return serie 
    
    def Tf_mean_1f(self):
        
        self.df['Tfl1_TS [°C]'] = self.Tflz(self.df["202 - E_in_imm [°C]"],
                                         self.df['Cp_TS_mean [J/kg/k]'] ,
                                         self.df['qth_eff  [W/m²]'], self.z['1'],
                                         self.df['105 - mass [kg/s]'])
    
        self.df['Tfl2_TS [°C]'] = self.Tflz(self.df["202 - E_in_imm [°C]"],
                                         self.df['Cp_TS_mean [J/kg/k]'] ,
                                         self.df['qth_eff  [W/m²]'], self.z['2'],
                                         self.df['105 - mass [kg/s]'])
    
        self.df['Tfl3_TS [°C]'] = self.Tflz(self.df["202 - E_in_imm [°C]"],
                                         self.df['Cp_TS_mean [J/kg/k]'] ,
                                         self.df['qth_eff  [W/m²]'], self.z['3'],
                                         self.df['105 - mass [kg/s]'])
    
    def Tf_mean_2f(self, serie, qth):
        
        serie['Tfl1_TS [°C]'] = self.Tflz(serie["202 - E_in_imm [°C]"],
                                         serie['Cp_TS_mean [J/kg/k]'] ,
                                         qth, self.z['1'],
                                         serie['105 - mass [kg/s]'])
    
        serie['Tfl2_TS [°C]'] = self.Tflz(serie["202 - E_in_imm [°C]"],
                                         serie['Cp_TS_mean [J/kg/k]'] ,
                                         qth, self.z['2'],
                                         serie['105 - mass [kg/s]'])
    
        serie['Tfl3_TS [°C]'] = self.Tflz(serie["202 - E_in_imm [°C]"],
                                         serie['Cp_TS_mean [J/kg/k]'] ,
                                         qth, self.z['3'],
                                         serie['105 - mass [kg/s]'])
        return serie
    
    def h_mean(self,serie):
        
        serie['h1_TS [W/m/K]'] = serie['q"th [W/m2]']/(serie['Tw1_TS [°C]'] - serie['Tfl1_TS [°C]'])
        serie['h2_TS [W/m/K]'] = serie['q"th [W/m2]']/(serie['Tw2_TS [°C]'] - serie['Tfl2_TS [°C]'])
        serie['h3_TS [W/m/K]'] = serie['q"th [W/m2]']/(serie['Tw3_TS [°C]'] - serie['Tfl3_TS [°C]'])
        serie['h_TS_mean [W/m/K]'] = (serie['h1_TS [W/m/K]'] + serie['h2_TS [W/m/K]'] + serie['h3_TS [W/m/K]'])/3
        return serie
    
    def nloss_2f(self):
        
        self.df['P_trans_TS (W)'] = (1-0.15)*self.df['P_el_TS (W)']
            
        #Mean temperature for the test section 
        self.df['qeff_TS [W/m^2]'] = self.df['P_trans_TS (W)']/self.Sin_clamps

        #Calculate some thermodynamical proprieties
        self.df[r'$Rho_{TS,in}$ [$m^3$/$kg$]'] = rho(self.df['118 - P_TS_in [bars]'].values*1e5, self.df["202 - E_in_imm [°C]"].values + 273.15,"R245fa")
        self.df['nu'] = nu(self.df["118 - P_TS_in [bars]"].values*1E5, self.df['218 - E_out_imm [°C]'].values + 273.15, "R245fa")
        self.df['Re [-]'] = Re(self.df['G (kg/m²/s)'].values,self.dint,self.df['nu'].values)
        self.df[r'$v$ $[m/s]$'] = self.df['105 - mass [kg/s]'].values/self.df[r'$Rho_{TS,in}$ [$m^3$/$kg$]'].values/self.Sint
        self.df['Cp_TS_mean [J/kg/k]'] = Cp( self.df["118 - P_TS_in [bars]"].values*1e5, self.df[r'Tfl_TS_mean [°C]'] + 273.15, 'R245fa')
            
        #Calculate pressure drop
        self.df[r'$f$ $[-]$'] = f_blasius(self.df['Re [-]'].values)
        self.df[r'dP mono [Pa]'] =  self.df[r'$Rho_{TS,in}$ [$m^3$/$kg$]']*self.df[r'$f$ $[-]$']*self.L_clamp_up/self.dint/2*self.df[r'$v$ $[m/s]$']**2

        #First TC
        self.df['E1_in_bot [°C]'] = self.Twiz(self.df['206 - E_1_bot [°C]'],self.df['qeff_TS [W/m^2]'])
        self.df['E1_in_mid [°C]'] = self.Twiz(self.df['207 - E_1_mid [°C]'],self.df['qeff_TS [W/m^2]'])
        self.df['E1_in_top [°C]'] = self.Twiz(self.df['208 - E_1_top [°C]'],self.df['qeff_TS [W/m^2]'])
        self.df['Twi_1 [°C]'] = (self.df['E1_in_bot [°C]'] + self.df['E1_in_mid [°C]'] + self.df['E1_in_top [°C]'] )/3

        #Second TC
        self.df['E2_in_bot [°C]'] = self.Twiz(self.df['209 - E_2_bot [°C]'],self.df['qeff_TS [W/m^2]'])
        self.df['E2_in_mid [°C]'] = self.Twiz(self.df['210 - E_2_mid [°C]'],self.df['qeff_TS [W/m^2]'])
        self.df['E2_in_top [°C]'] = self.Twiz(self.df['212 - E_2_top [°C]'],self.df['qeff_TS [W/m^2]'])
        self.df['Twi_2 [°C]'] = (self.df['E2_in_bot [°C]'] + self.df['E2_in_mid [°C]'])/2

        #Third TC
        self.df['E3_in_bot [°C]'] = self.Twiz(self.df['213 - E_3_bot [°C]'],self.df['qeff_TS [W/m^2]'])
        self.df['E3_in_mid [°C]'] = self.Twiz(self.df['214 - E_3_mid [°C]'],self.df['qeff_TS [W/m^2]'])
        self.df['E3_in_top [°C]'] = self.Twiz(self.df['215 - E_3_top [°C]'],self.df['qeff_TS [W/m^2]'])
        self.df['Twi_3 [°C]'] = (self.df['E3_in_bot [°C]'] + self.df['E3_in_mid [°C]'] + self.df['E3_in_top [°C]'])/3

        #Let's find ONB
        L_ONB = []
        for j in range(len(self.df)):
            if self.df['subcooled'].iloc[j] :
                z = 0
                Tfz = self.Tflz_1f(self.df["202 - E_in_imm [°C]"].iloc[j],
                                                             self.df['Cp_TS_mean [J/kg/k]'].iloc[j] ,
                                                             self.df['qeff_TS [W/m^2]'].iloc[j], 0,
                                                             self.df['105 - mass [kg/s]'].iloc[j])
                    
                Tsatz = Tsat(self.Pz(self.df['dP_TS [mbars]'].iloc[j]*1E2,
                            self.df[r'dP mono [Pa]'].iloc[j], self.df['118 - P_TS_in [bars]'].iloc[j]*1e5, 0),"R245fa") - 273.15
                while Tsatz - Tfz > 0 :
                    
                    z+=0.001
                    Tfz = self.Tflz_1f(self.df["202 - E_in_imm [°C]"].iloc[j],
                                                             self.df['Cp_TS_mean [J/kg/k]'].iloc[j] ,
                                                             self.df['qeff_TS [W/m^2]'].iloc[j], z,
                                                             self.df['105 - mass [kg/s]'].iloc[j])
                    Tsatz = Tsat(self.Pz(self.df['dP_TS [mbars]'].iloc[j]*1E2,
                            self.df[r'dP mono [Pa]'].iloc[j], self.df['118 - P_TS_in [bars]'].iloc[j]*1e5, z),"R245fa") - 273.15
            
                if z > self.dL_clamps : 
                    z = 'Monophasic'
                L_ONB.append(z)
            
            else : L_ONB.append('pre-evaporated')

        self.df['ONB [m]'] = L_ONB

        #Calculate the fluid temperature at the zi
        self.df['Tf1 [°C]'] = self.df['Tf2 [°C]'] = self.df['Tf3 [°C]'] = pd.Series(np.nan,self.df.index)
        for j in range(len(self.df)):
            if isinstance(self.df['ONB [m]'].iloc[j],float) :
                for i in self.z : 
                    
                    if self.z[i] < self.df['ONB [m]'].iloc[j] : 
                        self.df.iloc[j, -4 + int(i)] = self.Tflz_1f(self.df["202 - E_in_imm [°C]"].iloc[j],
                                                                 self.df['Cp_TS_mean [J/kg/k]'].iloc[j] ,
                                                                 self.df['qeff_TS [W/m^2]'].iloc[j], self.z[i],
                                                                 self.df['105 - mass [kg/s]'].iloc[j])
                    else : 
                        self.df.iloc[j, -4 + int(i)] = Tsat(self.Pz(self.df['dP_TS [mbars]'].iloc[j]*1E2,
                                self.df[r'dP mono [Pa]'].iloc[j], self.df['118 - P_TS_in [bars]'].iloc[j]*1e5, self.z[i]),"R245fa") - 273.15
            else :
                for i in self.z : 
                    string = 'Tf' + str(i) + ' [°C]'
                    self.df.iloc[j, -4 + int(i)] = Tsat(self.Pz(self.df['dP_TS [mbars]'].iloc[j]*1E2,
                            self.df[r'dP mono [Pa]'].iloc[j], self.df['118 - P_TS_in [bars]'].iloc[j]*1e5, self.z[i]),"R245fa") - 273.15

        # h (heat transfer coefficient) calculus
        self.df['h1 [W/m/K]'] = self.df['qeff_TS [W/m^2]']/(self.df['Twi_1 [°C]'] - self.df['Tf1 [°C]'])
        self.df['h2 [W/m/K]'] = self.df['qeff_TS [W/m^2]']/(self.df['Twi_2 [°C]'] - self.df['Tf2 [°C]'])
        self.df['h3 [W/m/K]'] = self.df['qeff_TS [W/m^2]']/(self.df['Twi_3 [°C]'] - self.df['Tf3 [°C]'])

        # x : vapor fraction calculus
        self.df['I_out_TS [J/kg]'] = self.df['I_out_PH [J/kg]'] + self.df['P_trans_TS (W)']/self.df['105 - mass [kg/s]']
        self.df['Il_in_TS [J/kg]'] = Hl(self.df['118 - P_TS_in [bars]'].values*1E5, 'R245fa')
        self.df['Iv_out_TS [J/kg]'] = Hv(self.df['114 - P_TS_out [bars]'].values*1E5, 'R245fa')

        self.df['I_TS_z1 [J/kg]'] = self.df['I_out_PH [J/kg]'] + self.df['P_trans_TS (W)']/self.df['105 - mass [kg/s]']/self.dL_clamps*self.z['1']
        self.df['I_TS_z2 [J/kg]'] = self.df['I_out_PH [J/kg]'] + self.df['P_trans_TS (W)']/self.df['105 - mass [kg/s]']/self.dL_clamps*self.z['2']
        self.df['I_TS_z3 [J/kg]'] = self.df['I_out_PH [J/kg]'] + self.df['P_trans_TS (W)']/self.df['105 - mass [kg/s]']/self.dL_clamps*self.z['3']

        self.df['x1 [-]'] = (self.df['I_TS_z1 [J/kg]'] - self.df['Il_in_TS [J/kg]'])/(self.df['Iv_out_TS [J/kg]'] - self.df['Il_in_TS [J/kg]']).mask(
            self.df['I_TS_z1 [J/kg]'] - self.df['Il_in_TS [J/kg]'] < 0, 0)
        self.df['x2 [-]'] = (self.df['I_TS_z2 [J/kg]'] - self.df['Il_in_TS [J/kg]'])/(self.df['Iv_out_TS [J/kg]'] - self.df['Il_in_TS [J/kg]']).mask(
            self.df['I_TS_z2 [J/kg]'] - self.df['Il_in_TS [J/kg]'] < 0, 0)
        self.df['x3 [-]'] = (self.df['I_TS_z3 [J/kg]'] - self.df['Il_in_TS [J/kg]'])/(self.df['Iv_out_TS [J/kg]'] - self.df['Il_in_TS [J/kg]']).mask(
            self.df['I_TS_z3 [J/kg]'] - self.df['Il_in_TS [J/kg]'] < 0, 0)

        self.df['x_out_TS [-]'] = (self.df['I_out_TS [J/kg]'] - self.df['Il_in_TS [J/kg]'])/(self.df['Iv_out_TS [J/kg]'] - self.df['Il_in_TS [J/kg]']).mask(
            self.df['I_out_TS [J/kg]'] - self.df['Il_in_TS [J/kg]'] < 0, 0)
        
    #def phi_th(self, hc, hinf, Tsat, Tinf, )

if __name__ == "__main__":
    evap = Evaporator(11)
    
