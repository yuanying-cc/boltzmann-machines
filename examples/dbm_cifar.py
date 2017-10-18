#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Train 2-layer Gaussian-Bernoulli-Multinomial DBM with pre-training
on CIFAR-10, augmented (x10) using shifts by 1 pixel
in all directions and horizontal mirroring.
Gaussian RBM is initialized from 26 small RBMs trained on patches 8x8
of images, as in [1].

References
----------
[1] A. Krizhevsky and G. Hinton. Learning multiple layers of features
    from tine images. 2009.
"""
print __doc__


import os
import argparse
import numpy as np

import env
from hdm.dbm import DBM
from hdm.rbm import GaussianRBM, MultinomialRBM
from hdm.utils import RNG, Stopwatch
from hdm.utils.augmentation import shift, horizontal_mirror
from hdm.utils.dataset import (load_cifar10,
                               im_flatten, im_unflatten)


def make_augmentation(X_train, n_train, args):
    X_aug = None
    X_aug_path = os.path.join(args.data_path, 'X_aug.npy')
    augment = True
    if os.path.isfile(X_aug_path):
        print "\nLoading augmented data ..."
        X_aug = np.load(X_aug_path)
        print "Checking augmented data ..."
        if 10 * n_train == len(X_aug):
            augment = False

    if augment:
        print "\nAugmenting data ..."
        s = Stopwatch(verbose=True).start()

        X_aug = np.zeros((10 * n_train, 32, 32, 3), dtype=np.float32)
        X_train = im_unflatten(X_train)
        X_aug[:n_train] = X_train
        for i in xrange(n_train):
            for k, offset in enumerate((
                    (1, 0),
                    (-1, 0),
                    (0, 1),
                    (0, -1)
            )):
                img = X_train[i].copy()
                X_aug[(k + 1) * n_train + i] = shift(img, offset=offset)
        for i in xrange(5 * n_train):
            X_aug[5 * n_train + i] = horizontal_mirror(X_aug[i].copy())

        # shuffle once again
        RNG(seed=1337).shuffle(X_aug)

        # convert to 'uint8' type to save disk space
        X_aug *= 255.
        X_aug = X_aug.astype('uint8')

        # flatten to (10 * `n_train`, 3072) shape
        X_aug = im_flatten(X_aug)

        # save to disk
        np.save(X_aug_path, X_aug)

        s.elapsed()
        print "\n"

    return X_aug

def make_small_rbms(X_train, X_val, small_rbm_config, args):
    small_rbms = []

    # first 16 ...
    for i in xrange(4):
        for j in xrange(4):
            rbm_id = 4 * i + j
            rbm_dirpath = args.small_dirpath_prefix + str(rbm_id) + '/'

            if os.path.isdir(rbm_dirpath):
                print "\nLoading small RBM #{0} ...\n\n".format(rbm_id)
                rbm = GaussianRBM.load_model(rbm_dirpath)
            else:
                print "\nTraining small RBM #{0} ...\n\n".format(rbm_id)
                X_patches = X_train[:, 8 * i:8 * (i + 1),
                            8 * j:8 * (j + 1), :]
                X_patches_val = X_val[:, 8 * i:8 * (i + 1),
                                8 * j:8 * (j + 1), :]
                X_patches = im_flatten(X_patches)
                X_patches_val = im_flatten(X_patches_val)

                rbm = GaussianRBM(random_seed=9000 + rbm_id,
                                  model_path=rbm_dirpath,
                                  **small_rbm_config)
                rbm.fit(X_patches, X_patches_val)
            small_rbms.append(rbm)

    # next 9 ...
    for i in xrange(3):
        for j in xrange(3):
            rbm_id = 16 + 3 * i + j
            rbm_dirpath = args.small_dirpath_prefix + str(rbm_id) + '/'

            if os.path.isdir(rbm_dirpath):
                print "\nLoading small RBM #{0} ...\n\n".format(rbm_id)
                rbm = GaussianRBM.load_model(rbm_dirpath)
            else:
                print "\nTraining small RBM #{0} ...\n\n".format(rbm_id)
                X_patches = X_train[:, 4 + 8 * i:4 + 8 * (i + 1),
                            4 + 8 * j:4 + 8 * (j + 1), :]
                X_patches_val = X_val[:, 4 + 8 * i:4 + 8 * (i + 1),
                                4 + 8 * j:4 + 8 * (j + 1), :]
                X_patches = im_flatten(X_patches)
                X_patches_val = im_flatten(X_patches_val)

                rbm = GaussianRBM(random_seed=9000 + rbm_id,
                                  model_path=rbm_dirpath,
                                  **small_rbm_config)
                rbm.fit(X_patches, X_patches_val)
            small_rbms.append(rbm)

    # ... the last one
    rbm_id = 25
    rbm_dirpath = args.small_dirpath_prefix + str(rbm_id) + '/'

    if os.path.isdir(rbm_dirpath):
        print "\nLoading small RBM #{0} ...\n\n".format(rbm_id)
        rbm = GaussianRBM.load_model(rbm_dirpath)
    else:
        print "\nTraining small RBM #{0} ...\n\n".format(rbm_id)
        X_patches = X_train.copy()  # (N, 32, 32, 3)
        X_patches = X_patches.transpose(0, 3, 1, 2)  # (N, 3, 32, 32)
        X_patches = X_patches.reshape((-1, 3, 4, 8, 4, 8)).mean(axis=4).mean(axis=2)  # (N, 3, 8, 8)
        X_patches = X_patches.transpose(0, 2, 3, 1)  # (N, 8, 8, 3)
        X_patches = im_flatten(X_patches)  # (N, 8*8*3)

        X_patches_val = X_val.copy()
        X_patches_val = X_patches_val.transpose(0, 3, 1, 2)
        X_patches_val = X_patches_val.reshape((-1, 3, 4, 8, 4, 8)).mean(axis=4).mean(axis=2)
        X_patches_val = X_patches_val.transpose(0, 2, 3, 1)
        X_patches_val = im_flatten(X_patches_val)

        rbm = GaussianRBM(random_seed=9000 + rbm_id,
                          model_path=rbm_dirpath,
                          **small_rbm_config)
        rbm.fit(X_patches, X_patches_val)
    small_rbms.append(rbm)
    return small_rbms

def make_large_weights(small_rbms):
    W = np.zeros((300 * 26, 32, 32, 3), dtype=np.float32)
    vb = np.zeros((32, 32, 3))
    hb = np.zeros(300 * 26)

    for i in xrange(4):
        for j in xrange(4):
            rbm_id = 4 * i + j
            weights = small_rbms[rbm_id].get_tf_params(scope='weights')
            W_small = weights['W']
            W_small = W_small.T  # (300, 192)
            W_small = im_unflatten(W_small)  # (300, 8, 8, 3)
            W[300 * rbm_id: 300 * (rbm_id + 1), 8 * i:8 * (i + 1),
                                                8 * j:8 * (j + 1), :] = W_small
            vb[8 * i:8 * (i + 1),
               8 * j:8 * (j + 1), :] += im_unflatten(weights['vb'])
            hb[300 * rbm_id: 300 * (rbm_id + 1)] = weights['hb']

    for i in xrange(3):
        for j in xrange(3):
            rbm_id = 16 + 3 * i + j
            weights = small_rbms[rbm_id].get_tf_params(scope='weights')
            W_small = weights['W']
            W_small = W_small.T
            W_small = im_unflatten(W_small)
            W[300 * rbm_id: 300 * (rbm_id + 1), 4 + 8 * i:4 + 8 * (i + 1),
                                                4 + 8 * j:4 + 8 * (j + 1), :] = W_small
            vb[4 + 8 * i:4 + 8 * (i + 1),
               4 + 8 * j:4 + 8 * (j + 1), :] += im_unflatten(weights['vb'])
            hb[300 * rbm_id: 300 * (rbm_id + 1)] = weights['hb']

    weights = small_rbms[25].get_tf_params(scope='weights')
    W_small = weights['W']
    W_small = W_small.T
    W_small = im_unflatten(W_small)
    vb_small = im_unflatten(weights['vb'])
    for i in xrange(8):
        for j in xrange(8):
            U = W_small[:, i, j, :]
            U = np.expand_dims(U, -1)
            U = np.expand_dims(U, -1)
            U = U.transpose(0, 2, 3, 1)
            W[-300:, 4 * i:4 * (i + 1),
                     4 * j:4 * (j + 1), :] = U / 16.
            vb[4 * i:4 * (i + 1),
               4 * j:4 * (j + 1), :] += vb_small[i, j, :].reshape((1, 1, 3)) / 16.
            hb[-300:] = weights['hb']

    W = im_flatten(W)
    W = W.T
    vb /= 2.
    vb[4:-4, 4:-4, :] /= 1.5
    vb = im_flatten(vb)

    return W, vb, hb

def main():
    # training settings
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # general
    parser.add_argument('--gpu', type=str, default='0', metavar='ID',
                        help="ID of the GPU to train on (or '' to train on CPU)")

    # data
    parser.add_argument('--n-train', type=int, default=49000, metavar='N',
                        help='number of training examples')
    parser.add_argument('--n-val', type=int, default=1000, metavar='N',
                        help='number of validation examples')
    parser.add_argument('--data-path', type=str, default='../data/', metavar='PATH',
                        help='directory for storing augmented data etc.')

    # small RBMs related
    parser.add_argument('--small-lr', type=float, default=1e-3, metavar='LR', nargs='+',
                        help='learning rate or sequence of such (per epoch)')
    parser.add_argument('--small-epochs', type=int, default=100, metavar='N',
                        help='number of epochs to train')
    parser.add_argument('--small-batch-size', type=int, default=48, metavar='B',
                        help='input batch size for training')
    parser.add_argument('--small-l2', type=float, default=1e-3, metavar='L2',
                        help='L2 weight decay coefficient')
    parser.add_argument('--small-dirpath-prefix', type=str, default='../models/rbm_cifar_small_', metavar='PREFIX',
                        help='directory path prefix to save RBMs trained on patches')

    # common for RBMs and DBM
    parser.add_argument('--epochs', type=int, default=[64, 120, 300], metavar='N', nargs='+',
                        help='number of epochs to train')
    parser.add_argument('--batch-size', type=int, default=[48, 48, 100], metavar='B', nargs='+',
                        help='input batch size for training, `--n-train` and `--n-val`' + \
                             'must be divisible by this number (for DBM)')
    parser.add_argument('--l2', type=float, default=[1e-4, 1e-3, 1e-7], metavar='L2', nargs='+',
                        help='L2 weight decay coefficient')

    # parse and check params
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    if len(args.epochs) == 1: args.epochs *= 3
    if len(args.batch_size) == 1: args.batch_size *= 3

    # prepare data (load + scale + split)
    print "\nPreparing data ..."
    X, _ = load_cifar10(mode='train', path='../data/')
    X = X.astype(np.float32)
    X /= 255.
    RNG(seed=42).shuffle(X)
    n_train = min(len(X), args.n_train)
    n_val = min(len(X), args.n_val)
    X_train = X[:n_train]
    X_val = X[-n_val:]

    # augment data
    X_aug = make_augmentation(X_train, n_train, args)

    # convert + scale augmented data again
    X_train = X_aug.astype(np.float32)
    X_train /= 255.
    print "Augmented shape: {0}".format(X_train.shape)
    print "Augmented range: {0}".format((X_train.min(), X_train.max()))

    # center and normalize training data
    X_mean = X_train.mean(axis=0)
    X_std = X_train.std(axis=0)
    X_train -= X_mean
    X_train /= X_std
    X_val -= X_mean
    X_val /= X_std
    np.save(os.path.join(args.data_path, 'X_mean.npy'), X_mean)
    np.save(os.path.join(args.data_path, 'X_std.npy'), X_std)
    print "Augmented mean: ({0:.3f}, ...); std: ({1:.3f}, ...)".format(X_train.mean(axis=0)[0],
                                                                       X_train.std(axis=0)[0])
    print "Augmented range: ({0:.3f}, {1:.3f})\n\n".format(X_train.min(), X_train.max())

    # train 26 small Gaussian RBMs on patches
    X_train = im_unflatten(X_train)
    X_val = im_unflatten(X_val)

    small_rbm_config = dict(n_visible=8*8*3,
                            n_hidden=300,
                            sigma=1.,
                            W_init=0.001,
                            vb_init=0.,
                            hb_init=0.,
                            n_gibbs_steps=1,
                            learning_rate=args.small_lr,
                            momentum=np.geomspace(0.5, 0.9, 8),
                            max_epoch=args.small_epochs,
                            batch_size=args.small_batch_size,
                            l2=args.small_l2,
                            sample_v_states=True,
                            sample_h_states=True,
                            dbm_first=True,  # !!!
                            metrics_config=dict(
                                msre=True,
                                feg=True,
                                train_metrics_every_iter=1000,
                                val_metrics_every_epoch=2,
                                feg_every_epoch=2,
                                n_batches_for_feg=50,
                            ),
                            verbose=True,
                            display_filters=12,
                            v_shape=(8, 8, 3),
                            display_hidden_activations=24,
                            tf_dtype='float32',
                            tf_saver_params=dict(max_to_keep=1))

    small_rbms = make_small_rbms(X_train, X_val, small_rbm_config, args)

    # assemble large weight matrix and biases
    print "\nAssembling weights for large Gaussian RBM ...\n\n"
    W, vb, hb = make_large_weights( small_rbms )

    # pre-train large Gaussian RBM
    grbm = GaussianRBM(n_visible=32*32*3,
                       n_hidden=300*26,
                       sigma=1.,
                       W_init=W,
                       vb_init=vb,
                       hb_init=hb,
                       n_gibbs_steps=1,
                       learning_rate=5e-4,
                       momentum=np.geomspace(0.5, 0.9, 8),
                       max_epoch=args.epochs[0],
                       batch_size=args.batch_size[0],
                       l2=args.l2[0],
                       sample_v_states=True,
                       sample_h_states=True,
                       sparsity_target=args.small_sparsity_target,
                       sparsity_cost=args.small_sparsity_cost,
                       dbm_first=True,  # !!!



                            metrics_config=dict(
                                msre=True,
                                feg=True,
                                train_metrics_every_iter=1000,
                                val_metrics_every_epoch=2,
                                feg_every_epoch=2,
                                n_batches_for_feg=50,
                            ),
                            verbose=True,
                            display_filters=12,
                            v_shape=(8, 8, 3),
                            display_hidden_activations=24,
                            tf_dtype='float32',
                            tf_saver_params=dict(max_to_keep=1))

    ## NETFLIX PAPER ##
    """
    Lr 0.01
    momentum 0.9
    L2 1e-3
    W_std 0.01
    CD increased over time (for RBM #2)
    """


if __name__ == '__main__':
    main()