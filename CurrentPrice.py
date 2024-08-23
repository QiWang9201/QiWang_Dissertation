import pandas as pd
import numpy as np
#每次计算combined_y的时候需要在已经更新的基础上，而不是一直用最初始状态的combined_y

# all_x_points: all the possible prices(x) in hour z
# combined_y: corresponding y for the all_x_points
def get_inisol(all_x_points, combined_y):
    point0 = 0
    point1 = 0
    if min(combined_y) > 0:
        return max(all_x_points)
    else:
        for y in range(len(combined_y)-1):
            if combined_y[y] >= 0 and combined_y[y+1] <= 0: # it means that the zeros appears in this segment
                slope0 = (combined_y[y+1]-combined_y[y])/(all_x_points[y+1]-all_x_points[y])
                intercept0 = combined_y[y]-slope0*all_x_points[y]
                if slope0 != 0:
                    point0 = -intercept0/slope0
                    return point0
                else:
                    point1 = all_x_points[y] 
                    return point1

def get_cpsol(all_x_points, combined_y, M):# M: the quantity of the accepted block bids (demand: positive, supply: negative)   
    combined_y = combined_y + M # add the quantity to the aggregate curve
    point0 = 0
    point1 = 0
    for y in range(len(combined_y)-1):
        if combined_y[y] >= 0 and combined_y[y+1] <= 0:
            slope0 = (combined_y[y+1]-combined_y[y])/(all_x_points[y+1]-all_x_points[y])
            intercept0 = combined_y[y]-slope0*all_x_points[y]
            if slope0 != 0:
                point0 = -intercept0/slope0
                return point0
            else:
                point1 = all_x_points[y]
                return point1