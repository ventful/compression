# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Packed tensors in bit sequences."""

import numpy as np
import tensorflow as tf


__all__ = [
    "PackedTensors",
]


class PackedTensors:
  """Packed representation of compressed tensors.

  This class can pack and unpack several tensor values into a single string. It
  can also optionally store a model identifier.

  The tensors currently must be rank 1 (vectors) and either have integer or
  string type.
  """

  def __init__(self, string=None):
    self._example = tf.train.Example()
    if string:
      self.string = string

  @property
  def model(self):
    """A model identifier."""
    buf = self._example.features.feature["MD"].bytes_list.value[0]
    return buf.decode("ascii")

  @model.setter
  def model(self, value):
    self._example.features.feature["MD"].bytes_list.value[:] = [
        value.encode("ascii")]

  @model.deleter
  def model(self):
    del self._example.features.feature["MD"]

  @property
  def string(self):
    """The string representation of this object."""
    return self._example.SerializeToString()

  @string.setter
  def string(self, value):
    self._example.ParseFromString(value)

  def pack(self, tensors, arrays):
    """Packs `Tensor` values into this object."""
    if len(tensors) != len(arrays):
      raise ValueError("`tensors` and `arrays` must have same length.")
    i = 1
    for tensor, array in zip(tensors, arrays):
      feature = self._example.features.feature[chr(i)]
      feature.Clear()
      if array.ndim != 1:
        raise RuntimeError("Unexpected tensor rank: {}.".format(array.ndim))
      if tensor.dtype.is_integer:
        feature.int64_list.value[:] = array
      elif tensor.dtype == tf.string:
        feature.bytes_list.value[:] = array
      else:
        raise RuntimeError(
            "Unexpected tensor dtype: '{}'.".format(tensor.dtype))
      i += 1
    # Delete any remaining, previously set arrays.
    while chr(i) in self._example.features.feature:
      del self._example.features.feature[chr(i)]
      i += 1

  # TODO(jonycgn): Remove this function once all models are converted.
  def unpack(self, tensors):
    """Unpacks `Tensor` values from this object."""
    # Check tensor dtype first for a more informative error message.
    for x in tensors:
      if not x.dtype.is_integer and x.dtype != tf.string:
        raise RuntimeError("Unexpected tensor dtype: '{}'.".format(x.dtype))

    # Extact numpy dtypes and call type-based API.
    np_dtypes = [x.dtype.as_numpy_dtype for x in tensors]
    return self.unpack_from_np_dtypes(np_dtypes)

  def unpack_from_np_dtypes(self, np_dtypes):
    """Unpacks values from this object based on numpy dtypes."""
    arrays = []
    for i, np_dtype in enumerate(np_dtypes):
      feature = self._example.features.feature[chr(i + 1)]
      if np.issubdtype(np_dtype, np.integer):
        arrays.append(np.array(feature.int64_list.value, dtype=np_dtype))
      elif np_dtype == np.dtype(object) or np.issubdtype(np_dtype, np.bytes_):
        arrays.append(np.array(feature.bytes_list.value, dtype=np_dtype))
      else:
        raise RuntimeError("Unexpected numpy dtype: '{}'.".format(np_dtype))
    return arrays
