"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
            Convective boiling bench : Linear regression Error table
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"""
This script provide a function allowing to select a Keithley channel and get the 
calibration law and the sensor root mean squares error.
"""

# Imports
import pandas as pd

# Generation of udf - table of uncertainties of the measurements
def generateUdf(df_meas : pd.DataFrame) -> pd.DataFrame :

    # Get the excel in a table
    excel_path = r"C:\Users\yberton\OneDrive - INSA Lyon\Expérimental\Acquisition\Etalonnage\Etalonnage.xlsm"
    df_excel_pressure = pd.read_excel(excel_path,sheet_name="capteurs de pression")
    df_excel_thermocouple = pd.read_excel(excel_path, sheet_name="thermocouples")
    df_excel_thermocouple['RMSE [°C]'] = df_excel_thermocouple['RMSE [°C]'].fillna(1.5)

    # Get matching thermocouples 
    dict_canal_thermocouple = {}
    for i in range(len(df_excel_thermocouple)):
        for j in range(len(df_meas.columns)) : 
            if str(df_excel_thermocouple['n° canal'][i]) in df_meas.columns[j] : 
                    dict_canal_thermocouple[df_meas.columns[j]] = pd.Series([df_excel_thermocouple['RMSE [°C]'][i] for k in range(len(df_meas))]) 
    
    # Get matching pressure sensors 
    dict_canal_pressure = {}
    for i in range(len(df_excel_pressure)):
        for j in range(len(df_meas.columns)) : 
            if str(df_excel_pressure['n° canal'][i]) in df_meas.columns[j] : 
                    dict_canal_pressure[df_meas.columns[j]] = pd.Series([df_excel_pressure['Err [hPa]'][i]*1E-3 for k in range(len(df_meas))]) 

    dict_canal =   dict_canal_pressure | dict_canal_thermocouple # Merge the dictionnaries

    # Add mass flow sensor uncertainty
    dict_canal['105 - mass [kg/s]'] = df_meas['105 - mass [kg/s]'].values*0.2/100 # Donnée constructeur : erreur = 0.2% de la mesure

    # Calculate electric power unit  
    ## Preheater
    def voltage_uncertainty(voltage : float) -> float : 
        """Return the voltage uncertainty value
        as a sum of an uncertainty over the range
        and an uncertainty over the value"""
         
        if 0 <= voltage <= 0.1 :
            return(25E-6*voltage + 35E-6*0.1)
        elif 0.1 < voltage <= 1 :
            return(25E-6*voltage + 7E-6*0.9)
        elif 1 < voltage <= 10 :
            return(20E-6*voltage + 5E-6*9)
        elif 10 < voltage <= 100 :
             return(35E-6*voltage + 9E-6*90)
        
    def current_uncertainty_PH(current : float) -> float : 
         """Return the current uncertainty value
         as a sum of an uncertainty over the value + 
         1400 mA"""

         return(current*0.2 + 1.4)

    def current_uncertainty_TS(current : float) -> float : 
         """Return the current uncertainty value
         as a sum of an uncertainty over the value + 
         1400 mA"""    
         return(current*0.4/100)
    
    dict_canal['109 -  V_PH_corr [V]'] = df_meas['109 -  V_PH_corr [V]'].apply(voltage_uncertainty).to_numpy()
    dict_canal['I_PH (A)'] = df_meas['I_PH (A)'].apply(current_uncertainty_PH).to_numpy()
    dict_canal['P_el_PH (W)'] = (df_meas['P_el_PH (W)'].values*((dict_canal['109 -  V_PH_corr [V]']/df_meas['109 -  V_PH_corr [V]'])**2 + (dict_canal['I_PH (A)']/df_meas['I_PH (A)'])**2)**(0.5)).to_numpy()
    
    dict_canal['117 - V_TS_corr [V]'] = df_meas['117 - V_TS_corr [V]'].apply(voltage_uncertainty).to_numpy()
    dict_canal['I_TS (A)'] = df_meas['I_TS (A)'].apply(current_uncertainty_TS).to_numpy()
    dict_canal['P_el_TS (W)'] = (df_meas['P_el_TS (W)'].values*((dict_canal['117 - V_TS_corr [V]'] /df_meas['117 - V_TS_corr [V]'])**2 + (dict_canal['I_TS (A)']/df_meas['I_TS (A)'])**2)**(0.5)).to_numpy()

    # Add power supply sensor uncertainty

    udf = pd.DataFrame(dict_canal)
    return(udf)
     
if __name__ == "__main__":
     
     from utilities.data.lvm import lvm_to_df
     from utilities.path import getAFilesPath
     df_meas = lvm_to_df(getAFilesPath())
     udf = generateUdf(df_meas) 