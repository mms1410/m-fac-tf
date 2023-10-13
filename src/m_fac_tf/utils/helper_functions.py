"""Helper functions used in models and optimizers module."""
import tensorflow as tf
from typing import Tuple, List
import pandas as pd


def get_simple_raw_model(input_shape, target_size):
    """
    Create non-compilated model.
    """
    model = tf.keras.models.Sequential([
        tf.keras.layers.Conv2D(filters=8, input_shape=input_shape, kernel_size=(4, 4),
                               activation='relu', name='conv_1'),
        tf.keras.layers.Conv2D(filters=8, kernel_size=(3, 3), activation='relu', name='conv_2'),
        tf.keras.layers.Flatten(name='flatten'),
        tf.keras.layers.Dense(units=32, activation='relu', name='dense_1'),
        tf.keras.layers.Dense(units=target_size, activation='softmax', name='dense_2')])
    return model

def _setupMatrices(self, G:tf.Variable, D:tf.Variable, B:tf.Variable) -> None:
        """
        """
        # init matrices
        self.G = self.grad_fifo.values
        self.D = tf.Variable(tf.math.scalar_mul(self.damp, tf.matmul(self.G, tf.transpose(self.G))))
        self.B = tf.Variable(tf.math.scalar_mul(self.damp, tf.Variable(tf.linalg.eye(self.m))))
        # Compute D
        for idx in range(1, self.m):
            denominator = tf.math.pow((self.m + self.D[idx - 1, idx - 1]), -1)
            test = self.D[idx:, idx:] - denominator * tf.matmul(tf.transpose(self.D[idx - 1:, idx:]), self.D[idx - 1:, idx:])
            self.D[idx:, idx:].assign(test)
        self.D = tf.linalg.band_part(self.D, 0, -1)
        # Compute B
        for idx in range(1, self.m):
            denominator = self.m + tf.linalg.diag_part(self.D)[:idx]
            tmp = tf.math.divide(-self.D[:idx, idx], denominator)
            tmp = tf.transpose(tmp)
            to_assign = tf.linalg.matvec(self.B[:idx, :idx], tmp)
            self.B[idx, :idx].assign(to_assign)

def _compute_InvMatVec(self, x):
    """
    Compute \hat{F_{m}}\bm{x} for precomputed D and B
    """
    self.G = self.grad_fifo.values
    q = tf.Variable(tf.linalg.matvec(self.G, x))
    q0 = q[0] / (self.m + self.D[0, 0])
    q[0].assign(q0)
    for idx in range(1, self.m):
        tmp = q[idx:] - tf.math.scalar_mul(q[idx - 1], tf.transpose(self.D[idx - 1, idx:]))
        q[idx:].assign(tmp)
    denominator =self.m + tf.linalg.diag_part(self.D)
    q = q / denominator
    tmp = tf.linalg.matvec(self.B, q)
    a = tf.transpose(tf.linalg.matvec(self.G, tmp, transpose_a=True))
    b = tf.math.scalar_mul(self.damp, x)
    result = a - b
    return result


class MatrixFifo:
    """
    Implements idea of fifo queue for tensorflow matrix.
    """
    def __init__(self, ncol):
        self.values = None
        self.ncol=ncol
        self.counter = 0
    
    def append(self, vector:tf.Tensor):
        """
        For k by m matrix and vecotr of dimension k by 1 move columns 2,...,m 'to left by one position' and substitute column m with vector.
        """
        if self.values is None:
            # first vector to append will determine nrow
            self.values = tf.Variable(tf.zeros(shape=[vector.shape[0], self.ncol]))
            self.values[:,-1].assign(tf.cast(vector, dtype=self.values.dtype))
        else:
            tmp = tf.identity(self.values)
            # update last column with new vector
            self.values[:,-1].assign(tf.cast(vector, dtype=self.values.dtype))
            # move other columns to left
            self.values[:,:-1].assign(tmp[:,1:])
        self.counter += 1


def deflatten(flattened_grads: tf.Variable, shapes_grads:list[tf.shape]) -> tuple[tf.Variable]:
    """Deflatten a tensorflow vector."""
    shapes_total = list(map(lambda x: tf.reduce_prod(x), shapes_grads))
    intermediate = tf.split(flattened_grads, shapes_total, axis = 0)
    deflattened = [tf.reshape(grad, shape) for grad, shape in zip(intermediate, shapes_grads)]
    return deflattened


if __name__ == "__main__":
    gradients_list = [tf.Variable(tf.random.normal((5, 2, 19))), tf.Variable(tf.random.normal((20,)))]
    flatten_grads = list(map(lambda x: tf.reshape(x, [-1]), gradients_list))
    flatten_grads = tf.concat(flatten_grads, axis = 0).numpy()
    shapes_grads = list(map(lambda x: x.shape, gradients_list))
    deflattened = deflatten(flatten_grads, shapes_grads)
    print([var.shape for var in deflattened])