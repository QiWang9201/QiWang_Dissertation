import numpy as np
import pandas as pd
import importlib
import time
import PW_curve as PW
import CurrentPrice as CP
import Obj_Hour as OH

importlib.reload(OH)
importlib.reload(CP)

def AIPAB(filename):
    # import the data
    print(f'The data is {filename}')
    column_names = ['Order_id','Segment','Hour_start','Type','Quantity','Price','Hour_Covered','Linked']
    df = pd.read_csv(filename, header=None, names = column_names)

    # the set of Order id of hourly bids
    Order_id_S = np.unique(df.loc[df.loc[:,'Type'] == 'S'].loc[:,'Order_id'])
    # the set of Order id of block bids
    Order_id_B = np.unique(df.loc[df.loc[:,'Type'] == 'B'].loc[:,'Order_id'])
    # the set of Order id of flexible bids
    Order_id_F = np.unique(df.loc[df.loc[:,'Type'] == 'F'].loc[:,'Order_id'])

    # Define the set of hourly supply bids S and the set of hourly demand bids T
    S = [];
    T = [];
    for i in Order_id_S:
        if sum(df[df.loc[:,'Order_id']==i].iloc[:,4]) > 0:
            T.append(i);
        else:
            S.append(i);

    # Define the set of block supply bids BS and the set of block demand bids BT
    BS = []
    BT = []
    for i in Order_id_B:
        if df[df.loc[:,'Order_id']==i].iloc[:,4].values[0] > 0:
            BT.append(i);
        else:
            BS.append(i);

    # Define the set of flexible supply bids ES and the set of flexible demand bid ET        
    ES = []
    ET = []
    for i in Order_id_F:
        if df[df.loc[:,'Order_id']==i].iloc[:,4].values[0] > 0:
            ET.append(i);
        else:
            ES.append(i);

    # Define the set of periods Z
    Z = np.arange(min(df['Hour_start'].tolist()), max(df['Hour_start'].values+df['Hour_Covered'].values))

    # Define the the Order_id in each time period
    bid_z = {}
    for z in Z:
        tlist = [];
        slist = [];
        for i in np.unique(df[df.loc[:,'Hour_start']==z]['Order_id']):
            if df[df['Order_id'] == i].iloc[:,3].values[0] == 'S':
                if sum(df[df.loc[:,'Order_id']==i].iloc[:,4]) > 0:
                    tlist.append(i);
                else:
                    slist.append(i);
        bid_z[z] = [tlist,slist]

    # Define L[i]: set of segments for hourly bid i
    # Form : {id:[segment number,quantity list,price list]}
    L_adj = {}
    for i in Order_id_S:
        L_adj[i] = [df[df.loc[:,'Order_id']==i].loc[:,['Segment']].values[-1][0]-1 , df[df.loc[:,'Order_id']==i]['Quantity'].tolist() , df[df.loc[:,'Order_id']==i]['Price'].tolist()]

    L= {}
    for i in T:
        L[i] = [L_adj[i][0] , L_adj[i][1][::-1] , L_adj[i][2][::-1]]
    for i in S:
        L[i] = [L_adj[i][0] , [-num for num in L_adj[i][1]] , L_adj[i][2]]

    # Define K_b(set of blocks linked to block bid b)
    # Form : {child : parent}
    Kb = {}
    for i in Order_id_B:
        if pd.isna(df.loc[df['Order_id'] == i, 'Linked']).values[0]:
            Kb[i] = np.array([])
        else:
            Kb[i] = np.array([(int(df.loc[df['Order_id'] == i, 'Linked'].values))])

    # Define Bsc (set of child supply block bids) and Bst (set of child demand block bids)
    Bsc = []
    Btc = []
    for i in Order_id_B:
        if pd.notna(df.loc[df[df.loc[:,'Order_id']==i].index, 'Linked']).values[0]:
            if df[df.loc[:,'Order_id']==i].iloc[:,4].values[0] > 0:
                Btc.append(i)
            else:
                Bsc.append(i)

    # Define Bbid (the information of each block bids b)
    # Form : Bbid[b] = [start time，covered time，quantity，price]
    Bbid = {}
    for i in Order_id_B:
        Bbid[i] = [df[df.loc[:,'Order_id'] == i].loc[:,'Hour_start'].values[0],df[df.loc[:,'Order_id'] == i].loc[:,'Hour_Covered'].values[0], df[df.loc[:,'Order_id']==i]['Quantity'].values[0], df[df.loc[:,'Order_id']==i]['Price'].values[0]]

    # Define Fbid (the information of each flexible bid e)
    # Form Fbid[e] = [Quantity,price]
    Fbid = {}
    for i in Order_id_F:
        Fbid[i] = [df[df.loc[:,'Order_id']==i]['Quantity'].values[0],df[df.loc[:,'Order_id']==i]['Price'].values[0]]

    # Define Delta (equal to 1 if block bid b covers time period z)
    Delta = {}
    for i in Order_id_B:
        base0 = [0] * 24
        base0[Bbid[i][0]-1:Bbid[i][0]+Bbid[i][1]-1] = [1] * Bbid[i][1]
        Delta[i] = base0

    # Define Fmin and Fmax
    # Form: F[z] = {Fmin,Fmax}
    F = {}
    for z in Z:
        if len(df[(df['Hour_start']==z) & (df['Type']=='S')]['Price'].tolist()) > 0:
            F[z] = [min(df[(df['Hour_start']==z) & (df['Type']=='S')]['Price'].tolist()),max(df[(df['Hour_start']==z) & (df['Type']=='S')]['Price'].tolist())]
        else:
            F[z] = [0,0]

    # Define Gamma (large number compared with the problem parameters)
    Gam = 50000

    #Output information about the data set
    print(f'The number of hourly bid is {len(Order_id_S)}')
    print(f'The number of demand block bids is {len(BT)}')
    print(f'The number of supply block bids is {len(BS)}')
    print(f'The number of demand flexible bids is {len(ET)}')
    print(f'The number of demand flexible bids is {len(ES)}')
    print(f'The number of linked block bids is {len(Bsc)+len(Btc)}')
    
    print('Start soloving model');
    start_time = time.process_time()
    
    # Step 0
    BR = [] # set of rejected block bids
    BR = list(Order_id_B) # reject all block bids
    BK = [] # set of accepted block bids
    BPA = [] # paradoxically accepted block bids
    FR = [] # set of rejected flexible bids
    FR = list(Order_id_F) # reject all flexible bids
    FK = [] # set of accepted flexible bids
    FPA = [] # paradoxically accepted flexible bids
    F_time = {} # store the time of the accpected flexible bids
    iter_num = 0
    iter_lim = 5
    grand_iter_num = 0
    grand_iter_lim = 10


    # Step1: Get the initial solution using only hourly bids
    x,y = PW.get_combine_curve(bid_z, L_adj, Z)

    # Step2: Calculate the current price
    curr_p = np.zeros(len(Z))
    for z in Z:
        curr_p[z-1] = CP.get_inisol(x[z],y[z])

    # Step3 - Step8
    while grand_iter_num < grand_iter_lim:
        flag3 = 1
        iter_num = 0
        # Step3 - Step4
        while flag3 > 0:
            impact_value_3 = {}
            for b in BR:
                avg_cp = sum(np.array(Delta[b])*curr_p)/Bbid[b][1]
                impact_value_3[b] = (Bbid[b][3] - avg_cp) * Bbid[b][2] * Bbid[b][1]

            # Step3.1 calculate the impact value for all bids in BR, sort them in decreasing order
            sorted_dict = sorted(impact_value_3.items(), key=lambda item: item[1],reverse = True)
            impact_value_3 = dict(sorted_dict)

            if list(impact_value_3.values())[0] > 0: # now go to Step3.2.1
                # update BK and BR
                add_in = list(impact_value_3.keys())[0]
                BK.append(add_in)
                BR.remove(add_in)

                # update current price curr_p
                for z in Z:
                    if Delta[add_in][z-1] > 0:# z_th hour is impacted by block b
                        y[z] = y[z] + Bbid[add_in][2] #在产生影响的小时里，需要更新y[z]（x是没有变化的），只需要在受影响的小时里面更改y即刻
                        ans = CP.get_inisol(x[z],y[z])
                        #ans = CP.get_inicp(x[z], y[z], Bbid[add_in][2])
                    else:
                        ans = curr_p[z-1]
                    curr_p[z-1] = ans
                flag3 = 1
                continue
            else:
                iter_num += 1


            if iter_num < iter_lim:# the iteration number less than the limit
                # now go to step 4
                impact_value_4 = {}
                for b in BK:
                    avg_cp = sum(np.array(Delta[b])*curr_p)/Bbid[b][1]
                    impact_value_4[b] = (Bbid[b][3] - avg_cp) * Bbid[b][2] * Bbid[b][1]
                sorted_dict = sorted(impact_value_4.items(), key=lambda item: item[1]) #in increasing order
                impact_value_4 = dict(sorted_dict)

                # determine whether there is bid in BK with negative impact value

                if list(impact_value_4.values())[0] < 0: # there exists a bid in BK with negative impact value
                    # Step 4.2.1
                    # update BR and BK
                    rem_out = list(impact_value_4.keys())[0]
                    BR.append(rem_out)
                    BK.remove(rem_out)
                    flag3 = 0
                    # update current price curr_p
                    for z in Z:
                        if Delta[rem_out][z-1] > 0:# z_th hour is impacted by block b
                            y[z] = y[z] - Bbid[rem_out][2]#因为是reject所以需要减掉对应的质量
                            ans = CP.get_inisol(x[z], y[z])
                            #ans = CP.get_cpsol(x[z], y[z], -Bbid[rem_out][2])
                        else:
                            ans = curr_p[z-1]
                        curr_p[z-1] = ans
                        #continue
                    # now go to Step 5
                else: # no bids in BK with negative impact value, now go to Step3
                    flag3 = 1
                    continue
            else: # iteration number exceeds the iteration limit
                flag3 = 0 # go to step5

        # Step 5
        impact_value_5 = {}
        # calculate the impact value for each bid in BK
        for b in BK:
            avg_cp = sum(np.array(Delta[b])*curr_p)/Bbid[b][1]
            impact_value_5[b] = (Bbid[b][3] - avg_cp) * Bbid[b][2] * Bbid[b][1]

        for b in list(impact_value_5.keys()):
            if impact_value_5[b] < 0:# if the bid has negative impact value
                #BK.remove(b)
                BPA.append(b)

        # Step 6 Consider the linked bids 
        # Step 6.1: sort BR by using the order_id
        # 问题：第一遍大循环和第二遍大循环明明已经被reject掉的再次被reject掉了
        # 解决：reject之后在第二遍大循环开始之后又在Step3中被接受了，所以会一直循环

        BR.sort() 
        NL = 1
        TBR = []

        while NL <= len(BR): # while NL less than the length of the BR
            block_checked = BR[NL-1] # set block_checked as the NL_th block in BR
            flag6 = 1

            # Step 6.3
            while flag6 == 1:
                # keys是block_checked的child的集合
                # keys is the set which contains all the child of bid block_checked
                keys = [key for key,value in Kb.items() if value == block_checked]
                if len(set(keys) & set(BK)) == 0: # no such c exists
                    # go to step 6.3.2
                    if BR[NL-1] == block_checked: # if block_checked is the NL_th bid in BR
                        NL = NL +1
                        flag6 = 0 # go to Step 6.2 or Step 6.4, but can not go to Step 6.3
                    else:
                        block_checked = Kb[block_checked][0]
                        # go to step 6.3
                        flag6 = 1
                else:# go to Step 6.3.1
                    b = list(set(keys) & set(BK))[0] # choose the first elements in the intersection of keys and BK
                    BK.remove(b)
                    TBR.append(b)
                    block_checked = b
                    # update current price curr_p
                    for z in Z:
                        if Delta[b][z-1] > 0:# z_th hour is impacted by block b
                            y[z] = y[z] - Bbid[b][2]
                            ans = CP.get_inisol(x[z], y[z])
                        else:
                            ans = curr_p[z-1]
                        curr_p[z-1] = ans
                    flag6 = 1 # now go to Step 6.3
        # Step 6.4 :merge BR and TBR
        BR.extend(TBR)

        #Step 7: Adding flexible bids
        flag72 = 1
        flag73 = 1
        ET_p = {}
        ES_p = {}
        for e in FR:
            if e in ET:
                ET_p[e] = Fbid[e][1]
            else:
                ES_p[e] = Fbid[e][1]

        # Step 7.2
        # Step7.2 improve ver.
        while flag72 > 0:
            if len(ET_p) > 0:# there are demand flexible bids not rejected
                if max(ET_p.values()) > min(curr_p):
                    ET_del = []
                    for e in ET_p.keys():
                        if ET_p[e] > min(curr_p):
                            FR.remove(e)
                            ET_del.append(e)# add the order id into the ET_del, which means that the key-value need to be deleted in ET_p
                            FK.append(e)
                            F_time[e] = np.argmin(curr_p) + 1 # which hour should flexible bid be accepted
                            # update current price curr_p
                            y[np.argmin(curr_p)+1] = y[np.argmin(curr_p)+1] + Fbid[e][0]#在对应的那一小时里面更新y
                            curr_p[np.argmin(curr_p)] = CP.get_inisol(x[np.argmin(curr_p)+1], y[np.argmin(curr_p)+1])
                            #curr_p[np.argmin(curr_p)] = CP.get_cpsol(x[np.argmin(curr_p)+1], y[np.argmin(curr_p)+1], Fbid[e][0])
                    for b in ET_del:# update the ET_p
                        ET_p.pop(b,None)
                else:
                    flag72 = 0
            else:
                flag72 = 0

        # Step 7.3
        #问题：没进step7.3
        #解决：因为出现最大值比current price的价格要大，结果就没循环后面的flexible bids，直接退出了
        #修改后，第一步判断ES_p里面是否还有键值对，第二步判断是否存在order符合接收准则，第三步对ES_p的所有order进行循环，测试能否接受
        while flag73 > 0:
            if len(ES_p) > 0:# there are demand flexible bids not rejected
                if min(ES_p.values()) < max(curr_p):
                    ES_del = []
                    for e in ES_p.keys():
                        if ES_p[e] < max(curr_p):
                            FR.remove(e)
                            ES_del.append(e)# add the order id into the ET_del, which means that the key-value need to be deleted in ET_p
                            FK.append(e)
                            F_time[e] = np.argmax(curr_p) + 1 # which hour should flexible bid be accepted
                            # update current price curr_p
                            y[np.argmax(curr_p)+1] = y[np.argmax(curr_p)+1] + Fbid[e][0]#在对应的那一小时里面更新y
                            curr_p[np.argmax(curr_p)] = CP.get_inisol(x[np.argmax(curr_p)+1], y[np.argmax(curr_p)+1])
                            #curr_p[np.argmax(curr_p)] = CP.get_cpsol(x[np.argmax(curr_p)+1], y[np.argmax(curr_p)+1], Fbid[e][0])
                    for b in ES_del:# update the ET_p
                        ES_p.pop(b,None)
                else:
                    flag73 = 0
            else:
                flag73 = 0


        #Step 8 : increment the grand iteration number by 1
        grand_iter_num += 1

    BR = list(BR)
    FR = list(FR)

    # Step 9 final feasibility check
    flag9 = 1
    # calculate the impact value for bids in BR and FR
    while flag9 == 1:
        impact_value_9 = {}
        for b in BR:
            avg_cp = sum(np.array(Delta[b])*curr_p)/Bbid[b][1]
            impact_value_9[b] = (Bbid[b][3] - avg_cp) * Bbid[b][2] * Bbid[b][1]
        for e in FR:
            if e in ET:
                impact_value_9[e] = (Fbid[e][1] - min(curr_p)) * Fbid[e][0]
            else:
                impact_value_9[e] = (Fbid[e][1] - max(curr_p)) * Fbid[e][0]

        # Step 9.1 for all bids in BR and FR, sort the impact value in decreasing order
        sorted_dict = sorted(impact_value_9.items(), key=lambda item: item[1],reverse = True)
        impact_value_9 = dict(sorted_dict)

        # step 9.2 check whether there is bid with positive impact value
        # go to Step 9.2.1
        for b in impact_value_9.keys():
            if impact_value_9[b] > 0:
                if b in Order_id_B:
                    if len(Kb[b]) == 0 or Kb[b] in BK:
                        BR.remove(b)
                        BK.append(b)
                        add_in_9 = b
                        for z in Z:
                            if Delta[add_in_9][z-1] > 0:# z_th hour is impacted by block b
                                y[z] = y[z] + Bbid[add_in_9][2]#在对应的小时里面更新y[z]
                                ans = CP.get_inisol(x[z], y[z])
                                #ans = CP.get_cpsol(x[z], y[z], Bbid[add_in_9][2])
                            else:
                                ans = curr_p[z-1]
                            curr_p[z-1] = ans
                        break
                else:
                    FR.remove(b)
                    FK.append(b)
                    add_in_9 = b
                    if b in ET:
                        F_time[b] = np.argmin(curr_p) + 1
                        y[np.argmin(curr_p)+1] = y[np.argmin(curr_p)+1] + Fbid[add_in_9][0]#更改accept flexible bid的那个小时的y
                        curr_p[np.argmin(curr_p)] = CP.get_inisol(x[z], y[z])
                        #curr_p[np.argmin(curr_p)] = CP.get_cpsol(x[z], y[z], Fbid[add_in_9][0])
                    else:
                        F_time[b] = np.argmax(curr_p) + 1
                        y[np.argmax(curr_p)+1] = y[np.argmax(curr_p)+1] + Fbid[add_in_9][0]
                        curr_p[np.argmax(curr_p)] = CP.get_inisol(x[z], y[z])
                        #curr_p[np.argmax(curr_p)] = CP.get_cpsol(x[z], y[z], Fbid[add_in_9][0])
                    break
            else:
                flag9 = 0
                break
    obj_hourly = OH.Obj_hour(curr_p, L, Z, bid_z)
    obj_block = 0
    for b in BK:
        if b in BT:
            obj_block += Bbid[b][1] * Bbid[b][2] * Bbid[b][3]
        else:
            obj_block -= Bbid[b][1] * (-Bbid[b][2]) * Bbid[b][3]

    for e in FK:
        if e in ET:
            obj_block += Fbid[e][0] * Fbid[e][1]
        else:
            obj_block -= (-Fbid[e][0]) * Fbid[e][1]
    obj = 0
    obj = obj_hourly + obj_block
    
    end_time = time.process_time()
    print('Finish');
    print(' ')

#     elapsed_time_runtime = end_time - start_time
#     print(f'The objective value of {filename} is {obj}')
#     print(f'The running time is of file {filename} is {elapsed_time_runtime}')
#     print(' ')
    return obj