"""
This file handles the usage of essentia models (particularly discogs-bs4) to extract vectors encoding the emotional
affect of songs.

This is not really meant to be messed with - the only function that is intended to be public is extract_affect_vector.

It bears mentioning that there is some complication in how the (mel) spectrograms are computed that might be worthwhile
to tease out in the future - particularly the channel expansion step, essentia seems to use some kind of triangular
kernel which is not available by default in scikit. It should be possible to do this manually, but will require looking
through the internals of the relevant packages.
"""

import os
from typing import Any

import numpy as np
import librosa
from scipy.signal import get_window

import config


# Constants
SR = 16000
N_MELS = 128
N_FRAMES = 96

def _audio_to_mel_patches(
    filepath,
    sr=16000,
    n_mels=96,
    patch_size=128,
    hop_size=64,
    fft_size=512,
    mel_hop=256,
    scale=10000.0,
    eps=1e-10):
    y, _ = librosa.load(filepath, sr=sr, mono=True)

    # Use a Hann window with no normalization (as in Essentia)
    window = get_window("hann", fft_size, fftbins=True)

    # Compute STFT manually to control all steps
    S = librosa.stft(
        y,
        n_fft=fft_size,
        hop_length=mel_hop,
        win_length=fft_size,
        window=window,
        center=True
    )
    magnitude = np.abs(S)

    # Mel filter bank matching Essentia parameters
    mel_basis = librosa.filters.mel(
        sr=sr,
        n_fft=fft_size,
        n_mels=n_mels,
        fmin=0.0,
        fmax=sr / 2,
        htk=False,      # Use Slaney-style Mel scale
        norm=None       # Match Essentia's "unit_tri"
    )

    mel = np.dot(mel_basis, magnitude**2)

    # Essentia-style compression: log10(1 + scale * mel)
    log_mel = np.log10(1.0 + scale * mel + eps)  # Add eps to avoid log(0)

    # Generate patches of shape (128, 96)
    patches = []
    for start in range(0, log_mel.shape[1] - patch_size + 1, hop_size):
        patch = log_mel[:, start:start + patch_size]
        patches.append(patch.T)  # Transpose to (128, 96)

    return np.stack(patches, axis=0)  # shape: (num_patches, 128, 96)



BATCH_SIZE = 64
INPUT_TENSOR_NAME = "serving_default_melspectrogram:0"
OUTPUT_TENSOR_NAME = "PartitionedCall:1"


def _run_model_on_patches(pb_path, patches):

    # ugly, but avoids losing 5s to tf startup on every execution
    import tensorflow as tf

    graph_def = tf.compat.v1.GraphDef()
    with tf.io.gfile.GFile(pb_path, 'rb') as f:
        graph_def.ParseFromString(f.read())

    with tf.Graph().as_default() as graph:
        tf.import_graph_def(graph_def, name="")
        input_tensor = graph.get_tensor_by_name(INPUT_TENSOR_NAME)
        output_tensor = graph.get_tensor_by_name(OUTPUT_TENSOR_NAME)

        with tf.compat.v1.Session(graph=graph) as sess:
            num_patches = patches.shape[0]
            # Possibly batch in 64s, depending on model constraint
            outputs = []
            for i in range(0, num_patches, 64):
                batch = patches[i:i + 64]
                if batch.shape[0] < 64:
                    pad_len = 64 - batch.shape[0]
                    pad = np.zeros((pad_len, 128, 96), dtype=np.float32)
                    batch = np.concatenate([batch, pad], axis=0)
                out = sess.run(output_tensor, feed_dict={input_tensor: batch})
                outputs.append(out[:batch.shape[0]])
            return np.concatenate(outputs, axis=0)


def extract_affect_vector(filepath: str) -> np.ndarray:
    """
    Return the affect vector for the song found at the given filepath.
    """
    mel_patches = _audio_to_mel_patches(filepath)
    tensor_file = os.path.join(config.program_files_dir, "discogs-effnet-bs64-1.pb")
    preds = _run_model_on_patches(tensor_file, mel_patches)
    v = preds.mean(axis=0)
    v /= np.sqrt(np.sum(np.square(v)))
    return v
