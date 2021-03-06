# -*- coding: utf-8 -*-
#!/usr/bin/env python

import numpy as np
#from numpy import linalg
import scipy as sp
import dill as pickle

from numba import jit

# normalized root mean square between two time series
# output: actual output of network
# target: desired output of network)
def nrmse(output,target):
    combinedVar = 0.5 * (np.var(target, ddof=1) + np.var(output, ddof=1))
    errorSignal = output - target
    return np.sqrt(np.mean(errorSignal ** 2) / combinedVar)

# generates internal weights for the network
# nInternalUnits: how many units N x N
# connectivity: percentage of connections
def generateInternalWeights(nInternalUnits, connectivity):
    success = False
    internalWeights = 0
    while success == False:
        try:
            internalWeights = np.random.randn(nInternalUnits,nInternalUnits) * (np.random.random((nInternalUnits,nInternalUnits)) < connectivity)
            specRad = abs(np.linalg.eig(internalWeights)[0][0]) ## MB: why abs? then always 0 or greater
            if (specRad > 0):                                   ## MB: or is this just checking greater than 0?
                internalWeights = internalWeights / specRad
                success = True
        except e:
            print(e)
    return internalWeights

def loadObject(filename):
    with open(filename, "rb") as input_file:
        restored = pickle.load(input_file)
    return restored

def createState(net):
    return {'x':np.zeros((net['p']['N'],1)),
           'xOld':np.zeros((net['p']['N'],1)),
           'evidence':np.zeros(4)}



@jit
def iterateClassifier(net, state, u):
    state['xOld'] = state['x']
    Wtarget = (net['net']['W'].dot(state['x'])) + (net['net']['Win'].dot(u))
    state['x'] = ((1.0-net['p']['LR']) * state['xOld']) + (net['p']['LR'] * np.tanh(Wtarget + net['net']['Wbias']))
    C = net['Cs'][0,0]
    C2 = net['Cs'][0,1]
    x = state['x']

    #state['evidence'][0] = x.T.dot(C.dot(x)) + x.T.dot((1.0-C2).dot(x)) #is p1, not p2
    #state['evidence'][1] = x.T.dot(C2.dot(x)) + x.T.dot((1.0-C).dot(x)) #is p2, no1 p1
    #state['evidence'][2] = x.T.dot((1.0 - C2).dot(x)) + x.T.dot((1.0-C).dot(x)) #not p1 + not p2
    state['evidence'][0] = x.T.dot(C.dot(x)) #is p1
    state['evidence'][1] = x.T.dot(C2.dot(x)) #is p2
    state['evidence'][2] = x.T.dot((1.0-C).dot(x)) #not p1
    state['evidence'][3] = x.T.dot((1.0 - C2).dot(x)) #n not p2
    return state



#pattern generation

def createGeneratorState(net):
    return {
        'x':0.5 * np.random.randn(net['p']['N'],1),
        'xOld':np.zeros((net['p']['N'],1)),
        'output':0.0
    }

def iterateGenerator(net, state, mixArray, excitation, leakrate):
    #conceptor mix
#     C = (net['Cs'][0,0].dot(mix1)) + (net['Cs'][0,1].dot((mix2)))
    leak = leakrate * net['p']['LR']
    C = np.zeros_like(net['Cs'][0,0])
    for i_morph, morph in enumerate(mixArray):
        C = C + (net['Cs'][0,i_morph].dot( morph ))
    #excitation
    Wsr = net['net']['W'].dot(excitation)
    #update reservoir
    state['xOld'] = state['x']
    Wtarget = Wsr.dot(state['x'])
    state['x'] = ((1.0-leak) * state['xOld']) + (leak * np.tanh(Wtarget + net['net']['Wbias']))
    #apply mixed conceptor
    state['x'] = C.dot(state['x'])
    #compute output layer
    state['output'] = net['net']['Wout'].dot(np.concatenate((state['x'][:,0], np.array([1]))))
    return state

def randomiseNetworkState(net, state):
    state['x'] = np.random.rand(net['p']['N'],1)
    return state

# state = createGeneratorState(cnet2)
# state = iterateGenerator(cnet2, state, np.array([0.0, 1.0]), 1.0)
# state['output']

# state = randomiseNetworkState(net, state)

# state = createState(restored)
# state = iterateClassifier(restored, state, 0.4)
# state['evidence']


# make a network
# p is a set of parameters, like
#params = {
    # 'N':30, # size of RNN
    # 'NetSR':1.6,
    # 'NetinpScaling':1.6,
    # 'BiasScaling':0.3,
    # 'TychonovAlpha':0.0001,
    # 'TychonovAlphaReadout':0.0001,
    # 'washoutLength':100,
    # 'learnLength':500,
    # 'learnLengthWout':500,
    # 'recallTestLength':100,
    # 'alphas':np.array([12.0,24.0]),
    # 'patts':np.array([pJ1b, pJ2])
#}
# def makeNetwork(p):
#     NetConnectivity = 1 # just for small networks
#     if p['N'] > 20:
#         NetConnectivity = 10.0/p['N'];
#     WstarRaw = generateInternalWeights(p['N'], NetConnectivity)
#     WinRaw = np.random.randn(p['N'], 1)
#     WbiasRaw = np.random.randn(p['N'], 1)
#
#     #Scale raw weights
#     Wstar = p['NetSR'] * WstarRaw;
#     Win = p['NetinpScaling'] * WinRaw;
#     Wbias = p['BiasScaling'] * WbiasRaw;
#     I = np.eye(p['N']) # identity matrix
#
#     xCollector = np.zeros((p['N'], p['learnLengthWout'])) # variable to collect states of x
#     pCollector = np.zeros((1, p['learnLengthWout'])) # variable to collect states of p (output?)
#     x = np.zeros((p['N'],1)) # initial state
#
#     # first training: washout is to wash out the input state 'noise'; learnLength is then the actual amount of learning samples
#     for n in np.arange(p['washoutLength'] + p['learnLength']):
#         u = np.random.randn() * 1.5  # random input
#         x = np.tanh((Wstar * x) + (Win * u + Wbias)) # calculate next internal activation
#         if n >= p['washoutLength']:
#             xCollector[:, n - p['washoutLength']] = x[:,0]
#             pCollector[0, n - p['washoutLength']] = u
#
# #     print("Mean/Max/Min Activations, random network driven by noise")
# #     plot(np.mean(xCollector.T, axis=1))
# #     plot(np.max(xCollector.T, axis=1))
# #     plot(np.min(xCollector.T, axis=1))
#
#     # Wout
#     Wout = np.linalg.inv( xCollector.dot(xCollector.conj().T) + ( p['TychonovAlphaReadout'] * np.eye(p['N']) ) ).dot(xCollector).dot(pCollector.conj().transpose()).conj().T
#     print("Initial training")
#     print("NRMSE: ", nrmse(Wout.dot(xCollector), pCollector))
#     print("absWeight: ", np.mean(abs(Wout)))
#
#     allTrainArgs = np.zeros((p['N'], p['patts'].size * p['learnLength']))
#     allTrainOldArgs = np.zeros((p['N'], p['patts'].size * p['learnLength']))
#     allTrainTargs = np.zeros((p['N'], p['patts'].size * p['learnLength']))
#     allTrainOuts = np.zeros((1, p['patts'].size * p['learnLength']))
#     xCollectors =  np.zeros((1, p['patts'].size), dtype=np.object)
#     SRCollectors =  np.zeros((1, p['patts'].size), dtype=np.object)
#     URCollectors =  np.zeros((1, p['patts'].size), dtype=np.object)
#     patternRs =  np.zeros((1, p['patts'].size), dtype=np.object)
#     #train_xPL =  np.zeros((1, p['patts'].size), dtype=np.object)
#     #train_pPL =  np.zeros((1, p['patts'].size), dtype=np.object)
#     startXs =  np.zeros((p['N'], p['patts'].size), dtype=np.object)
#
#     for i_pattern in range(p['patts'].size):
#         print('Loading pattern ', i_pattern)
#         patt = p['patts'][i_pattern]
#         xCollector = np.zeros((p['N'], p['learnLength']))
#         xOldCollector = np.zeros((p['N'], p['learnLength']))
#         pCollector = np.zeros((1, p['learnLength']))
#         x = np.zeros((p['N'],1))
#         for n in range(p['washoutLength'] + p['learnLength']):
#             u = patt(n+1)
#             xOld = x
#             x = np.tanh((Wstar * x) + (Win * u) + Wbias)
#             if n >= p['washoutLength']:
#                 xCollector[:, n - p['washoutLength']] = x[:,0]
#                 xOldCollector[:, n - p['washoutLength']] = xOld[:,0]
#                 pCollector[0, n - p['washoutLength']] = u
#
#         xCollectors[0,i_pattern] = xCollector
#         R = xCollector.dot(xCollector.T) / p['learnLength']
#         [Ux,sx,Vx] = np.linalg.svd(R)
#         SRCollectors[0,i_pattern] = np.diag(sx)
#         URCollectors[0,i_pattern] = Ux
#         patternRs[0,i_pattern] = R
#
#         startXs[:,i_pattern] = x[:,0]
#
#         #needed?
#         #train_xPL[0,i_pattern] = xCollector[:,:signalPlotLength]
#         #train_pPL[0,i_pattern] = pCollector[0,:signalPlotLength]
#         ###
#
#         allTrainArgs[:, i_pattern * p['learnLength']:(i_pattern+1) * p['learnLength']] = xCollector
#         allTrainOldArgs[:, i_pattern * p['learnLength']:(i_pattern+1) * p['learnLength']] = xOldCollector
#         allTrainOuts[0, i_pattern * p['learnLength']:(i_pattern+1) * p['learnLength']] = pCollector
#         allTrainTargs[:, i_pattern * p['learnLength']:(i_pattern+1) * p['learnLength']] = Win.dot(pCollector)
#
#     Wtargets = np.arctanh(allTrainArgs) - np.tile( Wbias, (1, p['patts'].size * p['learnLength']))
#
#     W = np.linalg.inv(allTrainOldArgs.dot(allTrainOldArgs.conj().T) +
#                       (p['TychonovAlpha'] * np.eye(p['N']))).dot(allTrainOldArgs).dot(Wtargets.conj().T).conj().T
#     print("W NMRSE: ", np.mean(nrmse(W.dot(allTrainOldArgs), Wtargets)))
#     print("absSize: ", np.mean(np.mean(abs(W), axis=0)))
#
#     # figure(1)
#     # plot(np.mean(W.dot(allTrainOldArgs).T, axis=1))
#
#     print('Computing conceptors')
#
#     Cs = np.zeros((4, p['patts'].size), dtype=np.object)
#     for i_pattern in range(p['patts'].size):
#         R = patternRs[0,i_pattern]
#         [U,s,V] = np.linalg.svd(R)
#         S = np.diag(s)
#         Snew = (S * np.linalg.inv(S + pow(p['alphas'][i_pattern], -2) * np.eye(p['N'])))
#
#         C =  U.dot(Snew).dot(U.T);
#         Cs[0,i_pattern] = C
#         Cs[1,i_pattern] = U
#         Cs[2,i_pattern] = np.diag(Snew)
#         Cs[3,i_pattern] = np.diag(S)
#
#     x_CTestPL = np.zeros((3, p['recallTestLength'], p['patts'].size))
#     p_CTestPL = np.zeros((1, p['recallTestLength'], p['patts'].size))
#     for i_pattern in range(p['patts'].size):
#         C = Cs[0,i_pattern]
#         x = 0.5 * np.random.randn(p['N'],1)
#         for n in range(p['recallTestLength'] + p['washoutLength']):
#             x = np.tanh(W.dot(x) + Wbias)
#             x = C.dot(x)
#             if (n > p['washoutLength']):
#                 x_CTestPL[:,n-p['washoutLength'],i_pattern] = x[0:3].T
#                 p_CTestPL[:,n-p['washoutLength'],i_pattern] = Wout.dot(x)
#     # for i_pattern in range(p['patts'].size):
#     #     figure(2 + i_pattern)
#     #     plot(p_CTestPL[:,:,i_pattern].T)
#     #     plot([p['patts'][i_pattern](x) for x in arange(p['recallTestLength'])])
#
#     return locals()

# def conceptor_mix_step( net, x, morphvalues, oversample=1 ):
#     ind = 0
#     C = np.zeros( (net['p']['N'] , net['p']['N'] ) )
#     for i_morph in morphvalues:
#         C = C + (net['Cs'][0,ind].dot( i_morph ))
#         ind = ind + 1
#     Wsr = net['W'].dot(1.2)
#     for i_oversample in range( oversample ):
#         x = np.tanh(Wsr.dot(x) + net['Wbias'])
#         x = C.dot(x)
#     output = net['Wout'].dot(x)
#     return output, x
#
## in notebook:

# params = {'N':30, 'NetSR':1.6, 'NetinpScaling':1.6,'BiasScaling':0.3,'TychonovAlpha':0.0001,
#          'washoutLength':100, 'learnLength':500, 'TychonovAlphaReadout':0.0001,
#          'learnLengthWout':500, 'recallTestLength':100,
#          'alphas':np.array([12.0,24.0]),
#           'patts':np.array([pJ1b, pJ2])
#          }
#
# net = makeNetwork(params)
