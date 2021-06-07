import numpy as np
import pandas as pd
import itertools
import copy
from tqdm import tqdm
import scipy.stats
import random as python_random

import joblib
from joblib import Parallel, delayed

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input_dir', type=str)
parser.add_argument('--output_dir', type=str)
parser.add_argument('--N', type=int)
parser.add_argument('--split', type=str)
parser.add_argument('--va_split_name', type=str, required=False)
parser.add_argument('--run', type=int)

args = parser.parse_args()
print(args)

N = args.N
run = args.run
run_idx_length = 10_000

if args.va_split_name is None:
    args.va_split_name = args.split

def load_sparse_features(fname):
    feat_dict = joblib.load('{}/{}'.format(args.input_dir, fname))
    INDS_init, X, A, X_next, R = feat_dict['inds_init'], feat_dict['X'], feat_dict['A'], feat_dict['X_next'], feat_dict['R']
    return INDS_init, X.toarray(), A, X_next.toarray(), R


print('Loading data ... ', end='')
# df_va1 = load_data('2-features.csv').set_index('pt_id').loc[(200_000+run*run_idx_length):(200_000+run*run_idx_length+N//2-1)].reset_index()
vaINDS_init, vaX, vaA, vaX_next, vaR = load_sparse_features('../unif-100k/2-21d-feature-matrices.sparse.joblib')
first_ind = vaINDS_init[run*run_idx_length]
last_ind = vaINDS_init[run*run_idx_length+N//2]
X1, A1, X_next1, R_1 = vaX[first_ind:last_ind], vaA[first_ind:last_ind], vaX_next[first_ind:last_ind], vaR[first_ind:last_ind]
# INDS_init1 = vaINDS_init[run*run_idx_length:run*run_idx_length+N//2]
# X_init1 = vaX[INDS_init1]
# INDS_init1 -= INDS_init1[0]

# df_va2 = load_data('../eps_0_1-100k/2-features.csv').set_index('pt_id').loc[(200_000+run*run_idx_length):(200_000+run*run_idx_length+N//2-1)].reset_index()
vaINDS_init, vaX, vaA, vaX_next, vaR = load_sparse_features('../eps_0_1-100k/2-21d-feature-matrices.sparse.joblib')
first_ind = vaINDS_init[run*run_idx_length]
last_ind = vaINDS_init[run*run_idx_length+N//2]
X2, A2, X_next2, R_2 = vaX[first_ind:last_ind], vaA[first_ind:last_ind], vaX_next[first_ind:last_ind], vaR[first_ind:last_ind]
# INDS_init2 = vaINDS_init[run*run_idx_length:run*run_idx_length+N//2]
# X_init2 = vaX[INDS_init2]
# INDS_init2 -= INDS_init2[0]

# df_va2['pt_id'] = df_va2['pt_id'] + 1_000_000
# df_va = pd.concat([df_va1, df_va2])

X = np.vstack([X1, X2])
A = np.concatenate([A1, A2])
R_ = np.concatenate([R_1, R_2])
X_next = np.vstack([X_next1, X_next2])
# X_init = np.vstack([X_init1, X_init2])
# INDS_init = np.concatenate([INDS_init1, INDS_init2 + len(X1)])

X_delta = X_next - X


import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '4'

import tensorflow as tf
from tensorflow import keras
from tf_utils import select_output_d, select_output
from OPE_utils_keras import *

behavior_net = learn_behavior_net(X, A, args.output_dir, args.va_split_name)
delta_net = learn_dynamics_delta_net([X,A], X_delta, args.output_dir, args.va_split_name)
reward_net = learn_dynamics_reward_net(X, R_, args.output_dir, args.va_split_name)
