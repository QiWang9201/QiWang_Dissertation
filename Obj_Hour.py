import pandas as pd
import numpy as np

def Obj_hour(curr_p, L, Z, bid_z):
    obj_hour = 0
    for z in Z:
        for b in bid_z[z][0]: #for demand hourly bids
            x = [0] * (len(L[b][2])-1) # store the accepted fraction for each segment
            for i in range(len(L[b][2])-1): #for each segment
                if curr_p[z-1] <= L[b][2][i+1]: # if the current price is lower than the last price of i_th segment, accept 1
                    x[i] = 1
                elif curr_p[z-1] >= L[b][2][i]:# if the current price is higher than the first price of i_th segment, accept 0
                    x[i] = 0
                else:
                    x[i] = (L[b][2][i] - curr_p[z-1])/(L[b][2][i] - L[b][2][i+1])
            for j in range(len(L[b][2])-1):
                obj_hour += 0.5*(2*L[b][2][j] + x[j]*(L[b][2][j+1] - L[b][2][j])) * x[j] * (L[b][1][j+1] - L[b][1][j])
        for b in bid_z[z][1]: #针对supply hourly bids
            x = [0] * (len(L[b][2])-1)
            for i in range(len(L[b][2])-1):
                if curr_p[z-1] >= L[b][2][i+1]:
                    x[i] = 1
                elif curr_p[z-1] <= L[b][2][i]:
                    x[i] = 0
                else:
                    x[i] = (curr_p[z-1] - L[b][2][i])/(L[b][2][i+1] - L[b][2][i])
            for j in range(len(L[b][2])-1):
                obj_hour -= 0.5*(2*L[b][2][j] + x[j]*(L[b][2][j+1] - L[b][2][j])) * x[j] * (L[b][1][j+1] - L[b][1][j])
    return obj_hour