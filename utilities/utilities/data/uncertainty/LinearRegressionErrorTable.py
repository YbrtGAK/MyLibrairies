"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
            Convective boiling bench : Linear regression Error table
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"""
This script provide a function allowing to select a Keithley channel and get the 
calibration law and the sensor root mean squares error.
"""

# Imports
import os
from functools import lru_cache

import numpy as np
import pandas as pd

EXCEL_PATH = r"C:\Users\Yann\Documents\These\Etalonnage.xlsm"

# ---------------------------------------------------------------------------
# Systematic floor on the thermocouple uncertainty
# ---------------------------------------------------------------------------
# The 'RMSE [°C]' column of the calibration workbook is the residual of the
# calibration fit alone: it excludes the uncertainty of the reference probe,
# post-calibration drift, and every installation effect (cold-junction, stem
# conduction, contact resistance, thermal paste). Ten of the twenty-four
# channels come out below 0.1 °C and two below 0.01 °C, which no installed
# type-K/T junction achieves in practice. Taken literally those values make the
# wall-to-fluid temperature difference — and hence h — look an order of
# magnitude better known than it is.
#
# TC_UNCERTAINTY_FLOOR is a Type-B floor applied to every thermocouple channel,
# and it is *systematic*: it is common to all the samples of a run, so it must
# NOT be divided by sqrt(N) when the run is averaged. Callers that average a
# .lvm acquisition therefore have to re-apply it afterwards — see
# apply_thermocouple_floor().
#
# Override with the TC_UNCERTAINTY_FLOOR environment variable (in °C); set it
# to 0 to recover the raw calibration residuals.
TC_UNCERTAINTY_FLOOR = float(os.environ.get("TC_UNCERTAINTY_FLOOR", 0.3))


@lru_cache(maxsize=1)
def _thermocouple_channels(excel_path : str = EXCEL_PATH) -> tuple :
    """Channel numbers, as strings, of every calibrated thermocouple."""
    sheet = pd.read_excel(excel_path, sheet_name="thermocouples")
    return tuple(str(c) for c in sheet['n° canal'])


def thermocouple_columns(columns, excel_path : str = EXCEL_PATH) -> list :
    """Subset of *columns* that are thermocouple channels.

    Same matching rule as generateUdf: the channel number appears in the
    column name.
    """
    channels = _thermocouple_channels(excel_path)
    return [c for c in columns if any(ch in c for ch in channels)]


def apply_thermocouple_floor(udf : pd.DataFrame,
                             floor : float = None,
                             excel_path : str = EXCEL_PATH) -> pd.DataFrame :
    """Raise every thermocouple column of *udf* to at least *floor* (°C).

    Idempotent, and meant to be applied again after any sqrt(N) averaging of
    the uncertainty table: the floor stands for a systematic effect that
    repeating the measurement does not reduce.
    """
    floor = TC_UNCERTAINTY_FLOOR if floor is None else float(floor)
    if floor <= 0:
        return udf
    for col in thermocouple_columns(udf.columns, excel_path):
        udf[col] = np.maximum(pd.to_numeric(udf[col], errors="coerce"), floor)
    return udf


# ---------------------------------------------------------------------------
# Electric power supplies — JCGM 100 Type B
# ---------------------------------------------------------------------------
# All the figures below come from
#   These/Incertitude/Note de calcul - Incertitudes alimentations électriques.xlsx
# and are manufacturer LIMITS, not standard deviations. JCGM 100 §4.3.7: with no
# knowledge of the shape, assume a rectangular distribution over ±a and take
# u = a/sqrt(3).
SQRT3 = np.sqrt(3.0)

# Voltage — DMM, spec of the form ±(ppm of reading + ppm of RANGE), per range.
# (ppm_reading, ppm_range, range full scale [V]); the range term multiplies the
# FULL SCALE of the range, not the width of the band.
_VOLTAGE_RANGES = [
    (25e-6, 35e-6, 0.1),
    (25e-6,  7e-6, 1.0),
    (20e-6,  5e-6, 10.0),
    (35e-6,  9e-6, 100.0),
    (45e-6,  6e-6, 1000.0),
]

# Current — taken from the manufacturers' technical documents, NOT from the
# workbook, whose figures could not be reproduced from either datasheet:
#
#   PH  Ametek Sorensen DCS 8-350E  (0-8 V, 0-350 A, 2800 W)
#       Operating manual M362295-01, §1.3.1 Electrical Specifications:
#           Meter accuracy, current .............. 4.5 A
#           Analog programming linearity, current  3.5 A
#           Line regulation, current ............. 0.35 A
#           Load regulation, current ............. 0.35 A
#       The logged value is a readback, so the meter accuracy applies: 4.5 A.
#       The workbook's 1.4 A appears nowhere in the datasheet.
#
#   TS  Sorensen SGA 60-250  (60 V, 250 A, 15 kW)
#       SG Series datasheet, "Programming & Read-back Specifications":
#           Remote digital interface, current .... +/-0.4 % of FULL SCALE
#           Remote analog interface, read-back ... +/-1.0 % of full scale
#           Front panel display .................. +/-(0.5 % fs + 1 digit)
#       Full scale for THIS unit is 250 A, so 0.4 % x 250 = 1.0 A.
#       The workbook applied the same 0.4 % to 6000 A (the series-wide maximum
#       printed on the datasheet cover, "5-6000 A") giving 24 A, and its table
#       used 2400 A (the 10 V / 24-30 kW entry of the ranges chart) giving
#       9.6 A. Neither is the rating of an SGA 60-250.
#
# Both overridable through the environment (in A) for sensitivity studies.
A_I_PH = float(os.environ.get("A_I_PH", 4.5))    # half-width of the limit [A]
A_I_TS = float(os.environ.get("A_I_TS", 1.0))    # half-width of the limit [A]

U_I_PH = A_I_PH / SQRT3
U_I_TS = A_I_TS / SQRT3

ELECTRICAL_COLUMNS = ['109 -  V_PH_corr [V]', 'I_PH (A)', 'P_el_PH (W)',
                      '117 - V_TS_corr [V]', 'I_TS (A)', 'P_el_TS (W)']


def voltage_uncertainty(voltage : float) -> float :
    """Standard uncertainty of a DMM voltage reading [V].

    Defined for every finite input: the sign is irrelevant to the accuracy
    spec, and anything above the largest range falls back to that range. The
    previous implementation returned None outside [0, 100] V, which silently
    poisoned every downstream column on runs where the supply was off.
    """
    if not np.isfinite(voltage):
        return np.nan
    v = abs(float(voltage))
    for ppm_rdg, ppm_rng, full_scale in _VOLTAGE_RANGES:
        if v <= full_scale:
            return (ppm_rdg * v + ppm_rng * full_scale) / SQRT3
    ppm_rdg, ppm_rng, full_scale = _VOLTAGE_RANGES[-1]
    return (ppm_rdg * v + ppm_rng * full_scale) / SQRT3


def _power_uncertainty(P, V, uV, I, uI):
    """u(P) for P = V*I, combined in quadrature on the relative terms.

    Guarded: V or I equal to zero (supply off) yields u(P) = 0 rather than the
    NaN the bare division produced, which used to propagate into 41 downstream
    columns.
    """
    P = np.asarray(P, dtype=float)
    V = np.asarray(V, dtype=float)
    I = np.asarray(I, dtype=float)
    uV = np.asarray(uV, dtype=float)
    uI = np.asarray(uI, dtype=float)
    rel_V = np.divide(uV, V, out=np.zeros_like(V), where=V != 0)
    rel_I = np.divide(uI, I, out=np.zeros_like(I), where=I != 0)
    return np.abs(P) * np.sqrt(rel_V ** 2 + rel_I ** 2)


# ---------------------------------------------------------------------------
# Which columns must survive sample averaging
# ---------------------------------------------------------------------------
# Everything generateUdf returns is a Type-B instrument figure — a calibration
# residual or a manufacturer spec. Such a term is common to every sample of one
# acquisition, so averaging n samples does NOT reduce it and the /sqrt(n) that
# the pipelines apply must be undone. Thermocouples and the electrical chain are
# treated that way here.
#
# That is EVERY column this module emits: the thermocouples (calibration
# residuals), the electrical chain (instrument limits), the pressure
# transducers ('Err [hPa]', calibration) and the mass-flow meter (0.2 % of
# reading, manufacturer data). None of them is random sample-to-sample scatter,
# so none is reducible by averaging and systematic_columns() returns all of
# them.
#
# The genuine Type-A term — the standard deviation of the n samples of one
# acquisition, divided by sqrt(n) — is a SEPARATE contribution that this module
# does not currently compute. Add it as a quadrature term if the steady-state
# scatter ever matters.
def systematic_columns(columns, excel_path : str = EXCEL_PATH) -> list :
    """Columns whose uncertainty is systematic and not reducible by sqrt(N)."""
    return list(columns)


def undo_sample_averaging(u_mean : pd.Series, n_samples : int,
                          excel_path : str = EXCEL_PATH) -> pd.Series :
    """Restore the systematic columns of *u_mean* after a /sqrt(n) division.

    *u_mean* is the per-column mean of a generateUdf table for one acquisition,
    as built by the pipelines. Multiplying the systematic subset back by
    sqrt(n_samples) cancels the division they apply next.
    """
    if n_samples <= 1:
        return u_mean
    out = u_mean.copy()
    cols = systematic_columns(out.index, excel_path)
    out[cols] = out[cols] * np.sqrt(n_samples)
    return out


# Generation of udf - table of uncertainties of the measurements
def generateUdf(df_meas : pd.DataFrame) -> pd.DataFrame :

    # Get the excel in a table
    excel_path = EXCEL_PATH
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

    # ---------------------------------------------------------------------
    # Electric power supplies
    # ---------------------------------------------------------------------
    # Source: "Note de calcul - Incertitudes alimentations électriques.xlsx".
    # The instrument figures there are manufacturer LIMITS (an interval the
    # error is stated not to exceed), so per JCGM 100 §4.3.7 each is converted
    # to a standard uncertainty by assuming a rectangular distribution and
    # dividing the half-width by sqrt(3).

    dict_canal['109 -  V_PH_corr [V]'] = (
        df_meas['109 -  V_PH_corr [V]'].apply(voltage_uncertainty).to_numpy())
    dict_canal['I_PH (A)'] = np.full(len(df_meas), U_I_PH)
    dict_canal['P_el_PH (W)'] = _power_uncertainty(
        df_meas['P_el_PH (W)'], df_meas['109 -  V_PH_corr [V]'],
        dict_canal['109 -  V_PH_corr [V]'], df_meas['I_PH (A)'],
        dict_canal['I_PH (A)'])

    dict_canal['117 - V_TS_corr [V]'] = (
        df_meas['117 - V_TS_corr [V]'].apply(voltage_uncertainty).to_numpy())
    dict_canal['I_TS (A)'] = np.full(len(df_meas), U_I_TS)
    dict_canal['P_el_TS (W)'] = _power_uncertainty(
        df_meas['P_el_TS (W)'], df_meas['117 - V_TS_corr [V]'],
        dict_canal['117 - V_TS_corr [V]'], df_meas['I_TS (A)'],
        dict_canal['I_TS (A)'])

    udf = pd.DataFrame(dict_canal)
    apply_thermocouple_floor(udf)
    return(udf)
     
if __name__ == "__main__":
     
     from utilities.data.lvm import lvm_to_df
     from utilities.path import getAFilesPath
     df_meas = lvm_to_df(getAFilesPath())
     udf = generateUdf(df_meas) 