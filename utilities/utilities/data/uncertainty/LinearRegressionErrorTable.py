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

# Calibration workbook: the ETALONNAGE_XLSM environment variable if set,
# otherwise the first copy found among the known locations (acquisition PC,
# then the root of D: on the writing laptop).
_EXCEL_CANDIDATES = (r"C:\Users\Yann\Documents\These\Etalonnage.xlsm",
                     r"D:\Etalonnage.xlsm")


def _find_workbook() -> str :
    env = os.environ.get("ETALONNAGE_XLSM")
    if env:
        return env
    for path in _EXCEL_CANDIDATES:
        if os.path.exists(path):
            return path
    return _EXCEL_CANDIDATES[0]


EXCEL_PATH = _find_workbook()

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
# TC_UNCERTAINTY_FLOOR is a Type-B floor applied to every thermocouple channel
# but the two below, and it is *systematic*: it is common to all the samples of
# a run, so it must NOT be divided by sqrt(N) when the run is averaged. Callers
# that average a .lvm acquisition therefore have to re-apply it afterwards —
# see apply_thermocouple_floor().
#
# The two immersed fluid thermocouples of the evaporator, inlet (202) and
# outlet (218), take TC_FLUID_FLOOR instead: 0.15 °C, from the in-house
# calibration campaign (thesis, data reduction chapter). Their fit residuals
# (0.004 and 0.001 °C) are the two below 0.01 °C mentioned above, so this floor
# is what sets their uncertainty.
#
# Override with the TC_UNCERTAINTY_FLOOR and TC_FLUID_FLOOR environment
# variables (in °C); set both to 0 to recover the raw calibration residuals.
TC_UNCERTAINTY_FLOOR = float(os.environ.get("TC_UNCERTAINTY_FLOOR", 0.3))
TC_FLUID_FLOOR = float(os.environ.get("TC_FLUID_FLOOR", 0.15))
TC_FLUID_CHANNELS = ('202', '218')


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
                             excel_path : str = EXCEL_PATH,
                             fluid_floor : float = None) -> pd.DataFrame :
    """Raise every thermocouple column of *udf* to at least its floor (°C).

    The channels of TC_FLUID_CHANNELS take *fluid_floor*, every other one
    *floor*; a floor <= 0 leaves its channels untouched. Idempotent, and meant
    to be applied again after any sqrt(N) averaging of the uncertainty table:
    the floor stands for a systematic effect that repeating the measurement
    does not reduce.
    """
    floor = TC_UNCERTAINTY_FLOOR if floor is None else float(floor)
    fluid_floor = TC_FLUID_FLOOR if fluid_floor is None else float(fluid_floor)
    for col in thermocouple_columns(udf.columns, excel_path):
        f = fluid_floor if _lvm_channel(col) in TC_FLUID_CHANNELS else floor
        if f > 0:
            udf[col] = np.maximum(pd.to_numeric(udf[col], errors="coerce"), f)
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

# Current — both supplies report their output current to LabVIEW over an RS-232
# digital link, so what applies is each one's READBACK accuracy: not the
# front-panel meter accuracy, and not an analog-monitor spec.
#
#   PH  Ametek Sorensen DCS 8-350E  (0-8 V, 0-350 A, 2800 W)
#       DCS Series datasheet, "DCS Series : Product Specifications 1-3 kW",
#       3 kW block, Readback Accuracy column (M130 / M131 / M9C / M85 digital
#       interface options):
#           Voltage ....... 12 mV
#           Current ....... 1400 mA   <- A_I_PH
#       Beware: the operation manual M362295-01 s1.3.1 does NOT carry this row.
#       Its "Meter accuracy, current 4.5 A" is the front-panel display spec and
#       must not be used for a digital readback.
#
#   TS  Sorensen SGA 60-250  (60 V, 250 A, 15 kW)
#       SG Series datasheet, "Programming & Read-back Specifications", Remote
#       Digital Interface row (the row whose notes list RS-232C):
#           Read-back, current ... +/-0.4 % of FULL SCALE
#       Full scale for THIS unit is 250 A, so 0.4 % x 250 = 1.0 A. For
#       reference the other two paths would give 2.5 A (remote analog read-back,
#       1.0 % fs) and 1.25 A + 1 digit (front panel).
#
# Both therefore land on 0.4 % of their own full scale.
#
# The bench workbook ("Note de calcul - Incertitudes alimentations
# electriques.xlsx") has the PH figure right at 1.4 A. Its TS figure is not:
# it applied the correct 0.4 % to 6000 A -- the series-wide maximum printed on
# the SG datasheet cover, "5-6000 A" -- giving 24 A, while its table used
# 2400 A (the 10 V / 24-30 kW entry of the ranges chart) giving 9.6 A. Neither
# is the rating of an SGA 60-250.
#
# Both overridable through the environment (in A) for sensitivity studies.
A_I_PH = float(os.environ.get("A_I_PH", 1.4))    # half-width of the limit [A]
A_I_TS = float(os.environ.get("A_I_TS", 1.0))    # half-width of the limit [A]

U_I_PH = A_I_PH / SQRT3
U_I_TS = A_I_TS / SQRT3

ELECTRICAL_COLUMNS = ['109 -  V_PH_corr [V]', 'I_PH (A)', 'P_el_PH (W)',
                      '117 - V_TS_corr [V]', 'I_TS (A)', 'P_el_TS (W)']

# Mass-flow meter: manufacturer limit of 0.2 % of reading, rectangular like the
# power-supply limits above.
A_MASS_REL = 0.2 / 100

# ---------------------------------------------------------------------------
# Pressure transducers — calibration certificates
# ---------------------------------------------------------------------------
# Every transducer, absolute and differential, was calibrated by an external
# company that issued one certificate per sensor (calibration law and its
# uncertainty). The 'capteurs de pression' sheet of the workbook transcribes
# them, the uncertainty in its 'Err [hPa]' column.
#
# The sheet's 'n° canal' column is out of date: the sensors moved between
# acquisition channels after it was filled in. Matching on it gave the outlet
# transducer (LVM channel 114) the 0.062 hPa of the 0-50 mbar differential
# sensor instead of its own 70 hPa. Sensors are therefore matched on the
# sheet's 'Nom' column, through the LVM channel below.
#
# The factor converts hPa into the unit the LVM column ACTUALLY carries. The
# absolute transducers are logged in bar. The 0-2 bar differential channel is
# logged in mbar despite its "[bars]" header (see HTC_analysis), so its
# uncertainty stays in hPa = mbar; applying the bar factor made it 1000 times
# too small.
#
# Channel 113 (DP_5) has no certificate in the sheet and is dead on this bench,
# so it gets no uncertainty column.
#
# TO CHECK: 'Err [hPa]' is used here as a STANDARD uncertainty (k = 1). If the
# certificates state an expanded uncertainty (k = 2 is the usual convention),
# every value below must be halved.
PRESSURE_SENSORS = {
    # LVM channel: (sheet 'Nom', hPa -> LVM column unit)
    '114': ('Evaporator out',         1e-3),   # bar
    '115': ('Tank',                   1e-3),   # bar
    '118': ('Evaporator in',          1e-3),   # bar
    '120': ('Pump in',                1e-3),   # bar
    '112': ('Evaporator (0-2 bars)',  1.0),    # mbar, despite the header
    '102': ('Evaporator (0-50mbars)', 1.0),    # mbar
}


def _lvm_channel(column : str) -> str :
    """'114 - P_TS_out [bars]' -> '114'."""
    return column.split(' - ')[0].strip()


def pressure_uncertainties(excel_path : str = EXCEL_PATH) -> dict :
    """Standard uncertainty of each pressure channel, in its LVM column unit.

    Keyed by LVM channel number. A sensor named in PRESSURE_SENSORS but missing
    from the sheet raises, rather than leaving the channel silently exact.
    """
    sheet = pd.read_excel(excel_path, sheet_name="capteurs de pression")
    err_hpa = dict(zip(sheet['Nom'].astype(str).str.strip(), sheet['Err [hPa]']))
    out = {}
    for channel, (name, factor) in PRESSURE_SENSORS.items():
        if name not in err_hpa:
            raise KeyError(f"Pressure sensor '{name}' (channel {channel}) not "
                           f"found in the 'capteurs de pression' sheet.")
        out[channel] = float(err_hpa[name]) * factor
    return out


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
# transducers ('Err [hPa]', calibration certificates) and the mass-flow meter
# (0.2 % of reading, manufacturer limit). None of them is random sample-to-sample scatter,
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


def type_a_uncertainty(df_meas : pd.DataFrame, n_samples : int = None) -> pd.Series :
    """Type-A standard uncertainty of the MEAN of each column (JCGM 100 s4.2.3).

    u_A(qbar) = s(q) / sqrt(n), with s the experimental standard deviation of
    the n samples of one acquisition. Unlike the Type-B terms above this one IS
    reduced by averaging, which is exactly why the two are kept apart.
    """
    n = len(df_meas) if n_samples is None else int(n_samples)
    num = df_meas.select_dtypes(include=[np.number])
    if n < 2 or num.empty:
        return pd.Series(0.0, index=num.columns, dtype=float)
    return num.std(ddof=1) / np.sqrt(n)


def combine_type_a(u_b : pd.Series, df_meas : pd.DataFrame,
                   n_samples : int = None) -> pd.Series :
    """Combine a Type-B uncertainty table with the Type-A sample scatter.

    u = sqrt(u_B^2 + u_A^2), column by column. Columns of *u_b* that the raw
    measurement table does not carry (derived quantities such as P_el) keep
    their Type-B value unchanged.
    """
    u_a = type_a_uncertainty(df_meas, n_samples)
    out = u_b.astype(float).copy()
    common = [c for c in out.index if c in u_a.index]
    if common:
        a = pd.to_numeric(u_a[common], errors="coerce").fillna(0.0).to_numpy()
        b = pd.to_numeric(out[common], errors="coerce").fillna(0.0).to_numpy()
        out[common] = np.sqrt(a ** 2 + b ** 2)
    return out


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
    df_excel_thermocouple = pd.read_excel(excel_path, sheet_name="thermocouples")
    df_excel_thermocouple['RMSE [°C]'] = df_excel_thermocouple['RMSE [°C]'].fillna(1.5)

    # Get matching thermocouples 
    dict_canal_thermocouple = {}
    for i in range(len(df_excel_thermocouple)):
        for j in range(len(df_meas.columns)) : 
            if str(df_excel_thermocouple['n° canal'][i]) in df_meas.columns[j] : 
                    dict_canal_thermocouple[df_meas.columns[j]] = pd.Series([df_excel_thermocouple['RMSE [°C]'][i] for k in range(len(df_meas))]) 
    
    # Get matching pressure sensors, by name (see PRESSURE_SENSORS)
    u_pressure = pressure_uncertainties(excel_path)
    dict_canal_pressure = {}
    for col in df_meas.columns:
        channel = _lvm_channel(col)
        if channel in u_pressure:
            dict_canal_pressure[col] = np.full(len(df_meas), u_pressure[channel])

    dict_canal =   dict_canal_pressure | dict_canal_thermocouple # Merge the dictionnaries

    # Add mass flow sensor uncertainty: manufacturer limit, rectangular
    dict_canal['105 - mass [kg/s]'] = (
        np.abs(df_meas['105 - mass [kg/s]'].values) * A_MASS_REL / SQRT3)

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