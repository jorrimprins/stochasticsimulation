import time
import numpy as np
import pandas as pd
import warnings
import scipy
from sklearn.metrics import mean_squared_error, mean_absolute_error
import random
warnings.filterwarnings('ignore')

seedy = 12345
reps = 25
df = pd.read_csv("predator-prey-data.csv")
t = df.values[:,0]
data_full = (df.values[:,1],df.values[:,2])
data = (df.values[:,1],df.values[:,2])
start = time.time()
n_iter = 5000

# n_gen=1
# popsize=2
# n_parents=2
# p_mutate=0.3

#Create functions
def get_ODE(data, t, alpha, beta, gamma, delta):
    """Returns set of ODE's for given data and params."""

    # data should be array-like of prey and predator quantities respectively
    # params should be array-like of 4 params (alpha, beta, gamma, delta)
    x, y = data[0], data[1]
    dxdt = alpha * x - beta * x * y
    dydt = delta * x * y - gamma * y
    return [dxdt, dydt]

def ODE_error(params,data,t,evalfunc='RMSE',indexdata='full'):
    """Solves set of ODE's for given data and params."""

    # data should be array-like of prey and predator quantities respectively
    # ODE should be function that returns ODE's
    # params should be array-like of 4 params (alpha, beta, gamma, delta)

    init = np.array([data[0][0],data[1][0]])
    if indexdata == 'full':
        index_x, index_y = np.arange(0, len(t)), np.arange(0, len(t))
    else:
        index_x, index_y = indexdata[0], indexdata[1]
    est = scipy.integrate.odeint(get_ODE, init, t, args=tuple(params))

    if evalfunc == 'MSE':
        error_x = mean_squared_error(est[index_x,0],data[0])
        error_y = mean_squared_error(est[index_y,1],data[1])
        error = np.mean([error_x,error_y])
    elif evalfunc == 'RMSE':
        error_x = mean_squared_error(est[index_x, 0], data[0],squared=False)
        error_y = mean_squared_error(est[index_y, 1], data[1],squared=False)
        error = np.mean([error_x, error_y])
    else:
        error_x = mean_absolute_error(est[index_x, 0], data[0])
        error_y = mean_absolute_error(est[index_y, 1], data[1])
        error = np.mean([error_x, error_y])
    return error

def hillclimber(function, data,t,params0=(0,0,0,0),evalfunc='RMSE',n_iter=1000,stepsize=0.5,indexdata='full'):
    """Finds optimum by using hill climber algorithm (local search)"""

    est_params = params0
    try: est_eval = function(params0, data, t, evalfunc,indexdata=indexdata)
    except ValueError: est_eval = 100
    eval_list = [est_eval]
    for iter in range(n_iter):
        new_params = np.array(est_params) + np.random.uniform(-1,1,len(params0))*stepsize
        new_params[new_params < 0] = 0
        new_params[new_params > 10] = 10

        try: new_eval  = function(new_params,data,t,evalfunc,indexdata=indexdata)
        except ValueError: new_eval = 100
        if new_eval <= est_eval:
            est_params, est_eval = new_params, new_eval
        eval_list.append(est_eval)
    return (est_eval, est_params, eval_list)

def sim_an(function,data,t,params0=(0,0,0,0),evalfunc='RMSE',stepsize=0.25,
                        temprange=(10**0,10**-3),n_iter=5000,cooling='quadratic',n_inner=50,indexdata='full'):
    """Performs simulated annealing to find a global solution"""
    temp0 = temprange[0]
    temp_end = temprange[1]
    if cooling == 'exponential':
        rate = (temp_end / temp0) ** (1 / (n_iter/n_inner - 1))
    elif cooling == 'linear':
        rate = (temp0-temp_end)/(n_iter/n_inner)
    else:
        alpha = (temp0 / temp_end - 1) / (n_iter/n_inner) ** 2

    est_params = params0
    try: est_eval = function(params0, data, t, evalfunc,indexdata=indexdata)
    except ValueError: est_eval = 100
    eval_list = [est_eval]
    epoch = 0
    temp = temp0

    for i in range(int(n_iter/n_inner)):
        inner_params, inner_eval = est_params, est_eval
        for j in range(n_inner):
            new_params = np.array(inner_params) + np.random.uniform(-1,1,len(params0))*stepsize
            new_params[new_params < 0] = 0
            new_params[new_params > 10] = 10
            try: new_eval = function(new_params, data, t, evalfunc,indexdata=indexdata)
            except ValueError: new_eval = 100
            delta_eval = new_eval - inner_eval
            if delta_eval < 0:
                inner_params, inner_eval = new_params, new_eval
            elif np.random.uniform(0, 1) < np.exp(-delta_eval / temp):
                inner_params, inner_eval = new_params, new_eval
        est_params, est_eval = inner_params, inner_eval
        eval_list.append(est_eval)
        epoch += 1
        if cooling == 'exponential':
            temp *= rate
        elif cooling == 'linear':
            temp -= rate
        else:
            temp = temp0 / (1 + alpha * i ** 2)

    return (est_eval, est_params, eval_list)

# Estimating the models and its parameters on full data, see convergence behavior and performance

np.random.seed(seedy)
for eval in ['RMSE','MAE']: # Loop over both evaluation methods
    start1 = time.time()
    HC05, HC10, HC_start1, HC_start2 = [], [], [], []
    HC05_conv, HC10_conv, HC_start1_conv, HC_start2_conv = np.repeat(0, n_iter), np.repeat(0, n_iter),\
                                                                                 np.repeat(0, n_iter), np.repeat(0, n_iter)
    SA01, SA025, SA05, SA10, SA40, SA25, SA100 = [], [], [], [], [], [], []
    SA01_conv, SA025_conv, SA05_conv, SA10_conv, SA40_conv, SA25_conv, SA100_conv = np.repeat(0, n_iter), np.repeat(0,n_iter), \
                                                                                 np.repeat(0, n_iter), np.repeat(0,n_iter), \
                                                                                 np.repeat(0, n_iter), np.repeat(0,n_iter),\
                                                                                    np.repeat(0,n_iter)
    SA_exp, SA_lin, SA_init10, SA_init01, SA_init005 = [], [], [], [], []
    SA_exp_conv, SA_lin_conv, SA_init10_conv, SA_init01_conv, SA_init005_conv = np.repeat(0, n_iter), np.repeat(0,n_iter),np.repeat(0, n_iter), \
                                                               np.repeat(0,n_iter), np.repeat(0, n_iter)
    for i in range(reps):
        print('REPLICATION {}'.format(i))
        #1. Stepsize experiments Hill climber
        RMSE, params, RMSE_list = hillclimber(ODE_error, data, t,n_iter=n_iter,stepsize=0.5,evalfunc=eval)
        HC05.append(RMSE)
        HC05_conv = [x + y  for x, y in zip(HC05_conv, np.array(RMSE_list)/reps)]
        if i == 0: params_HC05 = params
        elif RMSE < HC05[i-1]: params_HC05 = params
        print('HC .5 DONE')
        print('Run {} with {} took {} seconds'.format(i,eval,time.time()-start1))

        RMSE, params, RMSE_list = hillclimber(ODE_error, data, t, n_iter=n_iter, stepsize=1,evalfunc=eval)
        HC10.append(RMSE)
        HC10_conv = [x + y for x, y in zip(HC10_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_HC10 = params
        elif RMSE < HC10[i - 1]: params_HC10 = params
        print('HC 1 DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))

        #2. Starting value experiments HC
        RMSE, params, RMSE_list = sim_an(ODE_error, data, t,n_iter=n_iter,params0=(1,1,1,1),evalfunc=eval)
        HC_start1.append(RMSE)
        HC_start1_conv = [x + y for x, y in zip(HC_start1_conv, np.array(RMSE_list)/reps)]
        if i == 0: params_HC_start1 = params
        elif RMSE < HC_start1[i-1]: params_HC_start1 = params
        print('HC 1,1,1,1 DONE')
        print('Run {} with {} took {} seconds'.format(i,eval,time.time()-start1))

        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, params0=(2, 2, 2, 2),evalfunc=eval)
        HC_start2.append(RMSE)
        HC_start2_conv = [x + y for x, y in zip(HC_start2_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_HC_start2 = params
        elif RMSE < HC_start2[i - 1]: params_HC_start2 = params
        print('HC 2,2,2,2 DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))

        #3. Stepsize experiments for Simulated Annealing
        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter,stepsize=0.1,evalfunc=eval)
        SA01.append(RMSE)
        SA01_conv = [x + y for x, y in zip(SA01_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_SA01 = params
        elif RMSE < SA01[i - 1]: params_SA01 = params
        print('SA .1 DONE')
        print('Run {} with {} took {} seconds'.format(i,eval,time.time()-start1))

        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, stepsize=0.25,evalfunc=eval)
        SA025.append(RMSE)
        SA025_conv = [x + y for x, y in zip(SA025_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_SA025 = params
        elif RMSE < SA025[i - 1]: params_SA025 = params
        print('SA .25 DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))

        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, stepsize=0.5,evalfunc=eval)
        SA05.append(RMSE)
        SA05_conv = [x + y for x, y in zip(SA05_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_SA05 = params
        elif RMSE < SA05[i - 1]: params_SA05 = params
        print('SA .5 DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))

        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, stepsize=1,evalfunc=eval)
        SA10.append(RMSE)
        SA10_conv = [x + y for x, y in zip(SA10_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_SA10 = params
        elif RMSE < SA10[i - 1]: params_SA10 = params
        print('SA 1 DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))

        # 4. Markov chain experiments with SA
        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, n_inner=25,evalfunc=eval)
        SA25.append(RMSE)
        SA25_conv = [x + y for x, y in zip(SA25_conv, np.array(RMSE_list) / reps)]
        if i == 0:
            params_SA25 = params
        elif RMSE < SA25[i - 1]:
            params_SA25 = params
        print('SA 25 DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))

        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, n_inner=40,evalfunc=eval)
        SA40.append(RMSE)
        SA40_conv = [x + y for x, y in zip(SA40_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_SA40 = params
        elif RMSE < SA40[i - 1]: params_SA40 = params
        print('SA 40 DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))

        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, n_inner=100,evalfunc=eval)
        SA100.append(RMSE)
        SA100_conv = [x + y for x, y in zip(SA100_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_SA100 = params
        elif RMSE < SA100[i - 1]: params_SA100 = params
        print('SA 100 DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))

        # 7. Cooling schedule experiments for SA
        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, cooling='linear',evalfunc=eval)
        SA_lin.append(RMSE)
        SA_lin_conv = [x + y for x, y in zip(SA_lin_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_SA_lin = params
        elif RMSE < SA_lin[i - 1]: params_SA_lin = params
        print('SA linear DONE')
        print('Run {} with {} took {} seconds'.format(i,eval,time.time()-start1))

        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, cooling='exponential',evalfunc=eval)
        SA_exp.append(RMSE)
        SA_exp_conv = [x + y for x, y in zip(SA_exp_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_SA_exp = params
        elif RMSE < SA_exp[i - 1]: params_SA_exp = params
        print('SA exp DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))

        # 8. Starting temperature experiments for SA
        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter,temprange=(10**1,10**-3),evalfunc=eval)
        SA_init10.append(RMSE)
        SA_init10_conv = [x + y for x, y in zip(SA_init10_conv, np.array(RMSE_list) / reps)]
        if i == 0: params_SA_init10 = params
        elif RMSE < SA_init10[i - 1]: params_SA_init10 = params
        print('SA init10 DONE')
        print('Run {} with {} took {} seconds'.format(i,eval,time.time()-start1))

        RMSE, params, RMSE_list = sim_an(ODE_error, data, t, n_iter=n_iter, temprange=(10 ** -1, 10 ** -3),evalfunc=eval)
        SA_init01.append(RMSE)
        SA_init01_conv = [x + y for x, y in zip(SA_init01_conv, np.array(RMSE_list) / reps)]
        if i == 0:
            params_SA_init01 = params
        elif RMSE < SA_init01[i - 1]:
            params_SA_init01 = params
        print('SA init01 DONE')
        print('Run {} with {} took {} seconds'.format(i, eval, time.time() - start1))


    HC_convs = [HC05_conv, HC10_conv, HC_start1_conv, HC_start2_conv]
    for j in range(len(HC_convs)):
        if len(HC_convs[j]) < n_iter:
            HC_convs[j].extend(list(np.zeros(n_iter-len(HC_convs[j]))))


    SA01_conv = np.array([np.repeat(SA01_conv[i + 1], 50) for i in np.arange(0, len(SA01_conv) - 1)]).reshape(n_iter)
    SA025_conv = np.array([np.repeat(SA025_conv[i + 1], 50) for i in np.arange(0, len(SA025_conv) - 1)]).reshape(n_iter)
    SA05_conv = np.array([np.repeat(SA05_conv[i + 1], 50) for i in np.arange(0, len(SA05_conv) - 1)]).reshape(n_iter)
    SA10_conv = np.array([np.repeat(SA10_conv[i + 1], 50) for i in np.arange(0, len(SA10_conv) - 1)]).reshape(n_iter)
    SA25_conv = np.array([np.repeat(SA25_conv[i + 1], 25) for i in np.arange(0, len(SA25_conv) - 1)]).reshape(n_iter)
    SA40_conv = np.array([np.repeat(SA40_conv[i + 1], 40) for i in np.arange(0, len(SA40_conv) - 1)]).reshape(n_iter)
    SA100_conv = np.array([np.repeat(SA100_conv[i + 1], 100) for i in np.arange(0, len(SA100_conv) - 1)]).reshape(n_iter)
    SA_lin_conv = np.array([np.repeat(SA_lin_conv[i + 1], 50) for i in np.arange(0, len(SA_lin_conv) - 1)]).reshape(n_iter)
    SA_exp_conv = np.array([np.repeat(SA_exp_conv[i + 1], 50) for i in np.arange(0, len(SA_exp_conv) - 1)]).reshape(n_iter)
    SA_init10_conv = np.array([np.repeat(SA_init10_conv[i + 1], 50) for i in np.arange(0, len(SA_init10_conv) - 1)]).reshape(n_iter)
    SA_init01_conv = np.array([np.repeat(SA_init01_conv[i + 1], 50) for i in np.arange(0, len(SA_init01_conv) - 1)]).reshape(n_iter)

    #Create dataframes and save
    error_dict = {'HC05': HC05,'HC10': HC10,'HC_start1': HC_start1, 'HC_start2': HC_start2,
                 'SA01': SA01,'SA025': SA025, 'SA05': SA05,'SA10': SA10,'SA25':SA25,'SA40': SA40, 'SA100': SA100,
                 'SA_exp': SA_exp,'SA_lin': SA_lin, 'SA_init10': SA_init10,'SA_init01':SA_init01}
    conv_dict = {'HC05': HC05_conv, 'HC10': HC10_conv,'HC_start1': HC_start1_conv,
                 'HC_start2': HC_start2_conv,'SA01': SA01_conv, 'SA025': SA025_conv, 'SA05': SA05_conv, 'SA10': SA10_conv,'SA25': SA25_conv,
                 'SA40': SA40_conv, 'SA100': SA100_conv,'SA_exp': SA_exp_conv, 'SA_lin': SA_lin_conv, 'SA_init10': SA_init10_conv,
                 'SA_init01': SA_init01_conv}
    param_dict = {'HC05': params_HC05, 'HC10': params_HC10,'HC_start1': params_HC_start1,
                  'HC_start2': params_HC_start2,'SA01': params_SA01, 'SA025': params_SA025, 'SA05': params_SA05, 'SA10': params_SA10,
                  'SA25':params_SA25,'SA40': params_SA40, 'SA100': params_SA100,'SA_exp': params_SA_exp, 'SA_lin': params_SA_lin,
                  'SA_init10': params_SA_init10, 'SA_init01': params_SA_init01}
    pd.DataFrame(error_dict).to_csv('{}.csv'.format(eval))
    pd.DataFrame(conv_dict).to_csv('{}-conv.csv'.format(eval))
    pd.DataFrame(param_dict).to_csv('{}-params.csv'.format(eval))

print('Simulations with varying startvalues and cooling took {} seconds'.format(time.time()-start))

# ## Estimating the three models and its parameters on part of data, see convergence behavior and performance
sizes = np.arange(100,0,-10)
shortlist = ['lessx','lessy','lessboth','onlypeaks','nopeaks']

for eval in ['RMSE', 'MAE']:
    print('Runs with {} as evaluation function'.format(eval))# Loop over both evaluation methods
    for short in shortlist:
        HC, SA = [], []
        HC_std, SA_std = [], []
        for s in sizes:
            print('SAMP SIZE {}'.format(s))
            if short == 'lessx':
                index_x = np.sort(np.append(np.random.choice(np.arange(1, 99), s - 2), np.array([0, 99])))
                index_y = np.arange(0, 100)
            elif short == 'lessy':
                index_y = np.sort(np.append(np.random.choice(np.arange(1, 99), s - 2), np.array([0, 99])))
                index_x = np.arange(0, 100)
            elif short == 'lessboth':
                index_x = np.sort(np.append(np.random.choice(np.arange(1, 99), s - 2), np.array([0, 99])))
                index_y = np.sort(np.append(np.random.choice(np.arange(1, 99), s - 2), np.array([0, 99])))
            elif short == 'onlypeaks':
                index_x = np.sort(np.append(np.where(data[0] > 2), np.array([0, 99])))
                index_y = np.sort(np.append(np.where(data[1] > 2), np.array([0, 99])))
            else:
                index_x = np.sort(np.append(np.where(data[0] < 2), np.array([0, 99])))
                index_y = np.sort(np.append(np.where(data[1] < 2), np.array([0, 99])))
            indexdata = (index_x, index_y)
            shortdata = (data[0][index_x], data[1][index_y])

            HC_sample, SA_sample = [], []
            for i in range(reps):
                #1. Hill climber
                print('REP {}'.format(i))
                RMSE, params, RMSE_list = hillclimber(ODE_error, shortdata, t,n_iter=n_iter,indexdata=indexdata,evalfunc=eval)
                error = ODE_error(params,data,t,evalfunc=eval)
                HC_sample.append(error)

                #2. Simulated Annealing
                if eval == 'RMSE':
                    RMSE, params, RMSE_list = sim_an(ODE_error, shortdata, t, n_iter=n_iter, indexdata=indexdata,
                                                     temprange=(10 ** -1, 10 ** -3),evalfunc=eval)
                else:
                    RMSE, params, RMSE_list = sim_an(ODE_error, shortdata, t,n_iter=n_iter,indexdata=indexdata,n_inner=40,
                                                          temprange=(10 ** 1, 10 ** -3),evalfunc=eval)
                error = ODE_error(params, data, t, evalfunc=eval)
                SA_sample.append(RMSE)

            HC.append(np.mean(HC_sample))
            HC_std.append(np.std(HC_sample))
            SA.append(np.mean(SA_sample))
            SA_std.append(np.std(SA_sample))
            if short in ['onlypeaks', 'nopeaks']:
                break
        RMSE_dict = {'HC_mean':HC,'HC_std':HC_std,'SA_mean':SA,'SA_std':SA_std}
        pd.DataFrame(RMSE_dict).to_csv('fracdata-{}-{}.csv'.format(short,eval))



print('Simulations took {} seconds'.format(time.time()-start))

#3. Genetic Algorithm
#         RMSE, params, pop, RMSE_list_best, RMSE_list_avg = gen_al(ODE_error, data, t, n_gen=n_gen)
#         RMSE_GA.append(RMSE)
#         RMSE_GA_conv = [x + y for x, y in zip(RMSE_GA_conv, np.array(RMSE_list_best) / reps)]
#         RMSE_GA_conv2 = [x + y for x, y in zip(RMSE_GA_conv2, np.array(RMSE_list_avg) / reps)]
#         if i == 0:
#             params_GA = params
#         elif RMSE < RMSE_GA[i - 1]:
#             params_GA = params
#     #Create dataframes and save
#     RMSE_dict = {'HC':RMSE_HC,'SA':RMSE_SA,'GA':RMSE_GA}
#     pd.DataFrame(RMSE_dict).to_csv('Data/{}-overall-{}.csv'.format(name,eval))
#     RMSE_dict = {'HC':RMSE_HC_conv,'SA':RMSE_SA_conv}
#     pd.DataFrame(RMSE_dict).to_csv('Data/{}-avg-conv-{}.csv'.format(name,eval))
#     pd.DataFrame({'GA':RMSE_GA_conv}).to_csv('Data/{}-avg-conv-GA-{}.csv'.format(name,eval))
#     param_dict = {'HC':params_HC,'SA':params_SA,'GA':params_GA}
#     pd.DataFrame(param_dict).to_csv('Data/{}-best-params-{}.csv'.format(name,eval))


def gen_al(function,data,t,evalfunc='RMSE',popsize=50,n_gen=25,
           n_parents=30,p_mutate=0.3):
    """Performs simulated annealing to find a solution"""
    pop = np.random.uniform(0, 2, (popsize,4))
    pop_eval = np.zeros(popsize)
    for p in range(popsize):
        try: pop_eval[p] = function(pop[p], data, t, evalfunc)
        except ValueError: pop_eval[p] = 100
    eval_list1 = [min(pop_eval)]
    eval_list2 = [np.mean(pop_eval)]

    epoch = 0

    for i in range(n_gen):
        sort_eval = list(np.sort(pop_eval))
        parents = []
        for j in range(n_parents):
            parents.append(np.where(pop_eval == sort_eval[j])[0][0])
        random.shuffle(parents)

        for j in range(int(len(parents) / 2)):
            for k in range(np.random.randint(1, 4)):
                alpha = np.random.uniform(0, 1)
                offspring = alpha * pop[parents[j]] + (1 - alpha) * pop[parents[j + int(len(parents) / 2)]]
                if np.random.uniform(0, 1) <= p_mutate:
                    offspring += np.random.normal(0, 1, 4)/20
                    offspring[offspring < 0] = 0
                pop = np.vstack((pop, offspring))
        pop_eval = np.zeros(pop.shape[0])
        for p in range(pop.shape[0]):
            try: pop_eval[p] = function(pop[p], data, t, evalfunc)
            except ValueError: pop_eval[p] = 100
        sort_eval = list(np.sort(pop_eval))
        index = []
        for j in range(popsize):
            index.append(np.where(pop_eval == sort_eval[j])[0][0])
        pop = pop[index]
        pop_eval = sort_eval[0:popsize]
        best_eval = min(pop_eval)
        best_params = pop[np.where(pop_eval == best_eval)[0][0]]
        eval_list1.append(best_eval)
        eval_list2.append(np.mean(pop_eval))
        epoch += 1
        # print(epoch)

    return (best_eval, best_params, pop,eval_list1,eval_list2)