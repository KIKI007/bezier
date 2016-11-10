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

"""Helper for B |eacute| zier Surfaces / Triangles.

.. |eacute| unicode:: U+000E9 .. LATIN SMALL LETTER E WITH ACUTE
   :trim:

.. testsetup:: *

  import numpy as np
  import bezier
"""


try:
    from matplotlib import path as _path_mod
    from matplotlib import patches
except ImportError:
    _path_mod = None
    patches = None
import numpy as np

from bezier import _base
from bezier import curve as _curve_mod


_LINEAR_SUBDIVIDE = np.array([
    [1.0, 0.0, 0.0],
    [0.5, 0.5, 0.0],
    [0.0, 1.0, 0.0],
    [0.5, 0.0, 0.5],
    [0.0, 0.5, 0.5],
    [0.0, 0.0, 1.0],
])
_QUADRATIC_SUBDIVIDE = np.array([
    [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    [0.5, 0.5, 0.0, 0.0, 0.0, 0.0],
    [0.25, 0.5, 0.25, 0.0, 0.0, 0.0],
    [0.0, 0.5, 0.5, 0.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    [0.5, 0.0, 0.0, 0.5, 0.0, 0.0],
    [0.25, 0.25, 0.0, 0.25, 0.25, 0.0],
    [0.0, 0.25, 0.25, 0.25, 0.25, 0.0],
    [0.0, 0.0, 0.5, 0.0, 0.5, 0.0],
    [0.25, 0.0, 0.0, 0.5, 0.0, 0.25],
    [0.0, 0.25, 0.0, 0.25, 0.25, 0.25],
    [0.0, 0.0, 0.25, 0.0, 0.5, 0.25],
    [0.0, 0.0, 0.0, 0.5, 0.0, 0.5],
    [0.0, 0.0, 0.0, 0.0, 0.5, 0.5],
    [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
])


class Surface(_base.Base):
    r"""Represents a B |eacute| zier `surface`_.

    .. _surface: https://en.wikipedia.org/wiki/B%C3%A9zier_triangle
    .. _unit simplex:
        https://en.wikipedia.org/wiki/Simplex#The_standard_simplex
    .. _barycentric coordinates:
        https://en.wikipedia.org/wiki/Barycentric_coordinate_system

    We define a B |eacute| zier triangle as a mapping from the
    `unit simplex`_ in 2D (i.e. the unit triangle) onto a surface in an
    arbitrary dimension. We use `barycentric coordinates`_

    .. math::

       \lambda_1 = 1 - s - t, \lambda_2 = s, \lambda_3 = t

    for points in

    .. math::

       \left\{(s, t) \mid 0 \leq s, t, s + t \leq 1\right\}.

    As with curves, using these weights we get convex combinations
    of points :math:`v_{i, j, k}` in some vector space:

    .. math::

       B\left(\lambda_1, \lambda_2, \lambda_3\right) =
           \sum_{i + j + k = d} \binom{d}{i \, j \, k}
           \lambda_1^i \lambda_2^j \lambda_3^k \cdot v_{i, j, k}

    .. note::

       We assume the nodes are ordered from left-to-right and from
       bottom-to-top. So for example, the linear triangle::

          (0,0,1)

          (1,0,0)  (0,1,0)

       is ordered as

       .. math::

          \left[\begin{array}{c c c}
              v_{1,0,0} & v_{0,1,0} & v_{0,0,1} \end{array}\right]^T

       the quadratic triangle::

          (0,0,2)

          (1,0,1)  (0,1,1)

          (2,0,0)  (1,1,0)  (0,2,0)

       is ordered as

       .. math::

          \left[\begin{array}{c c c c c c}
              v_{2,0,0} & v_{1,1,0} &
              v_{0,2,0} & v_{1,0,1} &
              v_{0,1,1} & v_{0,0,2} \end{array}\right]^T

       the cubic triangle::

          (0,0,3)

          (1,0,2)  (0,1,2)

          (2,0,1)  (1,1,1)  (0,2,1)

          (3,0,0)  (2,1,0)  (1,2,0)  (0,3,0)

       is ordered as

       .. math::

          \left[\begin{array}{c c c c c c c c c c}
              v_{3,0,0} & v_{2,1,0} &
              v_{1,2,0} & v_{0,3,0} &
              v_{2,0,1} & v_{1,1,1} &
              v_{0,2,1} & v_{1,0,2} &
              v_{0,1,2} & v_{0,0,3} \end{array}\right]^T

       and so on.

    .. doctest:: surface-ctor

      >>> import bezier
      >>> nodes = np.array([
      ...     [0.0, 0.0],
      ...     [1.0, 0.25],
      ...     [0.25, 1.0],
      ... ])
      >>> surface = bezier.Surface(nodes)
      >>> surface
      <Surface (degree=1, dimension=2)>

    Args:
        nodes (numpy.ndarray): The nodes in the surface. The rows
            represent each node while the columns are the dimension
            of the ambient space.
    """

    _area = None
    _edges = None

    @staticmethod
    def _get_degree(num_nodes):
        """Get the degree of the current surface.

        Args:
            num_nodes (int): The number of control points for a
                B |eacute| zier surface.

        Returns:
            int: The degree :math:`d` such that :math:`(d + 1)(d + 2)/2`
            equals ``num_nodes``.

        Raises:
            ValueError: If ``num_nodes`` isn't a triangular number.
        """
        # 8 * num_nodes = 4(d + 1)(d + 2)
        #               = 4d^2 + 12d + 8
        #               = (2d + 3)^2 - 1
        d_float = 0.5 * (np.sqrt(8.0 * num_nodes + 1.0) - 3.0)
        d_int = int(np.round(d_float))
        if (d_int + 1) * (d_int + 2) == 2 * num_nodes:
            return d_int
        else:
            raise ValueError(num_nodes, 'not a triangular number')

    @property
    def area(self):  # pylint: disable=missing-returns-doc
        """float: The area of the current surface.

        Raises:
            NotImplementedError: If the area isn't already cached.
        """
        if self._area is None:
            raise NotImplementedError(
                'Area computation not yet implemented.')
        return self._area

    def _compute_edges(self):
        """Compute the edges of the current surface.

        Returns:
            Tuple[Curve, Curve, Curve]: The edges of the surface.

        Raises:
            NotImplementedError: If the degree exceeds 2.
        """
        if self.degree == 1:
            nodes1 = self._nodes[(0, 1), :]
            nodes2 = self._nodes[(1, 2), :]
            nodes3 = self._nodes[(2, 0), :]
        elif self.degree == 2:
            nodes1 = self._nodes[(0, 1, 2), :]
            nodes2 = self._nodes[(2, 4, 5), :]
            nodes3 = self._nodes[(5, 3, 0), :]
        else:
            raise NotImplementedError(
                'Degree 1 and 2 only supported at this time')

        edge1 = _curve_mod.Curve(nodes1)
        edge2 = _curve_mod.Curve(nodes2)
        edge3 = _curve_mod.Curve(nodes3)
        return edge1, edge2, edge3

    @property
    def edges(self):
        """tuple: The edges of the surface.

        Returns:
            Tuple[Curve, Curve, Curve]: The edges of the surface.
        """
        if self._edges is None:
            self._edges = self._compute_edges()
        return self._edges

    def evaluate_barycentric(self, lambda1, lambda2, lambda3):
        r"""Compute a point on the surface.

        Evaluates :math:`B\left(\lambda_1, \lambda_2, \lambda_3\right)`.

        Args:
            lambda1 (float): Parameter along the reference triangle.
            lambda2 (float): Parameter along the reference triangle.
            lambda3 (float): Parameter along the reference triangle.

        Returns:
            numpy.ndarray: The point on the curve (as a one dimensional
            NumPy array).

        Raises:
            ValueError: If the parameters are not valid, e.g. they
                don't sum to ``1`` or some are negative.
            NotImplementedError: If the degree is not greater than 3.
        """
        if not np.allclose(lambda1 + lambda2 + lambda3, 1.0):
            raise ValueError('Values do not sum to 1',
                             lambda1, lambda2, lambda3)
        if lambda1 < 0.0 or lambda2 < 0.0 or lambda3 < 0.0:
            raise ValueError('Parameters must be positive',
                             lambda1, lambda2, lambda3)

        if self.degree == 1:
            weights = np.array([
                [lambda1, lambda2, lambda3],
            ])
        elif self.degree == 2:
            weights = np.array([
                [
                    lambda1 * lambda1,
                    2.0 * lambda1 * lambda2,
                    lambda2 * lambda2,
                    2.0 * lambda1 * lambda3,
                    2.0 * lambda2 * lambda3,
                    lambda3 * lambda3,
                ]
            ])
        elif self.degree == 3:
            weights = np.array([
                [
                    lambda1 * lambda1 * lambda1,
                    3.0 * lambda1 * lambda1 * lambda2,
                    3.0 * lambda1 * lambda2 * lambda2,
                    lambda2 * lambda2 * lambda2,
                    3.0 * lambda1 * lambda1 * lambda3,
                    6.0 * lambda1 * lambda2 * lambda3,
                    3.0 * lambda2 * lambda2 * lambda3,
                    3.0 * lambda1 * lambda3 * lambda3,
                    3.0 * lambda2 * lambda3 * lambda3,
                    lambda3 * lambda3 * lambda3,
                ]
            ])
        else:
            raise NotImplementedError('Degree 1 only supported at this time')

        return weights.dot(self._nodes).flatten()  # pylint: disable=no-member

    def evaluate_cartesian(self, s, t):
        r"""Compute a point on the surface.

        Evaluates :math:`B\left(1 - s - t, s, t\right)`.

        Args:
            s (float): Parameter along the reference triangle.
            t (float): Parameter along the reference triangle.

        Returns:
            numpy.ndarray: The point on the surface (as a one dimensional
            NumPy array).
        """
        return self.evaluate_barycentric(1.0 - s - t, s, t)

    def plot(self, pts_per_edge, plt, show=False):
        """Plot the current surface.

        Args:
            pts_per_edge (int): Number of points to plot per edge.
            plt (~types.ModuleType): Plotting module (i.e.
                :mod:`plt <matplotlib.pyplot>`) to use for creating
                figures, etc.
            show (bool): (Optional) Flag indicating if the plot should be
                shown.

        Returns:
            ~matplotlib.figure.Figure: The figure created for the plot.

        Raises:
            NotImplementedError: If the curve's dimension is not ``2``.
        """
        if self.dimension != 2:
            raise NotImplementedError('2D is the only supported dimension',
                                      'Current dimension', self.dimension)

        edge1, edge2, edge3 = self.edges
        s_vals = np.linspace(0.0, 1.0, pts_per_edge)

        points1 = edge1.evaluate_multi(s_vals)
        points2 = edge2.evaluate_multi(s_vals)
        points3 = edge3.evaluate_multi(s_vals)

        fig = plt.figure()
        ax = fig.gca()
        line, = ax.plot(points1[:, 0], points1[:, 1])
        color = line.get_color()
        ax.plot(points2[:, 0], points2[:, 1], color=color)
        ax.plot(points3[:, 0], points3[:, 1], color=color)

        if patches is not None:
            polygon = np.vstack([
                points1[1:, :],
                points2[1:, :],
                points3[1:, :],
            ])
            path = _path_mod.Path(polygon)
            patch = patches.PathPatch(
                path, facecolor=color, alpha=0.6)
            ax.add_patch(patch)

        ax.plot(self._nodes[:, 0], self._nodes[:, 1],
                color='black', marker='o', linestyle='None')

        if show:
            plt.show()

        return fig

    def subdivide(self):
        r"""Split the surface into four sub-surfaces.

        Takes the reference triangle

        .. math::

           T = \left\{(s, t) \mid 0 \leq s, t, s + t \leq 1\right\}

        and splits it into four sub-triangles

        .. math::

           \begin{align*}
           A &= \left\{(s, t) \mid 0 \leq s, t, s + t \leq
               \frac{1}{2}\right\} \\
           B &= -A + \left(\frac{1}{2}, \frac{1}{2}\right) \\
           C &= A + \left(\frac{1}{2}, 0\right) \\
           D &= A + \left(0, \frac{1}{2}\right).
           \end{align*}

        These are the lower left (:math:`A`), central (:math:`B`), lower
        right (:math:`C`) and upper left (:math:`D`) sub-triangles.

        Returns:
            Tuple[Surface, Surface, Surface, Surface]: The lower left, central,
            lower right and upper left sub-surfaces (in that order).

        Raises:
            NotImplementedError: If the degree is not 1 or 2.
        """
        if self.degree == 1:
            # pylint: disable=no-member
            new_nodes = _LINEAR_SUBDIVIDE.dot(self._nodes)
            # pylint: enable=no-member
            nodes_a = new_nodes[(0, 1, 3), :]
            nodes_b = new_nodes[(4, 3, 1), :]
            nodes_c = new_nodes[(1, 2, 4), :]
            nodes_d = new_nodes[(3, 4, 5), :]
        elif self.degree == 2:
            # pylint: disable=no-member
            new_nodes = _QUADRATIC_SUBDIVIDE.dot(self._nodes)
            # pylint: enable=no-member
            nodes_a = new_nodes[(0, 1, 2, 5, 6, 9), :]
            nodes_b = new_nodes[(11, 10, 9, 7, 6, 2), :]
            nodes_c = new_nodes[(2, 3, 4, 7, 8, 11), :]
            nodes_d = new_nodes[(9, 10, 11, 12, 13, 14), :]
        else:
            raise NotImplementedError(
                'Degrees 1 and 2 only supported at this time')

        return (Surface(nodes_a), Surface(nodes_b),
                Surface(nodes_c), Surface(nodes_d))
