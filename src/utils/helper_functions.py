"""Helper functions used in models and optimizers module."""
import datetime
import itertools
import os
import platform
import re
from datetime import datetime as dt
from pathlib import Path
from typing import List, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf
from omegaconf.listconfig import ListConfig


def remove_optimizer_name(name: str, optimizer_name: str) -> str:
    """ """
    result = name.replace(optimizer_name + "_", "")
    return result


def write_os_info_to_file(output_file: Union[str, Path]) -> None:
    """

    Args:
        output_file:

    Returns:

    """
    with open(output_file, "w") as file:
        file.write("Operating System Information:\n")
        file.write(f"System: {platform.system()}\n")
        file.write(f"Node Name: {platform.node()}\n")
        file.write(f"Release: {platform.release()}\n")
        file.write(f"Version: {platform.version()}\n")
        file.write(f"Machine: {platform.machine()}\n")
        file.write(f"Processor: {platform.processor()}\n")


def set_log_filename_default(optimizer_name, modelname, batchsize, run):
    """

    Args:
        optimizer_name:
        modelname:
        batchsize:
        run:

    Returns:
        string with configuration information.
    """
    conf_name = datetime.datetime.now()
    conf_name = conf_name.strftime("%Y-%m-%d:%H:%mm")
    conf_name = conf_name + "_" + optimizer_name
    conf_name = conf_name + "_" + modelname
    conf_name = conf_name + "_batch-" + str(batchsize)
    conf_name = conf_name + "_run-" + str(run)

    return conf_name


def set_log_filename_mfac(optimizer_name, modelname, batchsize, run, m):
    """Set the filename for experiment configuration.

    Args:
        optimizer_name:
        batchsize:
        run:
        m:

    Returns:
        string of configuration information.
    """
    conf_name = datetime.datetime.now()
    conf_name = conf_name.strftime("%Y-%m-%d:%H:%mm")
    conf_name = conf_name + "_" + optimizer_name
    conf_name = conf_name + "_" + modelname
    conf_name = conf_name + "_batch-" + str(batchsize)
    conf_name = conf_name + "_m-" + str(m)
    conf_name = conf_name + "_run-" + str(run)

    return conf_name


def set_log_dir(root: str, name: str = "logs") -> Path:
    """
    Args:
        root:

    Returns:
        string with path to log
    """
    log_dir_path = Path(root, name)
    if not log_dir_path.exists():
        log_dir_path.mkdir(parents=True)
    return log_dir_path


def residual_block(x: tf.keras.layers, filters: int):
    # Define a single residual block
    shortcut = x
    x = tf.keras.layers.Conv2D(filters, (3, 3), padding="same")(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation("relu")(x)

    x = tf.keras.layers.Conv2D(filters, (3, 3), padding="same")(x)
    x = tf.keras.layers.BatchNormalization()(x)

    x = tf.keras.layers.Add()([x, shortcut])
    x = tf.keras.layers.Activation("relu")(x)

    return x


def build_resnet_20(input_shape, num_classes):
    # Define the input layer
    input_layer = tf.keras.layers.Input(shape=input_shape)

    # Initial convolution and max-pooling
    x = tf.keras.layers.Conv2D(16, (3, 3), padding="same")(input_layer)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation("relu")(x)
    x = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(x)

    # Stack residual blocks
    num_blocks = 6  # 6 residual blocks for a total of 20 layers
    for _ in range(num_blocks):
        x = residual_block(x, 16)

    # Global average pooling and final dense layer
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dense(num_classes, activation="softmax")(x)

    # Create the model
    model = tf.keras.Model(inputs=input_layer, outputs=x, name="resnet20")

    return model


def build_resnet_32(input_shape, num_classes: int):
    """Build Resnet 32 model.

    Build a renet32 model based on the desired input shape and classes.

    Args:
        input_shape: Tuple of form (int, int, int).
        num_classes: integer number.

    Returns:
        keras model
    """
    # Define the input layer
    input_layer = tf.keras.layers.Input(shape=input_shape)

    # Initial convolution and max-pooling
    x = tf.keras.layers.Conv2D(16, (3, 3), padding="same")(input_layer)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation("relu")(x)
    x = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(x)

    # Stack residual blocks
    num_blocks = 10  # 10 residual blocks for a total of 32 layers
    for _ in range(num_blocks):
        x = residual_block(x, 16)

    # Global average pooling and final dense layer
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dense(num_classes, activation="softmax")(x)

    # Create the model
    model = tf.keras.Model(inputs=input_layer, outputs=x, name="resnet32")

    return model


def get_simple_raw_model(input_shape, target_size):
    """
    Create non-compilated model.
    """
    model = tf.keras.models.Sequential(
        [
            tf.keras.layers.Conv2D(
                filters=8,
                input_shape=input_shape,
                kernel_size=(4, 4),
                activation="relu",
                name="conv_1",
            ),
            tf.keras.layers.Conv2D(filters=8, kernel_size=(3, 3), activation="relu", name="conv_2"),
            tf.keras.layers.Flatten(name="flatten"),
            tf.keras.layers.Dense(units=32, activation="relu", name="dense_1"),
            tf.keras.layers.Dense(units=target_size, activation="softmax", name="dense_2"),
        ]
    )
    return model


class MatrixFifo:
    """
    Implements idea of fifo queue for tensorflow matrix.
    """

    def __init__(self, ncol):
        self.values = None
        self.ncol = ncol
        self.counter = 0

    def append(self, vector: tf.Tensor):
        """
        For k by m matrix and vecotr of dimension k by 1 move columns 2,...,m 'to left by one position' and substitute column m with vector.
        """
        if self.values is None:
            # first vector to append will determine nrow
            self.values = tf.Variable(tf.zeros(shape=[vector.shape[0], self.ncol]))
            self.values[:, -1].assign(tf.cast(vector, dtype=self.values.dtype))
        else:
            tmp = tf.identity(self.values)
            # update last column with new vector
            self.values[:, -1].assign(tf.cast(vector, dtype=self.values.dtype))
            # move other columns to left
            self.values[:, :-1].assign(tmp[:, 1:])
        self.counter += 1


class RowWiseMatrixFifo:
    """Row-wise Matrix fifo queue.

    The top row contains the newest vector (row-wise).
    The matrix is initializes with zeros and when appended the firt m-1 rows
    move rown row down and the row on top is replaced by vector.
    """

    def __init__(self, m):
        self.values = None
        self.nrow = m
        self.counter = 0  # tf.Variable(0, dtype=tf.int32)

    def append(self, vector: tf.Tensor):
        """Append vector to fifoMatrix

        Append vector to first row and update all other rows,
        where row i contains values of former row i-1.
        The first appended vector determines ncol.

        Args:
            vector: tf.Vector of gradients
        """
        if self.values is None:
            # init zero matrix
            # this is done here so the shape of vector determines ncol
            # and is not set at init.
            self.values = tf.Variable(tf.zeros(shape=[self.nrow, vector.shape[0]]))  # noqa E501

        # first m-1 rows are part of updated fifo matrix.
        maintained_values = tf.identity(self.values[: self.nrow - 1, :])
        # move row i is now former row i - 1.
        self.values[1:, :].assign(maintained_values)
        # update firt row with new vector.
        self.values[0, :].assign(vector)
        # increment counter
        self.counter += 1  # self.counter.assign_add(1)

    def reset(self):
        self.counter = 0
        self.values = None


# def deflatten(
#    flattened_grads: tf.Variable, shapes_grads: List[tf.shape]
# ) -> tuple[tf.Variable]:  # noqa E501
#    """Deflatten a tensorflow vector.#
#
#    Args:
#        flattened_grads: flattened gradients.
#        shape_grads: shape in which to reshape#
#
#    Return:
#        tuple of tf.Variables
#    """
#    shapes_total = list(map(lambda x: tf.reduce_prod(x), shapes_grads))
#    intermediate = tf.split(flattened_grads, shapes_total, axis=0)  # noqa E501
#    deflattened = [
#        tf.reshape(grad, shape) for grad, shape in zip(intermediate, shapes_grads)
#    ]  # noqa E501
#    return deflattened


def write_results_to_plot(csv_file: str, destination_file: str) -> None:
    """ """
    df = pd.read_csv(csv_file)
    # Extract data for each metric
    epochs = df["epoch"]
    accuracy = df["accuracy"]
    elapsed_time = df["elapsed_time"]
    loss = df["loss"]
    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Metrics Over Epochs")
    # Plot accuracy
    axes[0, 0].plot(epochs, accuracy, label="accuracy", color="blue")
    axes[0, 0].set_title("accuracy")
    axes[0, 0].set_xlabel("epoch")
    axes[0, 0].set_ylabel("accuracy")
    # Plot elapsed_time
    axes[0, 1].plot(epochs, elapsed_time, label="elapsed_time", color="green")
    axes[0, 1].set_title("elapsed_time")
    axes[0, 1].set_xlabel("epochs")
    axes[0, 1].set_ylabel("elapsed_time")
    # Plot loss
    axes[1, 0].plot(epochs, loss, label="loss", color="red")
    axes[1, 0].set_title("loss")
    axes[1, 0].set_xlabel("epochs")
    axes[1, 0].set_ylabel("loss")
    # Adjust layout
    plt.tight_layout()
    # Save the figure as a PNG image
    plt.savefig(destination_file)


def get_param_combo_list(params: dict) -> List:
    """Create List of possible param combinations.

    Args:
        params: dictionary of possible param constellations.

    Returns:
        A list consisting of a dictioary for each combination.
    """
    # create all combinations
    keys = list(params.keys())
    # create a list with a list for each dimension in which cartesian product is computed.
    # if a value is already a list then just take value else list of value
    # if read from yaml via hydra element is not list but listConfig type.
    values = [
        value if isinstance(value, (ListConfig, list)) else [value] for value in params.values()
    ]

    combinations = itertools.product(*values)
    combinations = list(combinations)
    # append in list
    result_dicts = []
    for combo in combinations:
        result_dict = {key: val for key, val in zip(keys, combo)}
        result_dicts.append(result_dict)

    return result_dicts


def split_filename(string: str) -> Tuple[str, str, str, str]:
    """

    Args:
        string:

    Returns:

    """
    # m
    pattern = r"m-(\d+)"
    match = re.search(pattern, string)
    if match:
        m = match.group(1)
    else:
        m = ""
    # model
    pattern = r"(\d+)m_(.*?)_batch"
    match = re.search(pattern, string)
    model = match.group(2)
    # batch_size
    pattern = r"_batch-(\d+)"
    match = re.search(pattern, string)
    batch_size = match.group(1)
    # run
    pattern = r"_run-(\d+)"
    match = re.search(pattern, string)
    run = match.group(1)

    return model, batch_size, run, m


def get_time(string: str):
    """

    Args:
        string:

    Returns:

    """
    pattern = r"^(.*?)(m)"
    match = re.search(pattern, string)
    result = match.group(1)
    date_obj = dt.strptime(result, "%Y-%m-%d:%H:%M")
    timestamp = date_obj.timestamp()
    return timestamp


def get_optimzerfolder_dataframe(folder: Union[str, Path]) -> pd.DataFrame:
    """Aggregate logged metrics form multiple runs from an optimizer folder.

    This function create a single dataframe for logged data where a new column
    is created with filename.

    Args:
        folder: path to folder with csv files.

    Returns:
        pandas dataframe of logged data.
    """
    data = pd.DataFrame()
    for filename in os.listdir(folder):
        if str(filename).endswith(".csv"):
            tmp = pd.read_csv(Path(folder, filename))
            tmp["filename"] = filename
            tmp["optimizer"] = os.path.basename(folder)
            tmp["experiment"] = os.path.basename(os.path.dirname(folder))
            data = pd.concat([data, tmp])
    data[["model", "batch_size", "run", "m"]] = (
        data["filename"].apply(split_filename).apply(pd.Series)
    )
    return data


def add_mean_values(data: pd.DataFrame) -> pd.DataFrame:
    """ """
    mean_loss = data.groupby(["optimizer", "epoch", "batch_size", "model", "experiment"])[
        "loss"
    ].transform(np.mean)
    mean_val_loss = data.groupby(["optimizer", "epoch", "batch_size", "model", "experiment"])[
        "val_loss"
    ].transform(np.mean)
    mean_accuracy = data.groupby(["optimizer", "epoch", "batch_size", "model", "experiment"])[
        "accuracy"
    ].transform(np.mean)
    mean_val_accuracy = data.groupby(["optimizer", "epoch", "batch_size", "model", "experiment"])[
        "val_accuracy"
    ].transform(np.mean)
    data["mean_loss"] = mean_loss
    data["mean_val_loss"] = mean_val_loss
    data["mean_accuracy"] = mean_accuracy
    data["mean_val_accuracy"] = mean_val_accuracy
    return data


def write_experiment_plot(data: pd.DataFrame, savename: Union[str, Path], experiment_name: Union[str, Path]) -> None:
    """ """
    # data = data[(data['run'] < 1)]  # duplicates due to aggregation
    data["epoch"] = data["epoch"] + 1
    data["epoch"] = data["epoch"].astype(int)

    # Optimierer eindeutig identifizieren
    optimizers = data["optimizer"].unique()
    # Plot-Bereich erstellen
    fig, ax = plt.subplots(4, 1, figsize=(15, 20))
    # Für jeden Optimierer
    for optimizer in optimizers:
        # Daten für diesen Optimierer auswählen
        optimizer_data = data[data["optimizer"] == optimizer]
        # Trainings-Loss Plot
        ax[0].plot(optimizer_data["epoch"], optimizer_data["mean_loss"], label=optimizer)
        # Trainings-Accuracy Plot
        ax[1].plot(optimizer_data["epoch"], optimizer_data["mean_accuracy"], label=optimizer)
        # Validierungs-Loss Plot
        ax[2].plot(optimizer_data["epoch"], optimizer_data["mean_val_loss"], label=optimizer)
        # Validierungs-Accuracy Plot
        ax[3].plot(optimizer_data["epoch"], optimizer_data["mean_val_accuracy"], label=optimizer)

    # Beschriftung und Legenden
    ax[0].set_title("Metrics averaged over runs for each optimizer")
    ax[0].set_xlabel("Epoch")
    ax[0].set_ylabel("Train Mean Loss")
    ax[0].legend()
    ax[1].set_title("Train Mean Accuracy Per Epoch for Different Optimizers")
    ax[1].set_xlabel("Epoch")
    ax[1].set_ylabel("Train Mean Accuracy")
    ax[1].legend()
    ax[2].set_title("Validation Loss Per Epoch for Different Optimizers")
    ax[2].set_xlabel("Epoch")
    ax[2].set_ylabel("Validation Loss")
    ax[2].legend()
    ax[3].set_title("Validation Accuracy Per Epoch for Different Optimizers")
    ax[3].set_xlabel("Epoch")
    ax[3].set_ylabel("Validation Accuracy")
    ax[3].legend()
    plt.tight_layout()
    # plt.show()
    plt.savefig(savename)


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parents[2]
    grand_data = pd.DataFrame()
    experiment_name = "experiment1"
    folder = Path(project_dir, "logs", "experiment1")
    experiment_data = pd.DataFrame()
    for optimizer_folder in folder.iterdir():
        data = get_optimzerfolder_dataframe(optimizer_folder)
        experiment_data = pd.concat([experiment_data, data])
    experiment_data["experiment"] = experiment_name
    experiment_data = add_mean_values(experiment_data)
    experiment_data["run"] = experiment_data["run"].astype(int)
    experiment_data = experiment_data[
        experiment_data["run"] == 0
    ]  # duplicates due to aggregation over runs
    write_experiment_plot(experiment_data, folder, experiment_name)
