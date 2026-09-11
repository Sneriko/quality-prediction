from pathlib import Path

from quality_prediction.config import ResourcePaths, MetadataDefaults
from quality_prediction.dataset import DatasetSpec, build_dataset_multi


def main() -> None:
    datasets = [
        DatasetSpec(
            tag="ds1",
            gt_dir=Path(""),
            pred_dir=Path(
                ""
            ),
        ),
    ]

    resources = ResourcePaths(
        char_ngram_model=Path(""),
        ngram_sets=Path(""),
        global_bin_config=Path(""),
        use_dit=True,
        dit_model_name="",
        dit_pca_path=Path(""),
        lexicon_manifest_json=Path(""),
    )


    metadata = MetadataDefaults(century=17, script_type="handwriting")

    out_csv = Path(
        ""
    )

    build_dataset_multi(
        datasets=datasets,
        out_csv=out_csv,
        resources=resources,
        metadata=metadata,
        lambda_ins=1.0,
        force_refit_bins=False,  # set True if you want to deliberately refit bin edges
    )


if __name__ == "__main__":
    main()
