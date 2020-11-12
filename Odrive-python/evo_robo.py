from math import pi
import time
from random import uniform as r_uni

import pandas as pd
import numpy as np
import odrive
from odrive.enums import *

import robo
import calibrate
import configure
import trajectory

exec_tolerance = .1
reset_delays = 5
tolerance_fails = 0

### DESCONTAR EL TIMEPO X OPERACION EN CADA UNA
samples = 100
traj = trajectory.build_trajectory(pos1=0, pos2=pi, t1=0.5, t2=0.5, res=samples)
num_individuals = 5
num_generations = 1

def evo_gains(odrv):
    global traj
    traj = trajectory.build_trajectory(pos1=0, pos2=pi, t1=0.5, t2=0.5, res=samples)
    robo.update_time_errors(odrv, samples)

    class Individual:
        def __init__(self, generation, id, gains):
            self.generation = generation
            self.id = generation*1000+id
            self.gains = gains
            self.error = get_error_score(odrv, gains, traj)

    population = []
    #Initiate population randomly
    for n in range(1, num_individuals+1):
        population.append(Individual(0, n, (r_uni(10,70), r_uni(1/10,3/10), r_uni(0,.75))))

    configure.gains(odrv)
    return population


def get_error_score(odrv, gains, traj):
    configure.gains(odrv, *gains)
    ok = 1 #test_vibration()
    if ok:
        t_df = pd.Series(data=performance_traj(odrv, traj, samples))
        error = sum(np.square(np.subtract(t_df.at["input_pos"],t_df.at["pos_estimate_a0"]))) + sum(np.square(np.subtract(t_df.at["input_pos"],t_df.at["pos_estimate_a1"])))
        print("Quad error on exec = " +str(error) +'\n')
    else:
        error = 0
    return error


def performance_traj(odrv, traj, samples=0):
    if samples == 0:
        sample_interval = 1
    else:
        sample_interval = (len(traj["OUTBOUND"])+len(traj["RETURN"]))//samples

    tot_time = traj["OUT_PERIOD"]*len(traj["OUTBOUND"]) + traj["RET_PERIOD"]*len(traj["RETURN"])
    sample_diff = len(traj["OUTBOUND"])%sample_interval

    success = False
    while not success:
        inputs = []
        estimates_a0 = []
        estimates_a1 = []
        currents_a0 = []
        currents_a1 = []

        directions = (traj["OUTBOUND"], traj["RETURN"])

        start = time.perf_counter()
        for d_traj in directions:
            if d_traj== traj["OUTBOUND"]:
                T_time = traj["OUT_PERIOD"]
            else:
                T_time = traj["RET_PERIOD"]

            for i, p in enumerate(d_traj):
                odrv.axis0.controller.input_pos = p
                odrv.axis1.controller.input_pos = p
                if ((i-1)%sample_interval == sample_interval-1):
                    inputs.append(p)
                    estimates_a0.append(odrv.axis0.encoder.pos_estimate)
                    currents_a0.append(odrv.axis0.motor.current_control.Iq_setpoint)
                    estimates_a1.append(odrv.axis1.encoder.pos_estimate)
                    currents_a1.append(odrv.axis1.motor.current_control.Iq_setpoint)
                    time.sleep(float(T_time-robo.input_sleep_adjust-robo.data_delay))
                else:
                    time.sleep(float(T_time-robo.input_sleep_adjust))
        end = time.perf_counter()
        exec_time = end-start
        print("TRAYECTORY TIME = " + str(exec_time))

        if abs(exec_time-tot_time) < tot_time*exec_tolerance:
            success = True
        else:
            global tolerance_fails
            tolerance_fails += 1
            if tolerance_fails >= reset_delays:
                robo.update_time_errors(odrv, samples)
                tolerance_fails = 0

    #End While not Succes loop
    return {"input_pos":inputs,
    "pos_estimate_a0":estimates_a0,
    "pos_estimate_a1":estimates_a1,
    "Iq_setpoint_a0":currents_a0,
    "Iq_setpoint_a1":currents_a1}

'''
def build_evo_raw():
    df = pd.DataFrame()
    # Create columns to store data
    df.insert(0, "Individuo", pd.Series([], dtype=int))
    df.insert(1, "pos_gain", pd.Series([], dtype=float))
    df.insert(2, "vel_gain", pd.Series([], dtype=float))
    df.insert(3, "vel_integrator_gain", pd.Series([], dtype=float))
    df.insert(4, "input_pos", pd.Series([], dtype=object))
    df.insert(5, "pos_estimate_a0", pd.Series([], dtype=object))
    df.insert(6, "pos_estimate_a1", pd.Series([], dtype=object))
    df.insert(7, "Iq_setpoint_a0", pd.Series([], dtype=object))
    df.insert(8, "Iq_setpoint_a1", pd.Series([], dtype=object))
    return df

def add_evo_raw(df, id, kp, kv, kvi, inputs, e0, e1, c1, c2):
    row = [id, kp, kv, kvi, inputs, e0, e1, c1, c2
    df.loc[len(df)] = row
    return df
'''