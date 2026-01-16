"""
Thermodynamics functions and correlations
"""

#imports
from CoolProp.CoolProp import PropsSI
from math import log,exp,sin,cos,pi


########################################################################################################
#                                             Monophasic                                               #
########################################################################################################

#Nusselt

def Nu_Shah_London(dint, P, z) :

    """
    Monophasic slug flow, dynamically established, thermally established, homogeneous heat flux okay for 1000*Z/(dint*Peliq) > 1
    Z = 1000*z/(dint*Peliq) (1971)
       
       Avec : 
       dint : diamètre intérieur [m]
       P : Pression [Pa]
       z : abcisse [m]
       
       """
    
    Z = 1000*z/(dint*P) 
    if Z < 0.9 : 
        print("Z = %f < 1 " % Z)
        raise ValueError 
    else : return(4.364 + 8.68*Z**(-0.506) + exp(-0.041*Z))

########################################################################################################
#                                             Two phases                                               #
########################################################################################################



########################################################################################################
#                                    Heat transfer in the evaporator                                   #
########################################################################################################

