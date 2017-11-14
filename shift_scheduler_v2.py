from gurobipy import *
import csv
import time as time

#import demand data
filename="demand_1";     # read demand data file
r={}
with open(filename+".csv",'r') as infile:
    reader = csv.reader(infile,delimiter=',')
    linectr = 1
    for line in reader:
        r[linectr] = int(line[0])
        linectr += 1

#add parameters
delay = 48              # time between each shift
T = len(r)                # number of 15 minutes long blocks per biweekly pay-period
L = 3                   # number of type of shifts allowed
d = [32, 36, 40]        # duration of a shift of type l schedule
n = [10, 9, 8]          # number of shifts of type l schedule
m = [30, 20, 15]        # number of schedules for each type l schedule
N = sum(m)

#build model
model = Model('shift-line')

#add variables
if L == len(n) and L == len(m):
    try:
        s = {}
        t = {}
        z = {}
        o = {}
        for l in range(1,L+1):
            for i in range(1,n[l-1]+1):
                for j in range(1,m[l-1]+1):
                    s[i,j,l] = model.addVar(
                            lb=1.0,ub=T-((n[l-1]-i+1)*d[l-1]+(n[l-1]-i)*delay),vtype=GRB.INTEGER,name='s[{},{},{}]'.format(i,j,l))
                    t[i,j,l] = model.addVar(
                            lb=1.0,ub=T-((n[l-1]-i)*(d[l-1]+delay)),vtype=GRB.INTEGER,name='t[{},{},{}]'.format(i,j,l))
                    for k in range(1,T+1):
                        z[i,j,k,l] = model.addVar(
                                lb=0.0,ub=1.0,vtype=GRB.BINARY,name='z[{},{},{},{}]'.format(i,j,k,l))

        for u in range(1,T-d[L-1]+2):
            for v in range(u+d[0]-1,u+d[L-1]):
                o[u,v] = model.addVar(lb=0.0,ub=max(r.values()),vtype=GRB.INTEGER,name='o[{},{}]'.format(u,v))
        
        model.update()

#set Objective Functions
        obj = LinExpr(0)
        obj_constant = 0 
        for l in range(1,L+1):
            for i in range(1,n[l-1]+1):
                for j in range(1,m[l-1]+1):
                    obj.addTerms(1,t[i,j,l])
                    obj.addTerms(-1,s[i,j,l])
                    obj_constant += d[l-1]
        for u in range(1,T-d[L-1]+2):
            for v in range(u+d[0]-1,u+d[L-1]):
                obj.addTerms((v - u + 1),o[u,v])
        
        obj -= obj_constant
        model.setObjective(obj,GRB.MINIMIZE)

#add constraints
            # (5)
        for l in range(1,L+1):
            for i in range(1,n[l-1]):
                for j in range(1,m[l-1]+1):
                    model.addConstr(s[i+1,j,l] >= t[i,j,l] + delay, name= 'c05_{}_{}_{}'.format(i,j,l))
            # (6) + (7)
        for l in range(1,L+1):
            for i in range(1,n[l-1]+1):
                for j in range(1,m[l-1]+1):
                    model.addConstr(t[i,j,l] - s[i,j,l] >= d[l-1], name = 'c06_{}_{}_{}'.format(i,j,l))
                    model.addConstr(t[i,j,l] - s[i,j,l] <= d[L-1], name = 'c07_{}_{}_{}'.format(i,j,l))
            # (8)
        for k in range(1,T+1):
            coverage_con = LinExpr(0)
            for l in range(1,L+1):
                for i in range(1,n[l-1]+1):
                    for j in range(1,m[l-1]+1):
                        coverage_con.addTerms(1,z[i,j,k,l])
            for u in range(1,T-d[L-1]+2):
                for v in range(u+d[0]-1,u+d[L-1]):
                    if u <= k and v >= k:
                        coverage_con.addTerms(1,o[u,v])
            model.addConstr(coverage_con >= r[k], name = 'c08_{}'.format(k))
            # (9)
        for l in range(1,L+1):
            for i in range(1,n[l-1]+1):
                for j in range(1,m[l-1]+1):
                    for k in range(1,T+1):
                        model.addConstr(
                                s[i,j,l] <= k*z[i,j,k,l] + (T - (n[l-1] - i + 1)*(d[l-1] + delay))*(1 - z[i,j,k,l]), name = 'c09_{}_{}_{}_{}'.format(i,j,k,l))
            # (10)
                        model.addConstr(
                                t[i,j,l] >= k*z[i,j,k,l] + i*(d[l-1] + delay)*(1 - z[i,j,k,l]), name = 'c10_{}_{}_{}_{}'.format(i,j,k,l))
            # (11)
        for l in range(1,L+1):
            for j in range(1,m[l-1]+1):
                for k in range(1,T+1):
                    model.addConstr(quicksum(z[i,j,k,l] for i in range(1,n[l-1]+1))  <= 1, name = 'c11_{}_{}_{}'.format(j,k,l))
        model.update()

#optimize
        model.Params.TIME_LIMIT = 300     # model running time
        model.Params.MIPFocus = 1           # emphasize feasibility
        model.optimize()

#print out
        timestamp = str(time.localtime().tm_year)+'-'+str(time.localtime().tm_mon)+'-'+str(time.localtime().tm_mday)+'-'+str(time.localtime().tm_hour)+'-'+str(time.localtime().tm_min)+'-'+str(time.localtime().tm_sec)
        
        outfile = open('schedules_overtime'+timestamp+'.csv','w')
        print('\nOptimal: %g'%model.objVal)
        print('number of shifts\n'+
              '8hr:{}'.format(m[0]) +
              '\n9hr:{}'.format(m[1]) +
              '\n10hr:{}'.format(m[2]) +
              '\nTotal:{}'.format(N))
        outfile.write('number of shifts\n'+
                      '8hr,{}'.format(m[0]) +
                      '\n9hr,{}'.format(m[1]) +
                      '\n10hr,{}'.format(m[2]) +
                      '\nTotal,{}'.format(N) + '\n\n')
        for u in range(1,T-d[L-1]+2):
            for v in range(u+d[0]-1,u+d[L-1]):
                if o[u,v].X > 0.5:
                    outfile.write('o,{},{}'.format(u,v)+','+str(round(o[u,v].X))+'\n')
        outfile.write("i,j,l,s,t\n")
        for l in range(1,L+1):
            for j in range(1,m[l-1]+1):
                for i in range(1,n[l-1]+1):
                    outfile.write('{},{},{}'.format(l,j,i)+','+str(round(s[i,j,l].X))+",")
                    outfile.write(str(round(t[i,j,l].X))+'\n')
        outfile.close()
        outfile = open('z_indicators'+timestamp+'.csv','w')
        outfile.write("l,j,i,k\n")
        for l in range(1,L+1):
            for j in range(1,m[l-1]+1):
                for i in range(1,n[l-1]+1):
                    for k in range(1,T+1):
                        if z[i,j,k,l].X > 0.5:
                            outfile.write('{},{},{},{}'.format(l,j,i,k)+'\n')
        outfile.close()
    except ValueError:
        print()
else:
    print('L is not paired with n and m, parameters are missing')
