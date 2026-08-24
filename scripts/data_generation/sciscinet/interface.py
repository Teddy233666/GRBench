import argparse
import os
from pathlib import Path

from ScaleFactor import sf_generator


def data_scale_generator(current_scale, target_scale, data_root):

    print(f"[INFO] Generating from SF={current_scale} to SF={target_scale}...")

    sf = sf_generator(current_scale=current_scale, target_scale=target_scale, path=data_root)
    sf.generate_paperrefs()
    sf.generate_paper_nodes()
    sf.generate_author_paper()
    sf.generate_authors()
    sf.generate_paper_affi()

    sf.generate_paper_nsf()
    sf.generate_paper_nih()
    sf.generate_paper_nct()
    sf.generate_paper_newsfeed()
    sf.generate_paper_twitter()

    sf.generate_nsf()
    sf.generate_nih()
    sf.generate_nct()
    sf.generate_newsfeed()
    sf.generate_twitter()

    sf.generate_nobel_table()
    sf.generate_patent_table()
    sf.generate_papersource_table()
    sf.generate_hit0_table()
    sf.generate_hit1_table()
    sf.generate_norm0_table()
    sf.generate_norm1_table()
    sf.generate_source_table()

    sf.generate_authordetail_table()
    sf.generate_paperdetails_table()
    sf.generate_paper_fields()
    sf.generate_author_affiliation()
    sf.generate_affl2affl()
    sf.generate_affiliatins()

    sf.generate_fields()


def single_generator(current_scale, target_scale, file_name, data_root):

    print(f"[INFO] Generating from SF={current_scale} to SF={target_scale}...")

    sf = sf_generator(current_scale=current_scale, target_scale=target_scale, path=data_root)
    sf.generate_paperrefs()


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        default=os.environ.get("GRBENCH_DATA_ROOT", str(repo_root / "data" / "processed")),
        help="Directory containing sf10_N dataset directories.",
    )
    parser.add_argument("--highest-scale", type=int, default=4)
    args = parser.parse_args()
    for i in range(args.highest_scale - 1, -1, -1):
        current_scale = i + 1
        target_scale = i

        data_scale_generator(current_scale, target_scale, args.data_root)
