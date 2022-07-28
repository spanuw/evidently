from typing import Optional
from typing import Tuple
from typing import Union

import numpy as np
import pandas as pd

import pytest
from pytest import approx

from evidently.analyzers.classification_performance_analyzer import ConfusionMatrix
from evidently.pipeline.column_mapping import ColumnMapping
from evidently.metrics.base_metric import InputData
from evidently.metrics import ClassificationPerformanceMetrics
from evidently.metrics.classification_performance_metrics import get_prediction_data
from evidently.metrics.classification_performance_metrics import k_probability_threshold
from evidently.metrics.classification_performance_metrics import threshold_probability_labels


def test_classification_performance_metrics_binary_labels() -> None:
    test_dataset = pd.DataFrame(
        {
            "target": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
            "prediction": [1, 1, 0, 1, 0, 0, 1, 0, 0, 1],
        }
    )
    column_mapping = ColumnMapping(target="target", prediction="prediction")
    metric = ClassificationPerformanceMetrics()
    result = metric.calculate(
        data=InputData(current_data=test_dataset, reference_data=None, column_mapping=column_mapping), metrics={}
    )
    assert result is not None
    assert result.current_metrics.accuracy == 0.7
    assert result.current_metrics.precision == 0.6
    assert result.current_metrics.recall == 0.75
    assert result.current_metrics.f1 == 0.6666666666666665
    assert result.current_metrics.metrics_matrix == {
        "0": {"precision": 0.8, "recall": 0.6666666666666666, "f1-score": 0.7272727272727272, "support": 6},
        "1": {"precision": 0.6, "recall": 0.75, "f1-score": 0.6666666666666665, "support": 4},
        "accuracy": 0.7,
        "macro avg": {"precision": 0.7, "recall": 0.7083333333333333, "f1-score": 0.6969696969696968, "support": 10},
        "weighted avg": {"precision": 0.7200000000000001, "recall": 0.7, "f1-score": 0.7030303030303029, "support": 10},
    }
    assert result.current_metrics.confusion_matrix == ConfusionMatrix(labels=[0, 1], values=[[4, 2], [1, 3]])


def test_classification_performance_metrics_binary_probas_threshold() -> None:
    test_dataset = pd.DataFrame(
        {
            "target": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
            "prediction": [0.9, 0.7, 0.0, 0.5, 0.1, 0.4, 0.6, 0.2, 0.2, 0.8],
        }
    )
    class_threshold = 0.6
    column_mapping = ColumnMapping(target="target", prediction="prediction")
    metric = ClassificationPerformanceMetrics().with_threshold(class_threshold)
    result = metric.calculate(
        data=InputData(current_data=test_dataset, reference_data=None, column_mapping=column_mapping), metrics={}
    )
    assert result is not None
    assert result.current_by_threshold_metrics[class_threshold].accuracy == 0.6
    assert result.current_by_threshold_metrics[class_threshold].precision == 0.5
    assert result.current_by_threshold_metrics[class_threshold].recall == 0.5
    assert result.current_by_threshold_metrics[class_threshold].f1 == 0.5
    assert result.current_by_threshold_metrics[class_threshold].roc_auc == 0.625
    assert result.current_by_threshold_metrics[class_threshold].log_loss == 3.928216092142768
    assert result.current_by_threshold_metrics[class_threshold].confusion_matrix == ConfusionMatrix(
        labels=[0, 1], values=[[4, 2], [2, 2]]
    )


@pytest.mark.parametrize(
    "data,mapping,expected_predictions,expected_probas",
    [
        (
            pd.DataFrame([dict(target=1, preds=1)]),
            ColumnMapping(prediction="preds"),
            [1],
            None,
        ),
        # (
        #     pd.DataFrame([dict(target="a", pos_proba=0.9)]),
        #     ColumnMapping(prediction="pos_proba", target_names=["b", "a"]),
        #     pd.Series(["a"]),
        #     pd.DataFrame([dict(a=0.9, b=0.1)]),
        # )
    ],
)
def test_prediction_data_with_default_threshold(
    data: pd.DataFrame, mapping: ColumnMapping, expected_predictions: list, expected_probas: Optional[pd.DataFrame]
):
    predictions, predictions_probas = get_prediction_data(data, mapping)
    assert predictions.tolist() == expected_predictions

    if predictions_probas is None:
        assert predictions_probas == expected_probas

    else:
        assert predictions_probas.to_dict() == expected_probas


def test_classification_performance_metrics() -> None:
    test_dataset = pd.DataFrame({"target": [1, 1, 1, 1], "prediction": [1, 1, 1, 0]})
    data_mapping = ColumnMapping()
    metric = ClassificationPerformanceMetrics()
    result = metric.calculate(
        data=InputData(current_data=test_dataset, reference_data=None, column_mapping=data_mapping), metrics={}
    )
    assert result is not None
    assert result.current_metrics.accuracy == 0.75
    assert result.current_metrics.f1 == approx(0.86, abs=0.01)
    assert result.current_metrics.precision == 1
    assert result.current_metrics.recall == 0.75


@pytest.mark.parametrize(
    "data, mapping, threshold, expected",
    (
        (
            pd.DataFrame(
                {
                    "target": ["a", "a", "a", "b", "b", "b", "c", "c", "c", "c"],
                    "a": [0.9, 0.8, 0.6, 0.4, 0.4, 0.3, 0.6, 0.2, 0.2, 0.1],
                    "b": [0.0, 0.1, 0.1, 0.3, 0.5, 0.1, 0.1, 0.1, 0.0, 0.2],
                    "c": [0.1, 0.1, 0.3, 0.3, 0.1, 0.6, 0.3, 0.7, 0.8, 0.7],
                }
            ),
            ColumnMapping(prediction=["a", "b", "c"], target="target"),
            0.5,
            (
                pd.Series(["a", "a", "a", "a", "b", "c", "a", "c", "c", "c"]),
                pd.DataFrame(
                    {
                        "a": [0.9, 0.8, 0.6, 0.4, 0.4, 0.3, 0.6, 0.2, 0.2, 0.1],
                        "b": [0.0, 0.1, 0.1, 0.3, 0.5, 0.1, 0.1, 0.1, 0.0, 0.2],
                        "c": [0.1, 0.1, 0.3, 0.3, 0.1, 0.6, 0.3, 0.7, 0.8, 0.7],
                    }
                ),
            ),
        ),
        (
            pd.DataFrame(
                {
                    "target": ["a", "a", "a", "a", "b", "b", "b", "b", "b", "b"],
                    "a": [0.9, 0.7, 0.0, 0.5, 0.1, 0.4, 0.6, 0.2, 0.2, 0.8],
                    "b": [0.1, 0.3, 1.0, 0.5, 0.9, 0.6, 0.4, 0.8, 0.8, 0.2],
                }
            ),
            ColumnMapping(prediction=["a", "b"], target="target", pos_label="b"),
            0.5,
            (
                pd.Series(["a", "a", "b", "b", "b", "b", "a", "b", "b", "a"]),
                pd.DataFrame(
                    {
                        "b": [0.1, 0.3, 1.0, 0.5, 0.9, 0.6, 0.4, 0.8, 0.8, 0.2],
                        "a": [0.9, 0.7, 0.0, 0.5, 0.1, 0.4, 0.6, 0.2, 0.2, 0.8],
                    }
                ),
            ),
        ),
        (
            pd.DataFrame(
                {
                    "target": ["a", "a", "a", "a", "b", "b", "b", "b", "b", "b"],
                    "b": [0.1, 0.3, 1.0, 0.5, 0.9, 0.6, 0.4, 0.8, 0.8, 0.2],
                }
            ),
            ColumnMapping(prediction="b", target="target", pos_label="b"),
            0.5,
            (
                pd.Series(["a", "a", "b", "b", "b", "b", "a", "b", "b", "a"]),
                pd.DataFrame(
                    {
                        "b": [0.1, 0.3, 1.0, 0.5, 0.9, 0.6, 0.4, 0.8, 0.8, 0.2],
                        "a": [0.9, 0.7, 0.0, 0.5, 0.1, 0.4, 0.6, 0.2, 0.2, 0.8],
                    }
                ),
            ),
        ),
        (
            pd.DataFrame(
                {"target": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0], "0": [0.1, 0.3, 1.0, 0.5, 0.9, 0.6, 0.4, 0.8, 0.8, 0.2]}
            ),
            ColumnMapping(prediction="0", target="target", pos_label=0),
            0.5,
            (
                pd.Series([1, 1, 0, 0, 0, 0, 1, 0, 0, 1]),
                pd.DataFrame(
                    {
                        0: [0.1, 0.3, 1.0, 0.5, 0.9, 0.6, 0.4, 0.8, 0.8, 0.2],
                        1: [0.9, 0.7, 0.0, 0.5, 0.1, 0.4, 0.6, 0.2, 0.2, 0.8],
                    }
                ),
            ),
        ),
        (
            pd.DataFrame(
                {"target": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0], "preds": [0.1, 0.3, 1.0, 0.5, 0.9, 0.6, 0.4, 0.8, 0.8, 0.2]}
            ),
            ColumnMapping(prediction="preds", target="target"),
            0.5,
            (
                pd.Series([0, 0, 1, 1, 1, 1, 0, 1, 1, 0]),
                pd.DataFrame(
                    {
                        1: [0.1, 0.3, 1.0, 0.5, 0.9, 0.6, 0.4, 0.8, 0.8, 0.2],
                        0: [0.9, 0.7, 0.0, 0.5, 0.1, 0.4, 0.6, 0.2, 0.2, 0.8],
                    }
                ),
            ),
        ),
    ),
)
def test_get_prediction_data(
    data: pd.DataFrame, mapping: ColumnMapping, threshold: float, expected: Tuple[pd.Series, Optional[pd.DataFrame]]
):
    res = get_prediction_data(data, mapping, threshold)
    assert res[0].equals(expected[0])
    assert np.allclose(res[1], expected[1])
    assert list(res[1].columns) == list(expected[1].columns)


@pytest.mark.parametrize(
    "probas,k,expected",
    (
        (
            pd.DataFrame(
                dict(
                    a=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                    b=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                )
            ),
            0.1,
            0.9,
        ),
        (
            pd.DataFrame(
                np.array(
                    [
                        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                        [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                    ]
                ).T
            ),
            0.1,
            0.9,
        ),
        (
            pd.DataFrame(
                dict(
                    a=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                    b=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                )
            ),
            0.1,
            1.0,
        ),
        (
            pd.DataFrame(
                dict(
                    a=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                    b=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                )
            ),
            0.2,
            0.8,
        ),
        (
            pd.DataFrame(
                dict(
                    a=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                    b=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                )
            ),
            1,
            0.8,
        ),
        (
            pd.DataFrame(
                dict(
                    a=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                    b=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                )
            ),
            2,
            0.7,
        ),
        (
            pd.DataFrame(
                dict(
                    a=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                    b=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                )
            ),
            11,
            0.0,
        ),
        (
            pd.DataFrame(
                dict(
                    a=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                    b=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                )
            ),
            0.0,
            0.9,
        ),
    ),
)
def test_k_probability_threshold(probas: pd.DataFrame, k: Union[int, float], expected: float):
    assert k_probability_threshold(probas, k) == expected


@pytest.mark.parametrize(
    "probas, pos_label, neg_label, threshold, expected",
    (
        (
            pd.DataFrame(
                {
                    "a": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                    "b": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.09, 1],
                }
            ),
            "b",
            "a",
            0.1,
            ["b", "b", "b", "b", "b", "b", "b", "b", "a", "b"],
        ),
        (
            pd.DataFrame(
                {
                    "a": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0],
                    "b": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                }
            ),
            "a",
            "b",
            0.84,
            ["b", "b", "b", "b", "b", "b", "b", "b", "a", "b"],
        ),
        (
            pd.DataFrame({"a": [0.1, 0.2, 0.9, 0.8, 0.9, 0.5, 0.3, 0.99, 0.1, 1]}),
            "a",
            "b",
            0.84,
            ["b", "b", "a", "b", "a", "b", "b", "a", "b", "a"],
        ),
        (
            pd.DataFrame(
                {
                    "a": [0.1, 0.2, 0.9, 0.8, 0.9, 0.5, 0.3, 0.99, 0.1, 1],
                    "b": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1],
                }
            ),
            "b",
            "a",
            0.84,
            ["b", "a", "a", "a", "a", "a", "a", "a", "a", "b"],
        ),
    ),
)
def test_threshold_probability_labels(
    probas: pd.DataFrame, pos_label: str, neg_label: str, threshold: float, expected: pd.Series
) -> None:
    assert threshold_probability_labels(probas, pos_label, neg_label, threshold).tolist() == expected
