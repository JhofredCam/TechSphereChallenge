from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_mvp_deliverables_and_crisp_dm_structure_is_present_without_copies():
    required = (
        "mvp/README.md",
        "mvp/crisp-dm/README.md",
        "mvp/crisp-dm/01_business_understanding/README.md",
        "mvp/crisp-dm/02_data_understanding/README.md",
        "mvp/crisp-dm/03_data_preparation/README.md",
        "mvp/crisp-dm/04_modeling/README.md",
        "mvp/crisp-dm/05_evaluation/README.md",
        "mvp/crisp-dm/06_deployment/README.md",
        "mvp/deliverables/01_repository/README.md",
        "mvp/deliverables/02_architecture/README.md",
        "mvp/deliverables/03_final_report/README.md",
        "mvp/deliverables/04_video/README.md",
    )
    forbidden = (
        "mvp/dataset",
        "mvp/docs",
        "mvp/app-copy",
        "mvp/runtime-data",
    )

    # IT-STRUCT-01: formal phases and deliverables exist without canonical copies.
    assert all((REPOSITORY_ROOT / relative_path).is_file() for relative_path in required)
    assert all(not (REPOSITORY_ROOT / relative_path).exists() for relative_path in forbidden)
