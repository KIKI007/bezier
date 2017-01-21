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

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
import numpy as np
import pytest
import six

import bezier
from bezier import _intersection_helpers
from bezier import _plot_helpers

import candidate_curves
import runtime_utils


CONFIG = runtime_utils.Config()


def make_plots(curve1, curve2, points, ignore_save=False, failed=True):
    if not CONFIG.running:
        return

    ax = curve1.plot(64)
    curve2.plot(64, ax=ax)
    ax.plot(points[:, 0], points[:, 1],
            marker='o', linestyle='None', color='black')
    ax.axis('scaled')
    _plot_helpers.add_plot_boundary(ax)

    if CONFIG.save_plot:
        if not ignore_save:
            CONFIG.save_fig()
    else:
        if failed:
            plt.title(CONFIG.current_test + ': failed')
        else:
            plt.title(CONFIG.current_test)
        plt.show()

    plt.close(ax.figure)


def curve_curve_check(curve_or_id1, curve_or_id2, s_vals=None, t_vals=None,
                      points=None, ignore_save=False):
    # pylint: disable=too-many-locals
    if s_vals is None:
        # NOTE: Assume ``s_vals`` None means t_vals / points are.
        key = (curve_or_id1, curve_or_id2)
        info = candidate_curves.INTERSECTION_INFO[key]
        s_vals = info[:, 0]
        t_vals = info[:, 1]
        points = info[:, 2:]

    assert len(s_vals) == len(t_vals)
    assert len(s_vals) == len(points)

    if isinstance(curve_or_id1, six.integer_types):
        curve1 = candidate_curves.CURVES[curve_or_id1]
        curve2 = candidate_curves.CURVES[curve_or_id2]
    else:
        curve1 = curve_or_id1
        curve2 = curve_or_id2

    intersections = _intersection_helpers.all_intersections(
        [(curve1, curve2)])
    assert len(intersections) == len(s_vals)

    info = six.moves.zip(intersections, s_vals, t_vals, points)
    for intersection, s_val, t_val, point in info:
        assert intersection.first is curve1
        assert intersection.second is curve2

        CONFIG.assert_close(intersection.s, s_val)
        CONFIG.assert_close(intersection.t, t_val)

        computed_point = intersection.get_point()
        CONFIG.assert_close(computed_point[0, 0], point[0])
        CONFIG.assert_close(computed_point[0, 1], point[1])

        point_on1 = curve1.evaluate(s_val)
        CONFIG.assert_close(point_on1[0, 0], point[0])
        CONFIG.assert_close(point_on1[0, 1], point[1])

        point_on2 = curve2.evaluate(t_val)
        CONFIG.assert_close(point_on2[0, 0], point[0])
        CONFIG.assert_close(point_on2[0, 1], point[1])

    make_plots(curve1, curve2, points, ignore_save=ignore_save, failed=False)
    # pylint: enable=too-many-locals


def test_curves1_and_2():
    curve_curve_check(1, 2)


def test_curves3_and_4():
    curve_curve_check(3, 4)


def test_curves1_and_5():
    curve_curve_check(1, 5)


def test_curves1_and_6():
    curve_curve_check(1, 6)


def test_curves1_and_7():
    curve_curve_check(1, 7)


def test_curves1_and_8():
    curve_curve_check(1, 8)


def test_curves1_and_9():
    curve_curve_check(1, 9)


def test_curves10_and_11():
    curve_curve_check(10, 11)


def test_curve12_self_crossing():
    curve = candidate_curves.CURVES[12]
    left, right = curve.subdivide()
    # Re-create left and right so they aren't sub-curves. This is just to
    # satisfy a quirk of ``curve_curve_check``, not an issue with the
    # library.
    left = bezier.Curve(left.nodes, left.degree)
    right = bezier.Curve(right.nodes, right.degree)

    delta = np.sqrt(5.0) / 3.0
    s_vals = np.asfortranarray([1.0, 1.0 - delta])
    t_vals = np.asfortranarray([0.0, delta])
    points = np.asfortranarray([
        [-0.09375, 0.828125],
        [-0.25, 1.375],
    ])

    curve_curve_check(left, right, s_vals, t_vals, points)

    # Make sure the left curve doesn't cross itself.
    left1, right1 = left.subdivide()
    expected = right1.evaluate_multi(np.asfortranarray([0.0]))
    curve_curve_check(bezier.Curve(left1.nodes, left1.degree),
                      bezier.Curve(right1.nodes, right1.degree),
                      np.asfortranarray([1.0]),
                      np.asfortranarray([0.0]),
                      expected, ignore_save=True)

    # Make sure the right curve doesn't cross itself.
    left2, right2 = right.subdivide()
    expected = right2.evaluate_multi(np.asfortranarray([0.0]))
    curve_curve_check(bezier.Curve(left2.nodes, left2.degree),
                      bezier.Curve(right2.nodes, right2.degree),
                      np.asfortranarray([1.0]),
                      np.asfortranarray([0.0]),
                      expected, ignore_save=True)


def test_curves8_and_9():
    curve_curve_check(8, 9)


def test_curves1_and_13():
    curve_curve_check(1, 13)


def test_curves14_and_15():
    with pytest.raises(NotImplementedError):
        curve_curve_check(14, 15)

    curve14 = candidate_curves.CURVES[14]
    curve15 = candidate_curves.CURVES[15]
    info = candidate_curves.INTERSECTION_INFO[(14, 15)]
    points = info[:, 2:]
    make_plots(curve14, curve15, points)


def test_curves14_and_16():
    curve_curve_check(14, 16)


def test_curves10_and_17():
    curve_curve_check(10, 17)


def test_curves1_and_18():
    curve_curve_check(1, 18)


def test_curves1_and_19():
    curve_curve_check(1, 19)


def test_curves1_and_20():
    curve_curve_check(1, 20)


def test_curves20_and_21():
    curve_curve_check(20, 21)


def test_curves21_and_22():
    # NOTE: We require a bit more wiggle room for these roots.
    with CONFIG.wiggle(12):
        curve_curve_check(21, 22)


def test_curves10_and_23():
    curve_curve_check(10, 23)


def test_curves1_and_24():
    # NOTE: This is two coincident curves, i.e. CURVE1 on
    #       [1/4, 1] is identical to CURVE24 on [0, 3/4].
    curve1 = candidate_curves.CURVES[1]
    curve24 = candidate_curves.CURVES[24]
    left_vals = curve1.evaluate_multi(
        np.linspace(0.25, 1.0, 2**8 + 1))
    right_vals = curve24.evaluate_multi(
        np.linspace(0.0, 0.75, 2**8 + 1))
    assert np.all(left_vals == right_vals)

    with pytest.raises(NotImplementedError):
        curve_curve_check(1, 24)

    info = candidate_curves.INTERSECTION_INFO[(1, 24)]
    points = info[:, 2:]
    make_plots(curve1, curve24, points)


def test_curves15_and_25():
    curve_curve_check(15, 25)


def test_curves11_and_26():
    # NOTE: We require a bit more wiggle room for these roots.
    with CONFIG.wiggle(25):
        curve_curve_check(11, 26)


def test_curves8_and_27():
    # NOTE: We require a bit more wiggle room for these roots.
    with CONFIG.wiggle(42):
        curve_curve_check(8, 27)


def test_curves28_and_29():
    with pytest.raises(NotImplementedError):
        curve_curve_check(28, 29)

    curve28 = candidate_curves.CURVES[28]
    curve29 = candidate_curves.CURVES[29]
    info = candidate_curves.INTERSECTION_INFO[(28, 29)]
    points = info[:, 2:]
    make_plots(curve28, curve29, points)


def test_curves29_and_30():
    curve_curve_check(29, 30)


def test_curves8_and_23():
    curve_curve_check(8, 23)


def test_curves11_and_31():
    curve_curve_check(11, 31)


def test_curves32_and_33():
    # NOTE: We allow less wiggle room for this intersection.
    with CONFIG.wiggle(4):
        curve_curve_check(32, 33)


def test_curves34_and_35():
    curve_curve_check(34, 35)


def test_curves36_and_37():
    curve_curve_check(36, 37)


@pytest.mark.xfail
def test_curves38_and_39():
    curve_curve_check(38, 39)


def test_curves40_and_41():
    curve_curve_check(40, 41)


if __name__ == '__main__':
    CONFIG.run(globals())
