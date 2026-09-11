# quality-prediction

Tools for estimating and evaluating the quality of Handwritten Text Recognition (HTR) and OCR output.

`quality-prediction` can:

- extract page-level features from HTRflow JSON output;
- compare HTRflow predictions with PAGE XML or ALTO XML ground truth;
- build CSV datasets for quality-prediction experiments;
- train XGBoost regression models on those datasets;
- predict document quality from an in-memory HTRflow document.

The package provides three command-line tools:

- `qp-build-dataset` — extract features and ground-truth quality targets into a CSV dataset;
- `qp-evaluate` — evaluate HTRflow JSON predictions against PAGE XML or ALTO XML ground truth;
- `qp-train-xgb` — train and evaluate XGBoost quality-prediction models.

> [!NOTE]
> Ground truth is required when building training datasets or evaluating predictions. A trained model can estimate quality during inference without ground truth.

## Installation

### Install from PyPI

Once the package has been published:

```bash
python -m pip install quality-prediction
```

Install the optional modeling dependencies to train or run XGBoost models:

```bash
python -m pip install "quality-prediction[modeling]"
```

### Install from source

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/OWNER/quality-prediction.git
cd quality-prediction

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

For model training and inference:

```bash
python -m pip install -e ".[modeling]"
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Input formats

The package works with two primary inputs.

### Prediction input

Predictions are read from HTRflow JSON files. The parser supports:

- pages containing text regions with nested text lines;
- pages containing text lines directly;
- segmentation labels and confidence scores;
- transcription confidence scores;
- token-level transcription confidence scores;
- crop-local or page-absolute coordinates for nested lines.

### Ground-truth input

Ground truth can be supplied as:

- PAGE XML;
- ALTO XML.

Prediction JSON and ground-truth XML files are paired by filename stem.

For example:

```text
ground_truth/volume_1/page_001.xml
predictions/run_1/page_001.json
```

These files form a pair because they share the stem `page_001`. Their parent directory structures do not need to match.

> [!IMPORTANT]
> Filename stems should be unique within each input tree. If two files have the same stem, only the first discovered file is used.

## Building a quality-prediction dataset

Use `qp-build-dataset` to combine:

1. features extracted from HTRflow JSON output; and
2. target values calculated by comparing the predictions with ground truth.

The resulting CSV contains one row per matched page.

### List available features and targets

```bash
qp-build-dataset --list-features
```

```bash
qp-build-dataset --list-targets
```

### Minimal JSON-only dataset

This example uses features available directly from HTRflow JSON. It does not load source images, a language model, n-gram resource sets, or document metadata:

```bash
qp-build-dataset \
  --out-csv output/quality_dataset.csv \
  --dataset dataset_name /path/to/ground_truth /path/to/predictions \
  --feature segmentation,regionization,layout,htr_confidence,text \
  --target target_perm_cer_strict,target_bow_f1,target_map50_line
```

### Dataset with n-gram features

```bash
qp-build-dataset \
  --out-csv output/quality_dataset.csv \
  --ngram-sets /path/to/ngram_sets.pkl \
  --dataset dataset_name /path/to/ground_truth /path/to/predictions \
  --feature segmentation,regionization,layout,htr_confidence,text,ngram \
  --target target_perm_cer_strict,target_bow_f1,target_map50_line
```

### Dataset with language-model perplexity features

```bash
qp-build-dataset \
  --out-csv output/quality_dataset.csv \
  --char-lm /path/to/character_ngram_model.pkl \
  --dataset dataset_name /path/to/ground_truth /path/to/predictions \
  --feature htr_confidence,text,lm \
  --target target_perm_cer_strict,target_bow_f1
```

### Combine multiple datasets

Repeat `--dataset` to combine multiple sources into one CSV:

```bash
qp-build-dataset \
  --out-csv output/combined_quality_dataset.csv \
  --dataset dataset_a /path/to/dataset_a/xml /path/to/dataset_a/json \
  --dataset dataset_b /path/to/dataset_b/xml /path/to/dataset_b/json \
  --feature segmentation,regionization,layout,htr_confidence,text \
  --target target_perm_cer_strict,target_bow_f1,target_map50_line
```

Each `--dataset` argument has three values:

```text
--dataset TAG GT_DIR PRED_DIR
```

The generated dataset includes:

- `page_id`;
- `source_page_id`;
- `dataset_tag`;
- selected feature columns;
- selected target columns.

The dataset tag is included in `page_id`, helping distinguish pages from different datasets.

### Feature groups

The available feature groups are:

| Feature group | Description | Additional resource |
|---|---|---|
| `image` | Statistical features extracted from the source page image | Source image referenced by the JSON |
| `dit` | Document Image Transformer embeddings | DiT model and `--use-dit` |
| `segmentation` | Line and region segmentation statistics | None |
| `regionization` | Statistics describing regions and their contents | None |
| `layout` | Page-layout and geometry statistics | None |
| `htr_confidence` | HTR line and token confidence statistics | Confidence values in JSON |
| `text` | Statistics derived from recognized text | None |
| `ngram` | Ratios of recognized n-grams found in reference sets | `--ngram-sets` |
| `lm` | Language-model perplexity features | `--char-lm` |
| `lexicon` | Lexical matching statistics | Configured lexicon resources |
| `interaction` | Features combining other signals | `--char-lm` |
| `metadata` | Document metadata such as century and script type | `--century` and/or `--script-type` |

If `--feature` is omitted, the command attempts to calculate all feature groups. Provide the necessary resources when selecting resource-dependent groups.

`--char-lm` is required when explicitly selecting `lm` or `interaction`.

`--ngram-sets` is required when explicitly selecting `ngram`.

You can repeat `--feature`:

```bash
qp-build-dataset \
  --out-csv output/dataset.csv \
  --dataset example /path/to/xml /path/to/json \
  --feature segmentation \
  --feature layout \
  --feature htr_confidence
```

Alternatively, use a comma-separated list:

```bash
--feature segmentation,layout,htr_confidence
```

### Target selection

Targets are quality labels derived from ground truth. They are not prediction-time features.

If `--target` is omitted, all available targets are included. Select a subset by repeating the option or supplying a comma-separated list:

```bash
--target target_perm_cer_strict \
--target target_bow_f1,target_map50_line
```

Important target families include:

#### Transcription quality

- `target_perm_cer_strict`
- `target_perm_cer_split_tol`
- `target_perm_cer_split_penalty`
- `target_perm_cer_htr_only`
- `target_geom_order_avg_line_cer`
- `target_avg_line_cer`
- `target_bow_precision`
- `target_bow_recall`
- `target_bow_f1`

#### Missing and hallucinated content

- `target_pi_missing_ratio`
- `target_pi_halluc_ratio`
- `target_avg_missing_ratio`
- `target_avg_halluc_ratio`

#### Error decomposition

- `target_seg_error`
- `target_ro_error`
- `target_delta_cer`

#### Page statistics

- `target_gt_num_lines`
- `target_pred_num_lines`

#### Line segmentation

- `target_map50_line`
- `target_map75_line`
- `target_iou50_line_precision`
- `target_iou50_line_recall`
- `target_iou50_line_f1`
- `target_iou75_line_precision`
- `target_iou75_line_recall`
- `target_iou75_line_f1`
- `target_soft_iou50_line_precision`
- `target_soft_iou50_line_recall`
- `target_soft_iou50_line_f1`
- `target_soft_iou75_line_precision`
- `target_soft_iou75_line_recall`
- `target_soft_iou75_line_f1`

#### Region segmentation

- `target_map50_region`
- `target_map75_region`

Use the CLI to obtain the authoritative list for the installed version:

```bash
qp-build-dataset --list-targets
```

### Confidence-bin configuration

A fitted confidence-bin configuration can be reused between dataset builds:

```bash
qp-build-dataset \
  --out-csv output/dataset.csv \
  --bin-config resources/confidence_bins.json \
  --dataset example /path/to/xml /path/to/json
```

If the file does not exist, a global bin configuration is fitted from the matched prediction pages and written to that path.

To refit an existing configuration:

```bash
qp-build-dataset \
  --out-csv output/dataset.csv \
  --bin-config resources/confidence_bins.json \
  --force-refit-bins \
  --dataset example /path/to/xml /path/to/json
```

Fit preprocessing resources using training data only when creating a train/evaluation split. Reusing preprocessing fitted on evaluation data can cause data leakage.

### DiT image embeddings

Enable Document Image Transformer features with:

```bash
qp-build-dataset \
  --out-csv output/dataset_with_dit.csv \
  --dataset example /path/to/xml /path/to/json \
  --feature dit \
  --use-dit \
  --dit-model microsoft/dit-base \
  --dit-pool cls
```

Available pooling modes are:

```text
cls
mean
```

Additional options include:

```text
--dit-fp16
--dit-pca /path/to/fitted_pca.joblib
--dit-prefix dit_emb
```

As with confidence bins, PCA transformations should be fitted using training data only.

### Metadata features

Static metadata can be attached to every page in a build:

```bash
qp-build-dataset \
  --out-csv output/dataset.csv \
  --dataset example /path/to/xml /path/to/json \
  --feature metadata \
  --century 19 \
  --script-type handwritten
```

### Insertion penalty

The strict permutation-invariant CER uses an insertion penalty of `1.0` by default.

Override it with:

```bash
--lambda-ins 0.5
```

## Evaluating HTRflow output

Use `qp-evaluate` to compare HTRflow prediction JSON with PAGE XML or ALTO XML ground truth:

```bash
qp-evaluate \
  --gt /path/to/ground_truth \
  --pred /path/to/predictions
```

The command recursively pairs XML and JSON files by filename stem.

It computes page-level metrics for:

- permutation-invariant character error rate;
- linewise character error rate;
- geometry-aware character error rate;
- missing and hallucinated content;
- bag-of-words precision, recall, and F1;
- line and region mean average precision;
- hard IoU precision, recall, and F1;
- soft IoU precision, recall, and F1.

`qp-evaluate` measures actual quality using ground truth. It does not run a trained quality-prediction model.

### Change the insertion penalty

```bash
qp-evaluate \
  --gt /path/to/ground_truth \
  --pred /path/to/predictions \
  --lambda-ins 0.5
```

### Write per-page metrics to a log

```bash
qp-evaluate \
  --gt /path/to/ground_truth \
  --pred /path/to/predictions \
  --log output/evaluation.txt
```

The log contains one tab-separated record per evaluated page, with metrics represented as `name=value` fields.

If no log path is provided, `qp-evaluate` prints an aggregate summary to the terminal only.

## Training XGBoost models

Install the optional modeling dependencies before training:

```bash
python -m pip install -e ".[modeling]"
```

`qp-train-xgb` trains one or more XGBoost regressors for columns whose names begin with `target_`.

### Train with an internal training/validation split

```bash
qp-train-xgb \
  --train-csv /path/to/quality_dataset.csv \
  --model-dir output/models \
  --log-dir output/logs \
  --feature-analysis-dir output/feature_analysis \
  --n-trials-full 100 \
  --n-trials-baseline 30 \
  --feature-sets single_htr_line_score_mean,confidence_only,ngram_only,full
```

By default:

- 10% of the training data is used for validation;
- models are selected using mean absolute error;
- a constant-mean baseline is evaluated;
- feature-importance reports are generated;
- all columns beginning with `target_` are trained.

### Select target columns

Use `--targets` to train only selected targets:

```bash
qp-train-xgb \
  --train-csv /path/to/quality_dataset.csv \
  --targets target_bow_f1,target_map50_line,target_perm_cer_strict \
  --feature-sets confidence_only,json_model_only,full
```

### Use an external evaluation dataset

Repeat `--eval-csv` to evaluate trained models on one or more external datasets:

```bash
qp-train-xgb \
  --train-csv /path/to/train.csv \
  --eval-csv /path/to/evaluation_a.csv \
  --eval-csv /path/to/evaluation_b.csv \
  --model-dir output/models \
  --log-dir output/logs \
  --feature-analysis-dir output/feature_analysis
```

### Combine multiple training datasets

Repeat `--train-csv`:

```bash
qp-train-xgb \
  --train-csv /path/to/train_a.csv \
  --train-csv /path/to/train_b.csv \
  --model-dir output/models \
  --log-dir output/logs \
  --feature-analysis-dir output/feature_analysis
```

### Feature sets

Available feature-set names depend on the columns in the input dataset. Common feature sets include:

- `single_htr_line_score_mean`
- `confidence_only`
- `json_model_only`
- `image_only`
- `dit_only`
- `ngram_only`
- `lexical_only`
- `full`

Select feature sets with:

```bash
--feature-sets confidence_only,json_model_only,full
```

The default single-feature baseline uses:

```text
htr_line_score_mean
```

Override it with:

```bash
--single-feature-name another_feature
```

### Sample weighting

Enable sample weighting for supported targets with:

```bash
qp-train-xgb \
  --train-csv /path/to/quality_dataset.csv \
  --weights \
  --weight-alpha 5.0 \
  --weight-p 2.0 \
  --weight-clip-max 50.0
```

Choose the model-selection metric with:

```bash
--select-by mae
```

or:

```bash
--select-by wmae
```

Weighted mean absolute error is most relevant when sample weighting is enabled.

### Feature selection

Enable correlation pruning and permutation-importance feature selection:

```bash
qp-train-xgb \
  --train-csv /path/to/quality_dataset.csv \
  --feature-sets json_model_only,full \
  --feature-selection \
  --fs-apply-to json_model_only,full \
  --fs-corr-prune \
  --fs-corr-threshold 0.98 \
  --fs-perm-repeats 5 \
  --fs-top-k 100
```

Optional stability selection can be enabled with:

```bash
--fs-stability-runs 20 \
--fs-stability-min-freq 0.6
```

After feature selection, the model can either reuse the best hyperparameters:

```bash
--fs-retrain-mode refit_best_params
```

or perform another smaller hyperparameter search:

```bash
--fs-retrain-mode small_hpo \
--fs-retrain-trials 30
```

### Training outputs

The training command can produce:

- serialized trained models;
- hyperparameter-search metrics;
- summary metrics;
- validation predictions;
- feature-importance reports;
- feature-selection reports.

By default, output is written under:

```text
./models
./logs
./feature_analysis
```

Override these paths with:

```text
--model-dir
--log-dir
--feature-analysis-dir
--metrics-log-csv
--summary-metrics-csv
```

Disable the constant-mean baseline with:

```bash
--no-constant-baseline
```

Disable feature-importance output with:

```bash
--no-feature-importance
```

## Running quality prediction

A trained model can estimate page quality without ground truth.

The inference API loads a serialized model, extracts the features expected by that model, and returns one floating-point prediction.

```python
from quality_prediction.inference import XGBoostQualityPredictor

predictor = XGBoostQualityPredictor(
    model="models/quality_model.joblib",
)

quality = predictor.predict(htrflow_document)
print(quality)
```

By default, in-memory prediction uses feature groups available from the current HTRflow document:

```text
segmentation
regionization
layout
htr_confidence
text
```

The model must contain feature names through scikit-learn's `feature_names_in_` attribute or XGBoost booster metadata.

If the serialized model does not contain feature names, supply them explicitly:

```python
predictor = XGBoostQualityPredictor(
    model="models/quality_model.joblib",
    feature_names=[
        "num_lines",
        "htr_line_score_mean",
        "text_char_count",
    ],
)
```

The supplied feature names must match the names and order used during training.

## HTRflow integration

When the quality-prediction pipeline step is installed in HTRflow, it can be placed after text recognition and before export:

```yaml
- step: QualityPrediction
  settings:
    model: models/quality_model.joblib
    target: target_bow_f1
```

A simplified pipeline layout is:

```yaml
steps:
  - step: Segmentation
    settings:
      # Segmentation model configuration

  - step: TextRecognition
    settings:
      # Recognition model configuration

  - step: QualityPrediction
    settings:
      model: models/quality_model.joblib
      target: target_bow_f1

  - step: Export
    settings:
      format: json
      dest: output
```

The exact segmentation, recognition, and export configuration depends on the installed HTRflow version.

The quality prediction is stored in the HTRflow document annotations under:

```text
quality_prediction.<target>
```

For example:

```json
{
  "annotations": {
    "quality_prediction": {
      "target_bow_f1": 0.93
    }
  }
}
```

The model must have been trained using features available at inference time. A model requiring source-image, DiT, n-gram, language-model, lexicon, or manually supplied metadata features cannot be used with the default JSON-only inference configuration unless those resources are also provided by the integration.

## N-gram resources

The package supports two related n-gram feature types.

### N-gram presence features

N-gram presence features compare recognized text against serialized sets of accepted n-grams:

```bash
--ngram-sets /path/to/ngram_sets.pkl \
--feature ngram
```

### Language-model perplexity features

Language-model features use a serialized `NgramModel`:

```bash
--char-lm /path/to/character_ngram_model.pkl \
--feature lm
```

The serialized model should be created by a compatible version of the package. Pickle-based files should only be loaded from trusted sources.

> [!WARNING]
> Python pickle and joblib files can execute arbitrary code during loading. Never load a model or resource file from an untrusted source.

## Reproducible workflow

A typical research workflow is:

### 1. Produce HTRflow JSON

Run an HTRflow segmentation and recognition pipeline over the document images.

### 2. Build a labeled dataset

```bash
qp-build-dataset \
  --out-csv output/train.csv \
  --dataset training /path/to/train/xml /path/to/train/json \
  --feature segmentation,regionization,layout,htr_confidence,text \
  --target target_bow_f1,target_map50_line
```

### 3. Train models

```bash
qp-train-xgb \
  --train-csv output/train.csv \
  --targets target_bow_f1,target_map50_line \
  --feature-sets confidence_only,json_model_only,full \
  --model-dir output/models \
  --log-dir output/logs \
  --feature-analysis-dir output/feature_analysis
```

### 4. Evaluate on held-out documents

Build the held-out dataset separately and provide it through `--eval-csv`:

```bash
qp-build-dataset \
  --out-csv output/evaluation.csv \
  --dataset evaluation /path/to/evaluation/xml /path/to/evaluation/json \
  --feature segmentation,regionization,layout,htr_confidence,text \
  --target target_bow_f1,target_map50_line

qp-train-xgb \
  --train-csv output/train.csv \
  --eval-csv output/evaluation.csv \
  --targets target_bow_f1,target_map50_line \
  --feature-sets json_model_only,full \
  --model-dir output/models \
  --log-dir output/logs \
  --feature-analysis-dir output/feature_analysis
```

Keep documents from the same archival volume or source together when splitting data whenever possible. Randomly splitting closely related pages can produce overly optimistic evaluation results.

### 5. Use the model in HTRflow

Reference the selected model in a `QualityPrediction` pipeline step and export the resulting document as JSON.

## Development

Create a development environment:

```bash
git clone https://github.com/OWNER/quality-prediction.git
cd quality-prediction

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[modeling]"
python -m pip install pytest
```

Run the tests:

```bash
python -m pytest
```

Run command-line smoke tests:

```bash
qp-build-dataset --help
qp-build-dataset --list-features
qp-build-dataset --list-targets
qp-evaluate --help
qp-train-xgb --help
```

## Building the distribution

Install the build tools:

```bash
python -m pip install build twine
```

Build the source distribution and wheel:

```bash
rm -rf build dist
python -m build
```

Validate the distribution metadata:

```bash
python -m twine check dist/*
```

Inspect the files included in the artifacts:

```bash
unzip -l dist/*.whl
tar -tzf dist/*.tar.gz
```

Before publishing, install the wheel into a clean virtual environment and verify the imports and CLI entry points.

## Limitations

- Ground-truth XML and prediction JSON files are paired by filename stem.
- Duplicate stems within one input directory tree are ambiguous.
- Trained models are only compatible with the feature schema used during training.
- Resource-dependent features require the same compatible resources and preprocessing at training and inference time.
- The package does not include pretrained quality-prediction models.
- `qp-evaluate` evaluates predictions against ground truth; it does not invoke a trained quality-prediction model.
- Model and resource files serialized using pickle or joblib must only be loaded from trusted sources.

## Contributing

Contributions are welcome.

Before submitting a change:

1. create a branch;
2. add or update tests;
3. run the full test suite;
4. verify the command-line interfaces;
5. build and inspect the distribution;
6. open a pull request describing the motivation and behavior of the change.

```bash
python -m pytest
python -m build
python -m twine check dist/*
```

## License

Add the project's license name here and include the full license text in a root-level `LICENSE` file before publishing the package.