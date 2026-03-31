"""
Thermodynamics functions
"""
#imports
from CoolProp.CoolProp import PropsSI
from math import log,exp,sin,cos,pi

#functions

#Enthalphie [J/kg]
H = lambda P, T, fluid : PropsSI("H", "T",T,"P",P,fluid)
Tsat = lambda Psat, fluid : PropsSI("T", "P", Psat,"Q", 1, fluid) # [K]
Psat = lambda Tsat, fluid : PropsSI("P", "T", Tsat, "Q", 1, fluid) # [Pa]
rho = lambda Psat, T, fluid : PropsSI("D", "P",Psat, "T",T, fluid) # kg/m3
mu = lambda P, T, fluid : PropsSI("viscosity", "P", P, "T", T, fluid)  # dynamic viscosity [Pa·s]
Pr = lambda Psat, T, fluid : PropsSI("Prandtl", "P",Psat, "T",T, fluid)
lmb = lambda Psat, T, fluid : PropsSI("conductivity", "P",Psat, "T",T, fluid)
Hl = lambda Psat, fluid : PropsSI("H", "P",Psat,"Q",0,fluid)
Hv = lambda Psat, fluid : PropsSI("H", "P",Psat,"Q",1,fluid)
Cp = lambda P, T, fluid : PropsSI('C', "P", P, "T", T, fluid)  # evaluated at actual T, not forced Q=0

