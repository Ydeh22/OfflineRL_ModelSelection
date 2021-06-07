import numpy as np
import pandas as pd
import itertools
import copy
from tqdm import tqdm
import scipy.stats

import joblib
from joblib import Parallel, delayed

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input_dir', type=str)
parser.add_argument('--output_dir', type=str)
parser.add_argument('--N', type=int)
parser.add_argument('--run', type=int)
args = parser.parse_args()

run_idx_length = 10_000

gamma = 0.99
nS, nA = 1442, 8
d = 21
num_epoch = 50

NSTEPS = 20
PROB_DIAB = 0.2
DISCOUNT = 1
USE_BOOSTRAP=True
N_BOOTSTRAP = 100

def get_state_action_feature(x_s, a):
    x_sa = np.zeros((nA, d))
    x_sa[a, :] = x_s
    return x_sa.flatten()

# Make features for state-action pairs
X_ALL_states = []
for arrays in itertools.product(
    [[1,0], [0,1]], # Diabetic
    [[1,0,0], [0,1,0], [0,0,1]], # Heart Rate
    [[1,0,0], [0,1,0], [0,0,1]], # SysBP
    [[1,0], [0,1]], # Percent O2
    [[1,0,0,0,0], [0,1,0,0,0], [0,0,1,0,0], [0,0,0,1,0], [0,0,0,0,1]], # Glucose
    [[1,0], [0,1]], # Treat: AbX
    [[1,0], [0,1]], # Treat: Vaso
    [[1,0], [0,1]], # Treat: Vent
):
    X_ALL_states.append(np.concatenate(arrays))

X_ALL_states = np.array(X_ALL_states)
X_ALL = np.array([[get_state_action_feature(x, a_) for a_ in range(nA)] for x in X_ALL_states])
X_ALL_states.shape, X_ALL.shape

print('Loading data ... ', end='')
df_features_tr = pd.read_csv('{}/1-features.csv'.format(args.input_dir))

def load_sparse_features(fname):
    feat_dict = joblib.load('{}/{}'.format(args.input_dir, fname))
    INDS_init, X, A, X_next, R = feat_dict['inds_init'], feat_dict['X'], feat_dict['A'], feat_dict['X_next'], feat_dict['R']
    return INDS_init, X.toarray(), A, X_next.toarray(), R

trINDS_init, trX, trA, trX_next, trR = load_sparse_features('1-21d-feature-matrices.sparse.joblib')
first_ind = trINDS_init[args.run*run_idx_length]
last_ind = trINDS_init[args.run*run_idx_length+args.N]
X, A, X_next, R = trX[first_ind:last_ind], trA[first_ind:last_ind], trX_next[first_ind:last_ind], trR[first_ind:last_ind]

# # Add random noise to state feature vectors
# noise = scipy.stats.truncnorm(-2, 2, loc=0, scale=0.3).rvs((len(X), d), random_state=1)
# X = X + noise
# X_next[:-1] = X_next[:-1] + noise[1:]


print('DONE')
print()


import tensorflow as tf
from tensorflow import keras
from tf_utils import select_output

def clone_keras_model(model):
    model_copy = keras.models.clone_model(model)
    model_copy.set_weights(model.get_weights())
    return model_copy

print('FQI')

def init_networks():
    # Inputs
    state_input = keras.Input(shape=(d), name='state_input')
    action_input = keras.Input(shape=(), dtype=tf.int32, name='action_input')

    # Layers
    hidden_layers = keras.Sequential([
        keras.layers.Dense(1000, activation="relu"),
        keras.layers.Dense(nA),
    ], name='hidden_layers')

    action_selection_layer = keras.layers.Lambda(select_output, name='action_selection')

    # Outputs
    hidden_output = hidden_layers(state_input)
    Q_output = action_selection_layer([hidden_output, action_input])

    # Models
    hidden_net = keras.Model(inputs=[state_input], outputs=[hidden_output], name='hidden_net')
    Q_net = keras.Model(inputs=[state_input, action_input], outputs=[Q_output], name='Q_net')
    Q_net.compile(
        optimizer=keras.optimizers.Adam(),
        loss=keras.losses.MeanSquaredError(),
        metrics=keras.metrics.MeanSquaredError(),
    )
    return hidden_net, Q_net

fit_args = dict(
    batch_size=64, 
    validation_split=0.1, 
    epochs=100, 
    callbacks=[keras.callbacks.EarlyStopping(monitor="val_loss", min_delta=1e-4, patience=10)]
)

import pathlib
pathlib.Path('{}/NFQ-clipped-keras.models/'.format(args.output_dir)).mkdir(parents=True, exist_ok=True)

print("\033[1m\033[31mFQI iteration", 0, "\033[0m\033[0m")
tf.random.set_seed(0)
hidden_net, Q_net = init_networks()
Q_net.fit([X,A], np.zeros_like(R), **fit_args)
Q_net.save('{}/NFQ-clipped-keras.models/iter={}.Q_net'.format(args.output_dir, 0))
hidden_net.save('{}/NFQ-clipped-keras.models/iter={}.hidden_net'.format(args.output_dir, 0))

for k in range(num_epoch):
    print("\033[1m\033[31mFQI iteration", k+1, "\033[0m\033[0m")
    y = R + gamma * hidden_net.predict(X_next).max(axis=1)
    y = np.clip(y, -1, 1)
    tf.random.set_seed(0)
    hidden_net, Q_net = init_networks()
    Q_net.fit([X, A], y, **fit_args)
    Q_net.save('{}/NFQ-clipped-keras.models/iter={}.Q_net'.format(args.output_dir, k+1))
    hidden_net.save('{}/NFQ-clipped-keras.models/iter={}.hidden_net'.format(args.output_dir, k+1))
