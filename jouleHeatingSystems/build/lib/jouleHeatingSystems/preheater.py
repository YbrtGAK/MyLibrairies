
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 30 13:24:17 2025

@author: yberton

Class of the preheater
"""

# Imports
from math import pi, log
from jouleHeatingSystems.current_passage_tube import CurrentPassageTube
from flowStudy.thermodynamics import H, Psat, Tsat, rho, nu, Hl, Hv, Cp
from flowStudy.flow import G,Re 
import pandas as pd
import numpy as np

class Preheater(CurrentPassageTube):
    
    def __init__(self):
        
        CurrentPassageTube.__init__(self)
        
        #Tube
        self.name = 'PH'
        self.L_clamp_up = 0 #m
        self.L = 1.910 #m
        self.Sin_clamps = self.L
        self.rint = 1.5E-3 #m
        self.dint = self.rint*2 #m
        self.rext = 3E-3 #m
        self.dext = self.rext*2 #m
        self.Sint = 2*pi*self.L*self.rint #m²
        self.Sext = 2*pi*self.L*self.rext #m²
        self.Aint = pi*self.rint**2 #m²
        self.Aext = pi*self.rext**2 #m²
        self.V = self.Aint * self.L #m3
        self.LD = self.L/(self.rint*2)
        self.Lrf = self.L/self.rint
        self.z = {'1':665E-3, '2':809E-3, '3':1347E-3, '4':1585E-3}
        self.coeffs = [135.32645789,1.03232876]
        self.add_funs()
        
        
    def add_funs(self):
        self.f_pow_ratio = lambda dt,Pelec : (1/(0.7579189998726281 + 8.999334418324721696))*(-(dt)/(Pelec) + 8.999334418324721696)
        self.nloss_mono = lambda h : self.coeffs[0]*h**(-self.coeffs[1])
        self.Pz = lambda dP_meas, dP_mono, Pin, z : (Pin - dP_mono) - ( (dP_meas - dP_mono)/(self.L) * (z + self.L_clamp_up))   
        
    def Twi_mean(self, qth):
        
        #Inner wall temperatures calculus
        #First TC
        self.df['Tw1_PH [°C]'] = self.Twiz(self.df['226 -  PH1 [°C]'], qth)
        self.df['Tw2_PH [°C]'] = self.Twiz(self.df['227 - PH2 [°C]'], qth)
        self.df['Tw3_PH [°C]'] = self.Twiz(self.df['228 - PH3 [°C]'], qth)
        self.df['Tw4_PH [°C]'] = self.Twiz(self.df['229 - PH4 [°C]'], qth)
        self.df['Tw_mean_PH [°C]'] = (self.df['Tw1_PH [°C]'] + self.df['Tw2_PH [°C]'] + self.df['Tw3_PH [°C]'] + self.df['Tw4_PH [°C]'])/4
    
    ###########################################################################
    #                          Single-phase calculus                          #
    ###########################################################################
        
    def HTC_1f(self):
        
        if len(self.df) == 0 : raise NameError('No experimental data ')
        
        self.df = self.df
        
        #Calculate some thermodynamical proprieties
        self.df[r'$Rho_{TS,in}$ [$m^3$/$kg$]'] = rho(self.df['118 - P_TS_in [bars]'].values*1e5, self.df["202 - E_in_imm [°C]"].values + 273.15,"R245fa")
        self.df['nu'] = nu(self.df["118 - P_TS_in [bars]"].values*1E5, self.df['218 - E_out_imm [°C]'].values + 273.15, "R245fa")
        self.df['Re [-]'] = Re(self.df['G (kg/m²/s)'].values,self.dint,self.df['nu'].values)
        self.df[r'$v$ $[m/s]$'] = self.df['105 - mass [kg/s]'].values/self.df[r'$Rho_{TS,in}$ [$m^3$/$kg$]'].values/self.Sint
        
        #Mean temperatures of the preheater
        self.df[r'Tfl_PH_mean [°C]'] = (self.df["224 - PH_inlet_imm [°C]"] + self.df["202 - E_in_imm [°C]"])/2
        self.df['Two_PH_mean [°C]'] = (self.df['226 -  PH1 [°C]'] + self.df['227 - PH2 [°C]'] + self.df['228 - PH3 [°C]'] + self.df['229 - PH4 [°C]'])/4
        self.df[r'dT_amb_PH [°C]'] = self.df['Two_PH_mean [°C]'] - self.df['230 - Ambiant [°C]']
    
        #Thermal power preheater
        self.df['I_in_PH [J/kg]'] = H(self.df['115 - P_reservoir [bars]'].values*1e5, self.df["224 - PH_inlet_imm [°C]"].values +273.15, 'R245fa')
        self.df['I_out_PH [J/kg]'] = H(self.df['118 - P_TS_in [bars]'].values*1e5, self.df['202 - E_in_imm [°C]'].values + 273.15, 'R245fa')
        self.df['Pth_PH_1f [W]'] = self.df['105 - mass [kg/s]']*(self.df['I_out_PH [J/kg]'] - self.df['I_in_PH [J/kg]'])
        self.df['qeff_PH [W/m^2]'] = self.df['Pth_PH_1f [W]']/self.Sint
    
        # Inner wall temperatures
        self.df['Tw1_PH [°C]'] = self.Twiz(self.df['226 -  PH1 [°C]'], self.df['qeff_PH [W/m^2]'])
        self.df['Tw2_PH [°C]'] = self.Twiz(self.df['227 - PH2 [°C]'], self.df['qeff_PH [W/m^2]'])
        self.df['Tw3_PH [°C]'] = self.Twiz(self.df['228 - PH3 [°C]'], self.df['qeff_PH [W/m^2]'])
        self.df['Tw4_PH [°C]'] = self.Twiz(self.df['229 - PH4 [°C]'], self.df['qeff_PH [W/m^2]'])
    
        # Fluid temperature (monophasic)
        z1 = 665E-3 ; z2 = 809E-3 ; z3 = 1347E-3 ; z4 = 1585E-3
    
        self.df['Cp_PH_mean [J/kg/k]'] = Cp( self.df['115 - P_reservoir [bars]'].values*1e5, self.df[r'Tfl_PH_mean [°C]'], 'R245fa')
        self.df['Tfl1_PH [°C]'] = self.Tflz_1f(self.df["224 - PH_inlet_imm [°C]"],
                                         self.df['Cp_PH_mean [J/kg/k]'] ,
                                         self.df['qeff_PH [W/m^2]'], z1,
                                         self.df['105 - mass [kg/s]'])
    
        self.df['Tfl2_PH [°C]'] = self.Tflz_1f(self.df["224 - PH_inlet_imm [°C]"],
                                         self.df['Cp_PH_mean [J/kg/k]'] ,
                                         self.df['qeff_PH [W/m^2]'], z2,
                                         self.df['105 - mass [kg/s]'])
    
        self.df['Tfl3_PH [°C]'] = self.Tflz_1f(self.df["224 - PH_inlet_imm [°C]"],
                                         self.df['Cp_PH_mean [J/kg/k]'] ,
                                         self.df['qeff_PH [W/m^2]'], z3,
                                         self.df['105 - mass [kg/s]'])
    
        self.df['Tfl4_PH [°C]'] = self.Tflz_1f(self.df["224 - PH_inlet_imm [°C]"],
                                         self.df['Cp_PH_mean [J/kg/k]'] ,
                                         self.df['qeff_PH [W/m^2]'], z4,
                                         self.df['105 - mass [kg/s]'])
    
        #HTC calculation
    
        self.df['h1_PH [W/m²]'] = self.df['qeff_PH [W/m^2]']/(self.df['Tw1_PH [°C]'] - self.df['Tfl1_PH [°C]'])
        self.df['h2_PH [W/m²]'] = self.df['qeff_PH [W/m^2]']/(self.df['Tw2_PH [°C]'] - self.df['Tfl2_PH [°C]'])
        self.df['h3_PH [W/m²]'] = self.df['qeff_PH [W/m^2]']/(self.df['Tw3_PH [°C]'] - self.df['Tfl3_PH [°C]'])
        self.df['h4_PH [W/m²]'] = self.df['qeff_PH [W/m^2]']/(self.df['Tw4_PH [°C]'] - self.df['Tfl4_PH [°C]'])
        self.df['h_PH_mean [W/m²]'] = (self.df['h1_PH [W/m²]'] + self.df['h2_PH [W/m²]'] + self.df['h3_PH [W/m²]'] + self.df['h4_PH [W/m²]'])/4
        self.df['nloss_exp [-]'] = (self.df['P_el_PH (W)'] - self.df['Pth_PH_1f [W]'])/self.df['P_el_PH (W)']

        self.df = self.df
        
    def Tf_1f_mean(self):
        
        self.df['Tfl1_1f_PH [°C]'] = self.Tflz_1f(self.df["224 - PH_inlet_imm [°C]"],
                                         self.df['Cp_PH_mean [J/kg/k]'] ,
                                         self.df['qeff_PH [W/m^2]'], self.z['1'],
                                         self.df['105 - mass [kg/s]'])
    
        self.df['Tfl2_1f_PH [°C]'] = self.Tflz_1f(self.df["224 - PH_inlet_imm [°C]"],
                                         self.df['Cp_PH_mean [J/kg/k]'] ,
                                         self.df['qeff_PH [W/m^2]'], self.z['2'],
                                         self.df['105 - mass [kg/s]'])
    
        self.df['Tfl3_1f_PH [°C]'] = self.Tflz_1f(self.df["224 - PH_inlet_imm [°C]"],
                                         self.df['Cp_PH_mean [J/kg/k]'] ,
                                         self.df['qeff_PH [W/m^2]'], self.z['3'],
                                         self.df['105 - mass [kg/s]'])
    
        self.df['Tfl4_1f_PH [°C]'] = self.Tflz_1f(self.df["224 - PH_inlet_imm [°C]"],
                                         self.df['Cp_PH_mean [J/kg/k]'] ,
                                         self.df['qeff_PH [W/m^2]'], self.z['4'],
                                         self.df['105 - mass [kg/s]'])
        
        
    ###########################################################################
    #                            Two-phase calculus                           #
    ###########################################################################
    
    def nloss_2f(self):
        self.LSe = []
        
        for i in range(len(self.df)):
            Se = self.df.iloc[i]
            Se['nloss_2f'] = 0.1 #Initial guess of nloss value
            flag = [0,0] #2 steps flag condition : 2 successives nloss calculation have to end with a variation lower than 5%
            Se['Tfl1_PH [°C]'] = Se['Tfl2_PH [°C]'] = Se['Tfl3_PH [°C]'] = Se['Tfl4_PH [°C]'] = np.nan # Fixing Tfl NaN Value for initialization
            nb_iter = 0
            while flag[0] == 0 and flag[1] == 0: 
                    
                Se['P_trans_PH (W)'] = (1-Se['nloss_2f'])*Se['P_el_PH (W)'] #Transmitted power calculus
                Se['qeff_PH [W/m^2]'] =  Se['P_trans_PH (W)']/self.Sint #Transmitted heat flux calculus
                
                if str(Se['qeff_PH [W/m^2]']) == 'nan':
                    
                    print('Olala')
                    break
                
                #Fluid temperature calculus
                # Case : subcooled
                if Se['subcooled'] :
                    
                    Se['Tfl1_PH [°C]'] = self.Tflz_1f(Se["224 - PH_inlet_imm [°C]"],
                                                     Se['Cp_PH_mean [J/kg/k]'],
                                                     Se['qeff_PH [W/m^2]'], self.z['1'],
                                                     Se['105 - mass [kg/s]'])
                
                    Se['Tfl2_PH [°C]'] = self.Tflz_1f(Se["224 - PH_inlet_imm [°C]"],
                                                     Se['Cp_PH_mean [J/kg/k]'],
                                                     Se['qeff_PH [W/m^2]'], self.z['2'],
                                                     Se['105 - mass [kg/s]'])
                
                    Se['Tfl3_PH [°C]'] = self.Tflz_1f(Se["224 - PH_inlet_imm [°C]"],
                                                     Se['Cp_PH_mean [J/kg/k]'],
                                                     Se['qeff_PH [W/m^2]'], self.z['3'],
                                                     Se['105 - mass [kg/s]'])
                
                    Se['Tfl4_PH [°C]'] = self.Tflz_1f(Se["224 - PH_inlet_imm [°C]"],
                                                     Se['Cp_PH_mean [J/kg/k]'],
                                                     Se['qeff_PH [W/m^2]'], self.z['4'],
                                                     Se['105 - mass [kg/s]'])
                # Case : pre-evaporated
                #Let's find ONB
                else : 
                    z = 0
                    Tfz = self.Tflz_1f(Se["224 - PH_inlet_imm [°C]"],
                                       Se['Cp_PH_mean [J/kg/k]'] ,
                                       Se['qeff_PH [W/m^2]'], z,
                                       Se['105 - mass [kg/s]'])
                        
                    Tsatz = Tsat(self.Pz(Se['dP_PH [bars]']*1E5,
                                Se[r'dP_PH mono [Pa]'], Se['115 - P_reservoir [bars]']*1e5, 0),"R245fa") - 273.15
                    
                    while Tsatz - Tfz > 0 :
                        z+=0.001
                        Tfz = self.Tflz_1f(Se["224 - PH_inlet_imm [°C]"],
                                                                 Se['Cp_PH_mean [J/kg/k]'] ,
                                                                 Se['qeff_PH [W/m^2]'], z,
                                                                 Se['105 - mass [kg/s]'])
                        try :
                            Tsatz = Tsat(self.Pz(Se['dP_PH [bars]']*1E5,
                                    Se[r'dP_PH mono [Pa]'], Se['115 - P_reservoir [bars]']*1e5, z),"R245fa") - 273.15
                        except ValueError :
                            print(f"Se['118 - P_TS_in [bars]']*1e5 : {Se['118 - P_TS_in [bars]']*1e5} ; z = {z}")
                            Tsatz = Tsat(Se['118 - P_TS_in [bars]']*1e5,"R245fa")
                            
                        if z > self.L :
                            z = 'Monophasic'
                            break
        
                    # Now that the ONB has been found with a 0.001 m resolution, the fluid temperature for the different
                    # z locations have to be calculated accordingly.
                    # Case 1. As an increase of the temperature for the ones located before the ONB
                    # Case 2. As the variation of the saturated temperature with the pressure loss for those after
                    
                    Se['ONB [m]'] = z
                    
                    if isinstance(Se['ONB [m]'],float) :
                        for i in self.z :
                            #Case 1
                            if self.z[i] < Se['ONB [m]'] : 
                                Se['Tfl'+i+'_PH [°C]'] = self.Tflz_1f(Se["224 - PH_inlet_imm [°C]"],
                                                                         Se['Cp_PH_mean [J/kg/k]'] ,
                                                                         Se['qeff_PH [W/m^2]'], self.z[i],
                                                                         Se['105 - mass [kg/s]'])
                            #Case 2
                            else : 
                                Se['Tfl'+i+'_PH [°C]'] = Tsat(self.Pz(Se['dP_PH [bars]']*1E5,
                                        Se[r'dP_PH mono [Pa]'], Se['115 - P_reservoir [bars]']*1e5, self.z[i]),"R245fa") - 273.15
        
                # Twiz calculation
                Se['Tw1_PH [°C]'] = self.Twiz(Se['226 -  PH1 [°C]'], Se['qeff_PH [W/m^2]'])
                Se['Tw2_PH [°C]'] = self.Twiz(Se['227 - PH2 [°C]'], Se['qeff_PH [W/m^2]'])
                Se['Tw3_PH [°C]'] = self.Twiz(Se['228 - PH3 [°C]'], Se['qeff_PH [W/m^2]'])
                Se['Tw4_PH [°C]'] = self.Twiz(Se['229 - PH4 [°C]'], Se['qeff_PH [W/m^2]'])
                    
                # Heat transfer coefficient calculus    
                Se['h1_PH [W/m²]'] = Se['qeff_PH [W/m^2]']/(Se['Tw1_PH [°C]'] - Se['Tfl1_PH [°C]'])
                Se['h2_PH [W/m²]'] = Se['qeff_PH [W/m^2]']/(Se['Tw2_PH [°C]'] - Se['Tfl2_PH [°C]'])
                Se['h3_PH [W/m²]'] = Se['qeff_PH [W/m^2]']/(Se['Tw3_PH [°C]'] - Se['Tfl3_PH [°C]'])
                Se['h4_PH [W/m²]'] = Se['qeff_PH [W/m^2]']/(Se['Tw4_PH [°C]'] - Se['Tfl4_PH [°C]'])
                Lh = [Se['h1_PH [W/m²]'], Se['h2_PH [W/m²]'], Se['h3_PH [W/m²]'], Se['h4_PH [W/m²]']]
                Se['h_PH_mean [W/m²]'] = np.mean([h for h in Lh if h >0])
                #Se['h_PH_mean [W/m²]'] = (Se['h1_PH [W/m²]'] + Se['h3_PH [W/m²]'] + Se['h4_PH [W/m²]'])/3
                if nb_iter == 0 :
                    h0 = Se['h_PH_mean [W/m²]']
                if Se['h_PH_mean [W/m²]'] < 0 :
                    Se['h_PH_mean [W/m²]'] = h0
                    print('h_PH_mean < 0 : break')
                    break
    
                # Nloss calculation 
                if nb_iter < 50 : 
                    new_nloss = self.coeffs[0]*Se['h_PH_mean [W/m²]']**(-self.coeffs[1])
                elif nb_iter == 50 :
                    new_nloss = (self.coeffs[0]*Se['h_PH_mean [W/m²]']**(-self.coeffs[1]) + Se['nloss_2f'])/2
                elif nb_iter > 100:
                    break
                if new_nloss > 1 :
                    new_nloss = self.coeffs[0]*h0**(-self.coeffs[1])
                    Se['P_trans_PH (W)'] = (1-Se['nloss_2f'])*Se['P_el_PH (W)'] #Transmitted power calculus
                    Se['qeff_PH [W/m^2]'] =  Se['P_trans_PH (W)']/self.Sint #Transmitted heat flux calculus
                    break
                print(f""" 
################Run : {nb_iter}################
File name : {Se.name}
Se['qeff_PH [W/m^2]'] : {Se['qeff_PH [W/m^2]']}
Se['h_PH_mean [W/m²]'] : {Se['h_PH_mean [W/m²]']}
Se['nloss_2f'] : {Se['nloss_2f']}
new_nloss : {new_nloss}
###############################################
                      """)

                if flag[0] == 0:
                    flag[0] = (abs(Se['nloss_2f'] - new_nloss)/Se['nloss_2f'] < 0.005)
                else :
                    flag[1] = (abs(Se['nloss_2f'] - new_nloss)/Se['nloss_2f'] < 0.005)
                    if not flag[1] : flag[0] = 0
                Se['nloss_2f'] = new_nloss
                nb_iter += 1
            print('Success')
            self.LSe.append(Se)
        self.df = pd.concat(self.LSe, axis=1).T
            
    def Tflz_2f(self) :
        
        print('')
    
    def h_mean(self):
        
        self.df['h1_PH [W/m²]'] = self.df['qeff_PH [W/m^2]']/(self.df['Tw1_PH [°C]'] - self.df['Tfl1_PH [°C]'])
        self.df['h2_PH [W/m²]'] = self.df['qeff_PH [W/m^2]']/(self.df['Tw2_PH [°C]'] - self.df['Tfl2_PH [°C]'])
        self.df['h3_PH [W/m²]'] = self.df['qeff_PH [W/m^2]']/(self.df['Tw3_PH [°C]'] - self.df['Tfl3_PH [°C]'])
        self.df['h4_PH [W/m²]'] = self.df['qeff_PH [W/m^2]']/(self.df['Tw4_PH [°C]'] - self.df['Tfl4_PH [°C]'])
        self.df['h_PH_mean [W/m²]'] = (self.df['h1_PH [W/m²]'] + self.df['h2_PH [W/m²]'] + self.df['h3_PH [W/m²]'] + self.df['h4_PH [W/m²]'])/4

        
        