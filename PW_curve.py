import pandas as pd
import numpy as np

# plists : all the prices' list in hour z
def union_of_x(plists):
    all_x = set()
    for l in plists:
        all_x.update(l)
    return sorted(list(all_x)) # get all the possible prices in hour z

def line_info(points):
        line_eq = []
        for i in range(len(points)-1):
            x1,y1 = points[i]
            x2,y2 = points[i+1]
            slope = (y2-y1)/(x2-x1)
            intercept = y1-slope*x1
            line_eq.append((slope,intercept,x1,x2))
        return line_eq # get the information about each segment:  slope, intercept, first/last price

def get_combine_curve(bid_z, L_adj, Z):
    x = {}
    y = {}
    for z in Z:
        # define plists
        plists = []
        for i in bid_z[z]:
            for b in i:
                plists.append(L_adj[b][2]) #L_adj[b][2]: price list for hourly bid b

        all_x_points = union_of_x(plists)
        x[z] = all_x_points
        # 
        

        all_line_eq = {}
        for i in bid_z[z]:
            for b in i:
                points = list(zip(L_adj[b][2],L_adj[b][1])) #L_adj[b][2]: price list for hourly bid b, L_adj[b][1]: quantity list for hourly bid b
                all_line_eq[b] = line_info(points)

        # calculate the corresponding y(quantities) for every x in all_x_points(prices)
        combined_y = np.zeros(len(all_x_points))
        for i in bid_z[z]:
            for b in i:
                all_y_points = np.zeros(len(all_x_points))
                all_x_points = np.array(all_x_points)
                # according to the information of each segment, calculate the y(quantities)
                for k in range(len(all_x_points)):# for each element in all_x_points
                    for slope, intercept, x1, x2 in all_line_eq[b]:#determine which segment the x belongs to
                        if x1 <= all_x_points[k] <= x2:
                            all_y_points[k] = slope * all_x_points[k] + intercept
                combined_y = combined_y + all_y_points
        y[z] = combined_y
    return x,y
# x[z]: all_x_points in hour z
# y[z]: combined_y in hour z