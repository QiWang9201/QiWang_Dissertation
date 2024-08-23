import pandas as pd
import numpy as np
import time
import gurobipy as gp
from gurobipy import GRB

def AEPRB(filename):
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
        Bbid[i] = [df[df.loc[:,'Order_id'] == i].loc[:,'Hour_start'].values[0],df[df.loc[:,'Order_id'] == i].loc[:,'Hour_Covered'].values[0],abs(df[df.loc[:,'Order_id']==i]['Quantity'].values[0]),df[df.loc[:,'Order_id']==i]['Price'].values[0]]

    # Define Fbid (the information of each flexible bid e)
    # Form Fbid[e] = [Quantity,price]
    Fbid = {}
    for i in Order_id_F:
        Fbid[i] = [abs(df[df.loc[:,'Order_id']==i]['Quantity'].values[0]),df[df.loc[:,'Order_id']==i]['Price'].values[0]]

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

    # Define set of block bids without child block bids: no_child_S (Supply) and no_child_T (Demand)
    no_child_S = set(BS)-set(Bsc)
    no_child_T = set(BT)-set(Btc)

    # Output information about the data set
    print(f'The number of hourly bid is {len(Order_id_S)}')
    print(f'The number of block bids is {len(Order_id_B)}')
    print(f'The number of flexible bids is {len(Order_id_F)}')
    print(f'The number of linked block bids is {len(Bsc)+len(Btc)}')


    # Initialize Model
    m_exact = gp.Model('Exact Model')

    # Define the variables
    # x[z,b,i] : accpected fraction of segment i for hourly bid b in period z
    # w[z,b,i] : auxiliary variables
    # range of z:1-24, range of i: 0 to number of segments-1
    x = {}
    w = {}
    for z in Z:
        for l in bid_z[z]:
            for b in l:
                for i in range(L[b][0]):
                    x[z,b,i] = m_exact.addVar(name='x_%s,%s,%s'%(str(z),str(b),str(i+1)),lb=0,ub=1)
                    w[z,b,i] = m_exact.addVar(name='w_%s,%s,%s'%(str(z),str(b),str(i+1)),vtype = GRB.BINARY)

    # y[b] : whether block bid b is accepted
    y = m_exact.addVars(Order_id_B,name = 'y',vtype = GRB.BINARY)

    # v[e,z]: whether flexible bid e is accepted at time z
    v = m_exact.addVars(Order_id_F,Z,name = 'v',vtype = GRB.BINARY)

    # f[z] : market clearing price at time z
    f = m_exact.addVars(Z,name="f",lb = 0)

    # L[b][0]: number of segments for hourly bid b
    # L[b][1]：the quantity list of hourly bid b
    # L[b][2]：the price list of hourly bid b

    # bid_z[z][0]: the order_id of demand hourly bids in time period z
    # bid_z[z][1]: the order_id of supply hourly bids in time period z

    #Bbid[b][0]: the start time of block bid b
    #Bbid[b][1]: the during time of block bid b
    #Bbid[b][2]: the quantity of block bid b
    #Bbid[b][3]: the price of block bid b

    #Fbid[e][0]: the quantity of flexible bid e
    #Fbid[e][1]: the price of flexible bid e

    #Define the Objective
    # objective_S : the components in Objective corresponding to hourly bids
    objective_S = gp.quicksum(0.5 * ( 2*L[b][2][i] + x[z,b,i] * (L[b][2][i+1]-L[b][2][i]) ) * x[z,b,i] * (L[b][1][i+1]-L[b][1][i]) for z in Z for b in bid_z[z][0] for i in range(L[b][0]))
    objective_S = objective_S - gp.quicksum(0.5 * ( 2*L[b][2][i] + x[z,b,i] * (L[b][2][i+1]-L[b][2][i]) ) * x[z,b,i] * (L[b][1][i+1]-L[b][1][i]) for z in Z for b in bid_z[z][1] for i in range(L[b][0]))

    # objective_S : the components in Objective corresponding to block bids
    objective_B = gp.quicksum( Bbid[i][1] * Bbid[i][2] * Bbid[i][3] * y[i] for i in BT)
    objective_B = objective_B - gp.quicksum(Bbid[i][1] * Bbid[i][2] * Bbid[i][3] * y[i] for i in BS)

    # objective_S : the components in Objective corresponding to flexible bids
    objective_F = gp.quicksum( Fbid[i][0] * Fbid[i][1] * gp.quicksum(v[i,z] for z in Z) for i in ET)
    objective_F = objective_F - gp.quicksum( Fbid[i][0] * Fbid[i][1] * gp.quicksum(v[i,z] for z in Z) for i in ES)

    objective = objective_S + objective_B + objective_F

    m_exact.setObjective(objective, sense=GRB.MAXIMIZE)

    # Add the constraints
    # Supply-Demand Balance
    m_exact.addConstrs((gp.quicksum((L[b][1][i+1] - L[b][1][i]) * x[z,b,i] for b in bid_z[z][1] for i in range(L[b][0])) - gp.quicksum( (L[b][1][i+1]-L[b][1][i]) * x[z,b,i] for b in bid_z[z][0] for i in range(L[b][0])) 
                       + gp.quicksum(L[b][1][0] for b in bid_z[z][1]) - gp.quicksum(L[b][1][0] for b in bid_z[z][0])
                       + gp.quicksum(Delta[b][z-1] * Bbid[b][2] * y[b] for b in BS) - gp.quicksum(Delta[b][z-1] * Bbid[b][2] * y[b] for b in BT) 
                       + gp.quicksum(Fbid[b][0] * v[b,z] for b in ES) - gp.quicksum(Fbid[b][0] * v[b,z] for b in ET) == 0) for z in Z);

    # piecewise linear nature of hourly bids
    m_exact.addConstrs(w[z,b,0] <= x[z,b,0] for z in Z for l in (tuple(x) for x in bid_z[z]) for b in l);
    m_exact.addConstrs(w[z,b,i+1] <= x[z,b,i+1] for z in Z for l in (tuple(x) for x in bid_z[z]) for b in l for i in range(L[b][0]-2));
    m_exact.addConstrs(w[z,b,i] >= x[z,b,i+1] for z in Z for l in (tuple(x) for x in bid_z[z]) for b in l for i in range(L[b][0]-2));
    m_exact.addConstrs(x[z,b,L[b][0]-1] <= w[z,b,L[b][0]-2] for z in Z for l in (tuple(x) for x in bid_z[z]) for b in l);

    # the clearing price in hour z
    # Supply
    m_exact.addConstrs(f[z] == F[z][0] + gp.quicksum((L[b][2][i+1]-L[b][2][i]) * x[z,b,i] for i in range(L[b][0])) for z in Z for b in bid_z[z][1]);
    # Demand
    m_exact.addConstrs(f[z] == F[z][1] + gp.quicksum((L[b][2][i+1]-L[b][2][i]) * x[z,b,i] for i in range(L[b][0])) for z in Z for b in bid_z[z][0]);

    # block accpetance rule(PRB)
    m_exact.addConstrs( Bbid[b][1] * Bbid[b][3] - gp.quicksum(Delta[b][z-1] * f[z] for z in Z) <= Gam * (1-y[b]) for b in no_child_S);
    m_exact.addConstrs( -Bbid[b][1] * Bbid[b][3] + gp.quicksum(Delta[b][z-1] * f[z] for z in Z) <= Gam * (1-y[b]) for b in no_child_T);

    # whether accept linked bids
    for b in Order_id_B:
        if Kb[b].size > 0:
            m_exact.addConstrs(y[b] <= y[k] for k in Kb[b])

    # limit the acceptance of a flexible bid to a maximum of one period(PRB)
    m_exact.addConstrs(gp.quicksum(v[b,z] for z in Z) <= 1 for b in Order_id_F);
    m_exact.addConstrs(f[z] - Fbid[b][1] <= Gam * (1 - v[b,z]) for b in ET for z in Z);
    m_exact.addConstrs(-f[z] + Fbid[b][1] <= Gam * (1 - v[b,z]) for b in ES for z in Z);

    m_exact.update()

    m_exact.setParam('Outputflag',0)
    
    print('Start soloving model');
    start_time = time.process_time()
    m_exact.optimize()
    end_time = time.process_time()
    print('Finish');

    elapsed_time_runtime = end_time - start_time
    print(f'The objective value is {m_exact.objVal}');
    print(f'The running time is of file {filename} is {elapsed_time_runtime}');
    m_exact.write('PRB' + filename[-5:-3] + '.sol') 
    # for z in Z:
    #     print(f'The price in hour {z} is {f[z]}');