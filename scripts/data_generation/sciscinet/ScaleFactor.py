import duckdb
import os
import pandas as pd
import numpy as np
from ScaleMap import scale_map as sm
import subprocess



class sf_generator:
    # path: the path to directory that store datasets with all SF
    def __init__(self, seed=42, current_scale=4, target_scale=3, path=None):
        self.sm = sm(path)
        self.data_source = self.sm.get_data_path(current_scale)
        self.data_destination = self.sm.get_data_path(target_scale)
        self.current_scale = current_scale
        self.target_scale = target_scale
        self.seed = seed
        self.sample_ratio_default = 0.1
        self.sample_ratio_1M      = 0.2
        self.sample_ratio_100k    = 0.3
        self.sample_ratio_10k     = 0.4
        self.chunksize = 5000000

        os.makedirs(self.data_destination, exist_ok=True)
        np.random.seed(self.seed)

        self.con = duckdb.connect(database=':memory:')


    def count_rows(self, csv_path):
        query = f"""
        SELECT COUNT(*)
        FROM read_csv_auto('{csv_path}', header=true, strict_mode=false, ignore_errors=true)
        """
        return self.con.execute(query).fetchone()[0]


    # 1. sciscinet_paperrefs
    def generate_paperrefs(self, sample_ratio=None, chunksize=None):

        print("====== Processing: sciscinet_paperrefs ======")

        sample_ratio = sample_ratio or self.sample_ratio_default
        chunksize = chunksize or self.chunksize

        src_file = os.path.join(self.data_source, 'sciscinet_paperrefs.csv')
        dst_file = os.path.join(self.data_destination, 'sciscinet_paperrefs.csv')

        print("[Step 1] Counting rows with DuckDB...")
        total_rows = self.count_rows(src_file)

        target_rows = int(total_rows * sample_ratio)
        print(f"[INFO] Total rows: {total_rows}")
        print(f"[INFO] Target rows (~{sample_ratio*100:.0f}%): {target_rows}")
        print(f"[INFO] Random seed: {self.seed}")

        print("[Step 2] Sampling and writing...")

        header = pd.read_csv(src_file, nrows=0)
        header.to_csv(dst_file, index=False)

        sampled_rows = 0

        for chunk in pd.read_csv(src_file, chunksize=chunksize, header=0):
            mask = np.random.rand(len(chunk)) < sample_ratio
            sampled_chunk = chunk[mask]

            if sampled_chunk.empty:
                continue

            sampled_chunk.to_csv(
                dst_file,
                mode='a',
                index=False,
                header=False
            )

            sampled_rows += len(sampled_chunk)
            print(f"[Progress] Sampled so far: {sampled_rows}")

        print(f"[INFO] Final sampled rows: {sampled_rows}")
        print("Done.\n")


    # 2. sciscinet_papers
    def generate_paper_nodes(self, sample_ratio=None, chunksize=None):

        print("====== Processing: sciscinet_papers ======")

        sample_ratio = sample_ratio or self.sample_ratio_default
        chunksize = chunksize or self.chunksize

        src_papers = os.path.join(self.data_source, 'sciscinet_papers.csv')
        src_refs   = os.path.join(self.data_destination, 'sciscinet_paperrefs.csv')
        dst_papers = os.path.join(self.data_destination, 'sciscinet_papers.csv')

        # --------------------------------------------------
        # Step 1: Count unique paper nodes in 'src_refs'
        # --------------------------------------------------
        print("[Step 1] Collecting paper IDs from paperrefs...")

        con = duckdb.connect(database=':memory:')

        query = f"""
        SELECT DISTINCT citing_paperid AS paperid FROM read_csv_auto('{src_refs}', strict_mode=false, ignore_errors=true)
        UNION
        SELECT DISTINCT cited_paperid  AS paperid FROM read_csv_auto('{src_refs}', strict_mode=false, ignore_errors=true)
        """

        result = con.execute(query).fetchall()
        con.close()

        paper_ids = set(pid[0] for pid in result)
        print(f"[INFO] Collected unique paper IDs from refs: {len(paper_ids)}")

        # --------------------------------------------------
        # Step 2: Extracte unique paper nodes from 'src_refs'
        # --------------------------------------------------
        print("[Step 2] Extracting referenced paper nodes...")

        header = pd.read_csv(src_papers, nrows=0)
        header.to_csv(dst_papers, index=False)

        extracted = 0
        written_paper_ids = set()

        for chunk in pd.read_csv(src_papers, chunksize=chunksize):
            filtered = chunk[chunk['paperid'].isin(paper_ids)]

            if filtered.empty:
                continue

            filtered.to_csv(
                dst_papers,
                mode='a',
                index=False,
                header=False
            )

            written_paper_ids.update(filtered['paperid'])
            extracted += len(filtered)
            print(f"[Progress] Extracted paper nodes so far: {extracted}")

        print(f"[INFO] Step 2 done. Current paper nodes: {extracted}")

        # --------------------------------------------------------------
        # Step 3: Randomly append additional paper nodes (without edges)
        # --------------------------------------------------------------
        print("[Step 3] Randomly appending extra paper nodes to reach target scale...")

        # target paper number
        con = duckdb.connect(database=':memory:')
        total_papers = con.execute(
            f"SELECT COUNT(*) FROM read_csv_auto('{src_papers}', strict_mode=false, ignore_errors=true)"
        ).fetchone()[0]
        con.close()

        target_papers = int(total_papers * sample_ratio)
        print(f"[INFO] Total papers: {total_papers}")
        print(f"[INFO] Target papers (~{sample_ratio*100:.0f}%): {target_papers}")

        if extracted >= target_papers:
            print("[INFO] Already reached target paper scale. Write all extracted papers.")
            print(f"[INFO] Final paper nodes: {extracted}")
            print("Done.\n")
            return

        remaining_needed = target_papers - extracted
        print(f"[INFO] Need to append {remaining_needed} additional paper nodes.")

        np.random.seed(self.seed)

        appended = 0

        for chunk in pd.read_csv(src_papers, chunksize=chunksize):
            candidates = chunk[~chunk['paperid'].isin(written_paper_ids)]

            if candidates.empty:
                continue

            sample_prob = remaining_needed / total_papers
            sampled = candidates[np.random.rand(len(candidates)) < sample_prob]

            if sampled.empty:
                continue

            if appended + len(sampled) > remaining_needed:
                sampled = sampled.iloc[: remaining_needed - appended]

            sampled.to_csv(
                dst_papers,
                mode='a',
                index=False,
                header=False
            )

            written_paper_ids.update(sampled['paperid'])
            appended += len(sampled)

            print(f"[Progress] Appended extra papers so far: {appended}")

            if appended >= remaining_needed:
                break

        print(f"[INFO] Final paper nodes: {extracted + appended}")
        print("Done.\n")


    # 3. sciscinet_authors_paperid
    def generate_author_paper(self, sample_ratio=None, chunksize=None):

        print("====== Processing: sciscinet_authors_paperid ======")

        sample_ratio = sample_ratio or self.sample_ratio_default
        chunksize = chunksize or self.chunksize

        src_au_papers = os.path.join(self.data_source, 'sciscinet_authors_paperid.csv')
        src_papers    = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        dst_au_papers = os.path.join(self.data_destination, 'sciscinet_authors_paperid.csv')

        print("[Step 1] Collecting paper IDs from sciscinet_papers.csv...")

        # --------------------------------------------------
        # Step 1: get unique paper id from 'src_papers'
        # --------------------------------------------------
        con = duckdb.connect(database=':memory:')

        paper_ids = set(
            pid[0] for pid in con.execute(
                f"SELECT DISTINCT paperid FROM read_csv_auto('{src_papers}', strict_mode=false, ignore_errors=true)"
            ).fetchall()
        )

        print(f"[INFO] Collected paper IDs: {len(paper_ids)}")

        # --------------------------------------------------
        # Step 2: select tuples (subset) from authors_paperid
        # --------------------------------------------------
        print("[Step 2] Filtering author-paper relations...")

        header = pd.read_csv(src_au_papers, nrows=0)
        header.to_csv(dst_au_papers, index=False)

        matched_rows = 0
        selected_chunks = []

        for chunk in pd.read_csv(src_au_papers, chunksize=chunksize):
            filtered = chunk[chunk['paperid'].isin(paper_ids)]

            if filtered.empty:
                continue

            selected_chunks.append(filtered)
            matched_rows += len(filtered)

            print(f"[Progress] Matched author-paper relations so far: {matched_rows}")

        print(f"[INFO] Total matched author-paper relations: {matched_rows}")

        # --------------------------------------------------
        # Step 3: 若超出目标规模，则随机下采样
        # --------------------------------------------------
        con2 = duckdb.connect(database=':memory:')
        total_au_papers = con2.execute(
            f"SELECT COUNT(*) FROM read_csv_auto('{src_au_papers}', strict_mode=false, ignore_errors=true)"
        ).fetchone()[0]
        con2.close()

        target_rows = int(total_au_papers * sample_ratio)

        print(f"[INFO] Total author-paper relations: {total_au_papers}")
        print(f"[INFO] Target author-paper relations (~{sample_ratio*100:.0f}%): {target_rows}")

        np.random.seed(self.seed)

        if matched_rows <= target_rows:
            print("[INFO] Matched rows within target scale. Writing all.")
            for df in selected_chunks:
                df.to_csv(dst_au_papers, mode='a', index=False, header=False)
            final_rows = matched_rows
        else:
            print("[INFO] Matched rows exceed target scale. Randomly sampling...")

            all_selected = pd.concat(selected_chunks, ignore_index=True)

            sampled = all_selected.sample(
                n=target_rows,
                random_state=self.seed
            )

            sampled.to_csv(
                dst_au_papers,
                mode='a',
                index=False,
                header=False
            )

        final_rows = len(sampled)

        print(f"[INFO] Final author-paper relations written: {final_rows}")
        print("Done.\n")


    # 4. sciscinet_authors
    def generate_authors(self, sample_ratio=None, chunksize=None):

        print("====== Processing: sciscinet_authors ======")

        sample_ratio = sample_ratio or self.sample_ratio_default
        chunksize = chunksize or self.chunksize

        src_authors   = os.path.join(self.data_source, 'sciscinet_authors.csv')
        src_au_papers = os.path.join(self.data_destination, 'sciscinet_authors_paperid.csv')
        dst_authors   = os.path.join(self.data_destination, 'sciscinet_authors.csv')

        print("[Step 1] Collecting unique author IDs from author-paper relations...")

        con = duckdb.connect(database=':memory:')

        author_ids = set(
            aid[0] for aid in con.execute(
                f"""
                SELECT DISTINCT authorid
                FROM read_csv_auto(
                    '{src_au_papers}',
                    strict_mode=false,
                    ignore_errors=true
                )
                """
            ).fetchall()
        )

        print(f"[INFO] Collected author IDs from relations: {len(author_ids)}")

        # --------------------------------------------------
        # Step 2: 在 src_authors 中抽取匹配的 author 节点
        # --------------------------------------------------
        print("[Step 2] Extracting matched author nodes...")

        header = pd.read_csv(src_authors, nrows=0)
        header.to_csv(dst_authors, index=False)

        extracted = 0
        written_author_ids = set()

        for chunk in pd.read_csv(src_authors, chunksize=chunksize):
            filtered = chunk[chunk['authorid'].isin(author_ids)]

            if filtered.empty:
                continue

            filtered.to_csv(
                dst_authors,
                mode='a',
                index=False,
                header=False
            )

            written_author_ids.update(filtered['authorid'])
            extracted += len(filtered)

            print(f"[Progress] Extracted authors so far: {extracted}")

        print(f"[INFO] Step 2 done. Current author nodes: {extracted}")

        print("[Step 3] Checking target author scale...")

        con2 = duckdb.connect(database=':memory:')
        total_authors = con2.execute(
            f"""
            SELECT COUNT(*)
            FROM read_csv_auto(
                '{src_authors}',
                strict_mode=false,
                ignore_errors=true
            )
            """
        ).fetchone()[0]
        con2.close()

        target_authors = int(total_authors * sample_ratio)

        print(f"[INFO] Total authors: {total_authors}")
        print(f"[INFO] Target authors (~{sample_ratio*100:.0f}%): {target_authors}")

        if extracted >= target_authors:
            print("[INFO] Already reached target author scale.")
            print(f"[INFO] Final author number: {extracted}")
            print("Done.\n")
            return

        remaining_needed = target_authors - extracted
        print(f"[INFO] Need to append {remaining_needed} additional authors.")

        np.random.seed(self.seed)

        appended = 0

        for chunk in pd.read_csv(src_authors, chunksize=chunksize):
            candidates = chunk[~chunk['authorid'].isin(written_author_ids)]

            if candidates.empty:
                continue

            sample_prob = remaining_needed / total_authors
            sampled = candidates[np.random.rand(len(candidates)) < sample_prob]

            if sampled.empty:
                continue

            if appended + len(sampled) > remaining_needed:
                sampled = sampled.iloc[: remaining_needed - appended]

            sampled.to_csv(
                dst_authors,
                mode='a',
                index=False,
                header=False
            )

            written_author_ids.update(sampled['authorid'])
            appended += len(sampled)

            print(f"[Progress] Appended authors so far: {appended}")

            if appended >= remaining_needed:
                break

        print(f"[INFO] Final author nodes: {extracted + appended}")
        print("Done.\n")


    # 5. sciscinet_paper_author_affiliation
    def generate_paper_affi(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default
        print("====== Processing: sciscinet_paper_author_affiliation ======")

        src_papers     = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_paper_affi = os.path.join(self.data_source, 'sciscinet_paper_author_affiliation.csv')
        dst_paper_affi = os.path.join(self.data_destination, 'sciscinet_paper_author_affiliation.csv')

        self.get_edge_from_paper(src_papers, src_paper_affi, dst_paper_affi, sample_ratio)


    # 6. sciscinet_link_nsf
    def generate_paper_nsf(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_1M

        print("====== Processing: sciscinet_link_nsf ======")

        src_papers    = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_paper_nsf = os.path.join(self.data_source, 'sciscinet_link_nsf.csv')
        dst_paper_nsf = os.path.join(self.data_destination, 'sciscinet_link_nsf.csv')

        self.get_edge_from_paper(src_papers, src_paper_nsf, dst_paper_nsf, sample_ratio)


    # 7. sciscinet_link_nih
    def generate_paper_nih(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_1M

        print("====== Processing: sciscinet_link_nih ======")

        src_papers    = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_paper_nih = os.path.join(self.data_source, 'sciscinet_link_nih.csv')
        dst_paper_nih = os.path.join(self.data_destination, 'sciscinet_link_nih.csv')

        self.get_edge_from_paper(src_papers, src_paper_nih, dst_paper_nih, sample_ratio)


    # 8. sciscinet_link_clinicaltrials
    def generate_paper_nct(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_100k

        print("====== Processing: sciscinet_link_clinicaltrials ======")

        src_papers    = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_paper_nct = os.path.join(self.data_source, 'sciscinet_link_clinicaltrials.csv')
        dst_paper_nct = os.path.join(self.data_destination, 'sciscinet_link_clinicaltrials.csv')

        self.get_edge_from_paper(src_papers, src_paper_nct, dst_paper_nct, sample_ratio)


    # 9. sciscinet_link_newsfeed
    def generate_paper_newsfeed(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_1M

        print("====== Processing: sciscinet_link_newsfeed ======")

        src_papers         = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_paper_newsfeed = os.path.join(self.data_source, 'sciscinet_link_newsfeed.csv')
        dst_paper_newsfeed = os.path.join(self.data_destination, 'sciscinet_link_newsfeed.csv')

        self.get_edge_from_paper(src_papers, src_paper_newsfeed, dst_paper_newsfeed, sample_ratio)


    # 10. sciscinet_link_twitter
    def generate_paper_twitter(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: sciscinet_link_twitter ======")

        src_papers        = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_paper_twitter = os.path.join(self.data_source, 'sciscinet_link_twitter.csv')
        dst_paper_twitter = os.path.join(self.data_destination, 'sciscinet_link_twitter.csv')

        self.get_edge_from_paper(src_papers, src_paper_twitter, dst_paper_twitter, sample_ratio)


    # 11. sciscinet_nsf_metadata
    def generate_nsf(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_100k

        print("====== Processing: sciscinet_nsf_metadata ======")

        src_edge = os.path.join(self.data_destination, 'sciscinet_link_nsf.csv')
        src_nsf  = os.path.join(self.data_source, 'sciscinet_nsf_metadata.csv')
        dst_nsf  = os.path.join(self.data_destination, 'sciscinet_nsf_metadata.csv')

        self.get_target_vertex(src_edge, src_nsf, dst_nsf, 'award_id', sample_ratio)


    # 12. sciscinet_nih_metadata
    def generate_nih(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_100k

        print("====== Processing: sciscinet_nih_metadata ======")

        src_edge = os.path.join(self.data_destination, 'sciscinet_link_nih.csv')
        src_nih  = os.path.join(self.data_source, 'sciscinet_nih_metadata.csv')
        dst_nih  = os.path.join(self.data_destination, 'sciscinet_nih_metadata.csv')

        self.get_target_vertex(src_edge, src_nih, dst_nih, 'award_id', sample_ratio)


    # 13. sciscinet_clinicaltrials_metadata
    def generate_nct(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_100k

        print("====== Processing: sciscinet_clinicaltrials_metadata ======")

        src_edge = os.path.join(self.data_destination, 'sciscinet_link_clinicaltrials.csv')
        src_nct  = os.path.join(self.data_source, 'sciscinet_clinicaltrials_metadata.csv')
        dst_nct  = os.path.join(self.data_destination, 'sciscinet_clinicaltrials_metadata.csv')

        self.get_target_vertex(src_edge, src_nct, dst_nct, 'nct_id', sample_ratio)


    # 14. sciscinet_newsfeed_metadata
    def generate_newsfeed(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_1M

        print("====== Processing: sciscinet_newsfeed_metadata ======")

        src_edge = os.path.join(self.data_destination, 'sciscinet_link_newsfeed.csv')
        src_news = os.path.join(self.data_source, 'sciscinet_newsfeed_metadata.csv')
        dst_news = os.path.join(self.data_destination, 'sciscinet_newsfeed_metadata.csv')

        self.get_target_vertex(src_edge, src_news, dst_news, 'newsfeed_id', sample_ratio)


    # 15. sciscinet_twitter_metadata
    def generate_twitter(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: sciscinet_twitter_metadata ======")

        src_edge = os.path.join(self.data_destination, 'sciscinet_link_twitter.csv')
        src_x    = os.path.join(self.data_source, 'sciscinet_twitter_metadata.csv')
        dst_x    = os.path.join(self.data_destination, 'sciscinet_twitter_metadata.csv')

        self.get_target_vertex(src_edge, src_x, dst_x, 'tweet_id', sample_ratio)


    # 16. sciscinet_link_nobellaureates
    def generate_nobel_table(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_10k

        print("====== Processing: sciscinet_link_nobellaureates ======")

        table1     = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_table2 = os.path.join(self.data_source, 'sciscinet_link_nobellaureates.csv')
        dst_table2 = os.path.join(self.data_destination, 'sciscinet_link_nobellaureates.csv')

        self.get_table(table1, src_table2, dst_table2, 'paperid', sample_ratio)


    # 17. sciscinet_link_patents
    def generate_patent_table(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: sciscinet_link_patents ======")

        table1     = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_table2 = os.path.join(self.data_source, 'sciscinet_link_patents.csv')
        dst_table2 = os.path.join(self.data_destination, 'sciscinet_link_patents.csv')

        self.get_table(table1, src_table2, dst_table2, 'paperid', sample_ratio)


    # 18. sciscinet_papersources
    def generate_papersource_table(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: sciscinet_papersources ======")

        table1     = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_table2 = os.path.join(self.data_source, 'sciscinet_papersources.csv')
        dst_table2 = os.path.join(self.data_destination, 'sciscinet_papersources.csv')

        self.get_table(table1, src_table2, dst_table2, 'paperid', sample_ratio)


    # 19. hit_papers_level0
    def generate_hit0_table(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: hit_papers_level0 ======")

        table1     = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_table2 = os.path.join(self.data_source, 'hit_papers_level0.csv')
        dst_table2 = os.path.join(self.data_destination, 'hit_papers_level0.csv')

        self.get_table(table1, src_table2, dst_table2, 'paperid', sample_ratio)


    # 20. hit_papers_level1
    def generate_hit1_table(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: hit_papers_level1 ======")

        table1     = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_table2 = os.path.join(self.data_source, 'hit_papers_level1.csv')
        dst_table2 = os.path.join(self.data_destination, 'hit_papers_level1.csv')

        self.get_table(table1, src_table2, dst_table2, 'paperid', sample_ratio)


    # 21. normalized_citations_level0
    def generate_norm0_table(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: normalized_citations_level0 ======")

        table1     = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_table2 = os.path.join(self.data_source, 'normalized_citations_level0.csv')
        dst_table2 = os.path.join(self.data_destination, 'normalized_citations_level0.csv')

        self.get_table(table1, src_table2, dst_table2, 'paperid', sample_ratio)


    # 22. normalized_citations_level1
    def generate_norm1_table(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: normalized_citations_level1 ======")

        table1     = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_table2 = os.path.join(self.data_source, 'normalized_citations_level1.csv')
        dst_table2 = os.path.join(self.data_destination, 'normalized_citations_level1.csv')

        self.get_table(table1, src_table2, dst_table2, 'paperid', sample_ratio)


    # 23. sciscinet_paperdetails
    def generate_paperdetails_table(self):

        print("====== Processing: sciscinet_paperdetails ======")

        papers_path  = os.path.join(self.data_destination, "sciscinet_papers.csv")
        details_path = os.path.join(self.data_source, "sciscinet_paperdetails.csv")
        output_path  = os.path.join(self.data_destination, "sciscinet_paperdetails.csv")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if os.path.exists(output_path):
            os.remove(output_path)

        # =========================
        # Step 1: load sampled paper ids
        # =========================
        print("[Step 1] Loading sampled paper IDs...")

        paper_ids = set(
            pd.read_csv(
                papers_path,
                usecols=["paperid"],
                dtype={"paperid": "string"}
            )["paperid"]
        )

        total_target = len(paper_ids)
        print(f"[INFO] sampled papers: {total_target}")

        # =========================
        # Step 2: stream paperdetails
        # =========================
        print("[Step 2] Streaming paperdetails and extracting matches...")

        chunksize = self.chunksize
        written = 0
        first_write = True

        for chunk_idx, chunk in enumerate(
            pd.read_csv(
                details_path,
                chunksize=chunksize,
                dtype={"paperid": "string"},
                low_memory=False
            )
        ):
            # 找出匹配的 rows
            mask = chunk["paperid"].isin(paper_ids)
            matched = chunk[mask]

            if not matched.empty:
                matched.to_csv(
                    output_path,
                    mode="w" if first_write else "a",
                    header=first_write,
                    index=False
                )
                first_write = False

                # 从 paper_ids 中删除已匹配的
                paper_ids.difference_update(matched["paperid"])

                written += len(matched)

            # 进度日志
            if True:
                print(
                    f"[Progress] "
                    f"chunks={chunk_idx}, "
                    f"written={written}, "
                    f"remaining={len(paper_ids)}"
                )

            # 提前终止
            if not paper_ids:
                print("[INFO] All paperdetails matched. Early stop.")
                break

        print(f"[INFO] Final sampled rows: {written}")
        print("Done.\n")


    # 24. sciscinet_sources
    def generate_source_table(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_100k

        print("====== Processing: sciscinet_sources ======")

        table1     = os.path.join(self.data_destination, 'sciscinet_papersources.csv')
        src_table2 = os.path.join(self.data_source, 'sciscinet_sources.csv')
        dst_table2 = os.path.join(self.data_destination, 'sciscinet_sources.csv')

        self.get_table(table1, src_table2, dst_table2, 'sourceid', sample_ratio)


    # 25. sciscinet_author_details
    def generate_authordetail_table(self):

        print("====== Processing: sciscinet_author_details ======")

        table1     = os.path.join(self.data_destination, 'sciscinet_authors.csv')
        src_table2 = os.path.join(self.data_source, 'sciscinet_author_details.csv')
        dst_table2 = os.path.join(self.data_destination, 'sciscinet_author_details.csv')

        os.makedirs(os.path.dirname(dst_table2), exist_ok=True)

        if os.path.exists(dst_table2):
            os.remove(dst_table2)

        # =========================
        # Step 1: load sampled paper ids
        # =========================
        print("[Step 1] Loading sampled author IDs...")

        paper_ids = set(
            pd.read_csv(
                table1,
                usecols=["authorid"],
                dtype={"authorid": "string"}
            )["authorid"]
        )

        total_target = len(paper_ids)
        print(f"[INFO] sampled papers: {total_target}")

        # =========================
        # Step 2: stream paperdetails
        # =========================
        print("[Step 2] Streaming paperdetails and extracting matches...")

        chunksize = self.chunksize
        written = 0
        first_write = True

        for chunk_idx, chunk in enumerate(
            pd.read_csv(
                src_table2,
                chunksize=chunksize,
                dtype={"authorid": "string"},
                low_memory=False
            )
        ):
            # 找出匹配的 rows
            mask = chunk["authorid"].isin(paper_ids)
            matched = chunk[mask]

            if not matched.empty:
                matched.to_csv(
                    dst_table2,
                    mode="w" if first_write else "a",
                    header=first_write,
                    index=False
                )
                first_write = False

                # 从 paper_ids 中删除已匹配的
                paper_ids.difference_update(matched["authorid"])

                written += len(matched)

            # 进度日志
            if True:
                print(
                    f"[Progress] "
                    f"chunks={chunk_idx}, "
                    f"written={written}, "
                    f"remaining={len(paper_ids)}"
                )

            # 提前终止
            if not paper_ids:
                print("[INFO] All author details matched. Early stop.")
                break

        print(f"[INFO] Final sampled rows: {written}")
        print("Done.\n")

    # 26. sciscinet_paperfields
    def generate_paper_fields(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: sciscinet_paperfields ======")

        src_papers       = os.path.join(self.data_destination, 'sciscinet_papers.csv')
        src_paper_fields = os.path.join(self.data_source, 'sciscinet_paperfields.csv')
        dst_paper_fields = os.path.join(self.data_destination, 'sciscinet_paperfields.csv')

        self.get_edge_from_paper(src_papers, src_paper_fields, dst_paper_fields, sample_ratio)


    # 27. sciscinet_author_affiliation
    def generate_author_affiliation(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_default

        print("====== Processing: sciscinet_author_affiliation ======")

        src_authors     = os.path.join(self.data_destination, 'sciscinet_authors.csv')
        src_author_affi = os.path.join(self.data_source, 'sciscinet_author_affiliation.csv')
        dst_author_affi = os.path.join(self.data_destination, 'sciscinet_author_affiliation.csv')

        print(f"[Step 1] Collecting unique IDs from {src_authors}")

        con = duckdb.connect(database=':memory:')

        author_ids = set(
            pid[0] for pid in con.execute(
                f"SELECT DISTINCT authorid FROM read_csv_auto('{src_authors}', strict_mode=false, ignore_errors=true)"
            ).fetchall()
        )
        print(f"[INFO] Collected author IDs: {len(author_ids)}")

        print(f"[Step 2] Filtering edges from {src_author_affi}...")

        header = pd.read_csv(src_author_affi, nrows=0)
        header.to_csv(dst_author_affi, index=False)

        matched_rows = 0
        selected_chunks = []

        for chunk in pd.read_csv(src_author_affi, chunksize=self.chunksize):
            filtered = chunk[chunk['authorid'].isin(author_ids)]

            if filtered.empty:
                continue

            selected_chunks.append(filtered)
            matched_rows += len(filtered)

            print(f"[Progress] Matched edges so far: {matched_rows}")

        print(f"[INFO] Total matched edges: {matched_rows}")

        print("[Step 3] Random samplying...")

        con2 = duckdb.connect(database=':memory:')
        total_au_papers = con2.execute(
            f"SELECT COUNT(*) FROM read_csv_auto('{src_author_affi}', header=true, strict_mode=false, ignore_errors=true)"
        ).fetchone()[0]
        con2.close()

        target_rows = int(total_au_papers * sample_ratio)

        print(f"[INFO] Number of original edges: {total_au_papers}")
        print(f"[INFO] Number of target edges (~{sample_ratio*100:.0f}%): {target_rows}")

        np.random.seed(self.seed)

        if matched_rows <= target_rows:
            print("[INFO] Matched rows within target scale. Writing all.")
            for df in selected_chunks:
                df.to_csv(dst_author_affi, mode='a', index=False, header=False)
            final_rows = matched_rows
        else:
            print("[INFO] Matched rows exceed target scale. Randomly sampling...")

            # 合并后一次性采样（只在内存可承受时推荐）
            all_selected = pd.concat(selected_chunks, ignore_index=True)

            sampled = all_selected.sample(
                n=target_rows,
                random_state=self.seed
            )

            sampled.to_csv(
                dst_author_affi,
                mode='a',
                index=False,
                header=False
            )

        final_rows = len(sampled)

        print(f"[INFO] Final edges written: {final_rows}")
        print("Done.\n")


    # 28. sciscinet_affl_assoc_affl
    def generate_affl2affl(self, sample_ratio=None):
        sample_ratio = sample_ratio or self.sample_ratio_10k

        print("====== Processing: sciscinet_affl_assoc_affl ======")
        src_file = os.path.join(self.data_source, 'sciscinet_affl_assoc_affl.csv')
        dst_file = os.path.join(self.data_destination, 'sciscinet_affl_assoc_affl.csv')

        print("[Step 1] Counting rows with DuckDB...")
        total_rows = self.count_rows(src_file)

        target_rows = int(total_rows * sample_ratio)
        print(f"[INFO] Total rows: {total_rows}")
        print(f"[INFO] Target rows (~{sample_ratio*100:.0f}%): {target_rows}")
        print(f"[INFO] Random seed: {self.seed}")

        print("[Step 2] Sampling and writing...")

        header = pd.read_csv(src_file, nrows=0)
        header.to_csv(dst_file, index=False)

        sampled_rows = 0

        for chunk in pd.read_csv(src_file, chunksize=self.chunksize, header=0):
            mask = np.random.rand(len(chunk)) < sample_ratio
            sampled_chunk = chunk[mask]

            if sampled_chunk.empty:
                continue

            sampled_chunk.to_csv(
                dst_file,
                mode='a',
                index=False,
                header=False
            )

            sampled_rows += len(sampled_chunk)
            print(f"[INFO]Sampled so far: {sampled_rows}")


        print(f"[INFO] Final sampled rows: {sampled_rows}")
        print("Done.\n")


    # 29. sciscinet_affiliations
    def generate_affiliatins(self):

        print("====== Processing: sciscinet_affiliations ======")

        src_file = os.path.join(self.data_source, 'sciscinet_affiliations.csv')
        dst_file = os.path.join(self.data_destination, 'sciscinet_affiliations.csv')

        author_affi = os.path.join(self.data_destination, 'sciscinet_author_affiliation.csv')
        paper_affi  = os.path.join(self.data_destination, 'sciscinet_paper_author_affiliation.csv')
        affi_affi   = os.path.join(self.data_destination, 'sciscinet_affl_assoc_affl.csv')

        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
        if os.path.exists(dst_file):
            os.remove(dst_file)

        con = duckdb.connect(database=':memory:')

        def csv(path):
            return f"""
            read_csv_auto(
                '{path}',
                header=true,
                strict_mode=false,
                ignore_errors=true
            )
            """

        print("[Step 1] Coollecting all the unique institution IDs...")

        institution_cte = f"""
            SELECT DISTINCT institutionid FROM (
                SELECT institutionid FROM {csv(author_affi)}
                UNION ALL
                SELECT institutionid FROM {csv(paper_affi)}
                UNION ALL
                SELECT institutionid FROM {csv(affi_affi)}
            )
            WHERE institutionid IS NOT NULL
        """

        print("[Step 2] Filtering satisfied IDs...")

        filtered_affiliations = f"""
            SELECT a.*
            FROM {csv(src_file)} a
            SEMI JOIN (
                {institution_cte}
            ) i
            ON a.institutionid = i.institutionid
        """

        result_count = con.execute(
            f"SELECT COUNT(*) FROM ({filtered_affiliations})"
        ).fetchone()[0]

        print(f"[INFO] Affiliations selected: {result_count}")

        print("[Step 3] Writing affiliations...")

        con.execute(f"""
            COPY (
                {filtered_affiliations}
            )
            TO '{dst_file}'
            (HEADER, DELIMITER ',');
        """)

        con.close()

        print(f"[INFO] Output file : {dst_file}")
        print(f"[INFO] Total rows  : {result_count}")
        print("Done.\n")


    # 30. sciscinet_fields
    def generate_fields(self):

        print("====== Processing: sciscinet_fields ======")

        src = os.path.join(self.data_source, "sciscinet_fields.csv")
        bak = os.path.join(self.data_destination, "sciscinet_fields.csv")

        subprocess.run(["cp", src, bak], check=True)

        print(f"[INFO] Total rows  : 303")
        print("Done.\n")















    # public tool: for edges whose start vertex are 'paper'
    def get_edge_from_paper(self, start_vertex, src_edge, dst_edge, sample_ratio):

        print(f"====== Creating {dst_edge} ======")

        print(f"[Step 1] Collecting unique IDs from {start_vertex}")

        os.makedirs(os.path.dirname(dst_edge), exist_ok=True)

        if os.path.exists(dst_edge):
            os.remove(dst_edge)

        con = duckdb.connect(database=':memory:')

        paper_ids = set(
            pid[0] for pid in con.execute(
                f"SELECT DISTINCT paperid FROM read_csv_auto('{start_vertex}', strict_mode=false, ignore_errors=true)"
            ).fetchall()
        )
        print(f"[INFO] Collected paper IDs: {len(paper_ids)}")

        print(f"[Step 2] Filtering edges from {src_edge}...")

        header = pd.read_csv(src_edge, nrows=0)
        header.to_csv(dst_edge, index=False)

        matched_rows = 0
        selected_chunks = []

        for chunk in pd.read_csv(src_edge, chunksize=self.chunksize):
            filtered = chunk[chunk['paperid'].isin(paper_ids)]

            if filtered.empty:
                continue

            selected_chunks.append(filtered)
            matched_rows += len(filtered)

            print(f"[INFO] Matched edges so far: {matched_rows}")

        print(f"[INFO] Total matched edges: {matched_rows}")

        # --------------------------------------------------
        # Step 3: 若超出目标规模，则随机下采样
        # --------------------------------------------------
        con2 = duckdb.connect(database=':memory:')
        total_au_papers = con2.execute(
            f"SELECT COUNT(*) FROM read_csv_auto('{src_edge}', header=true, strict_mode=false, ignore_errors=true)"
        ).fetchone()[0]
        con2.close()

        target_rows = int(total_au_papers * sample_ratio)

        print(f"[INFO] Number of original edges: {total_au_papers}")
        print(f"[INFO] Number of target edges (~{sample_ratio*100:.0f}%): {target_rows}")

        np.random.seed(self.seed)

        final_rows = 0

        if matched_rows <= target_rows:
            print("[INFO] Matched rows within target scale. Writing all.")
            for df in selected_chunks:
                df.to_csv(dst_edge, mode='a', index=False, header=False)
            final_rows = matched_rows
        else:
            print("[INFO] Matched rows exceed target scale. Randomly sampling...")

            # 合并后一次性采样（只在内存可承受时推荐）
            all_selected = pd.concat(selected_chunks, ignore_index=True)

            sampled = all_selected.sample(
                n=target_rows,
                random_state=self.seed
            )

            sampled.to_csv(
                dst_edge,
                mode='a',
                index=False,
                header=False
            )

            final_rows = len(sampled)

        print(f"[INFO] Final edges written: {final_rows}")
        print("Done.\n")


    # public tool: given specific in-edge, sample subset from the target vertex
    def get_target_vertex(self, in_edge, src_vertex, dst_vertex, vertex_id, sample_ratio):

        print("[Step 1] Collecting unique IDs from in-edges...")

        os.makedirs(os.path.dirname(dst_vertex), exist_ok=True)

        if os.path.exists(dst_vertex):
            os.remove(dst_vertex)

        con = duckdb.connect(database=':memory:')

        vertex_ids = set(
            aid[0] for aid in con.execute(
                f"""
                SELECT DISTINCT {vertex_id}
                FROM read_csv_auto(
                    '{in_edge}',
                    strict_mode=false,
                    ignore_errors=true
                )
                """
            ).fetchall()
        )

        print(f"[INFO] Number of unique vertex id: {len(vertex_ids)}")

        print("[Step 2] Extracting matched vertices...")

        header = pd.read_csv(src_vertex, nrows=0)
        header.to_csv(dst_vertex, index=False)

        extracted = 0
        written_vertex_ids = set()

        for chunk in pd.read_csv(src_vertex, chunksize=self.chunksize):
            filtered = chunk[chunk[vertex_id].isin(vertex_ids)]

            if filtered.empty:
                continue

            filtered.to_csv(
                dst_vertex,
                mode='a',
                index=False,
                header=False
            )

            written_vertex_ids.update(filtered[vertex_id])
            extracted += len(filtered)

            print(f"[Progress] Number of extracted vertices: {extracted}")

        print(f"[INFO] Step 2 done. Current rows: {extracted}")

        # --------------------------------------------------
        # Step 3: 若 author 数量不足，则随机补齐
        # --------------------------------------------------
        print("[Step 3] Checking target vertex scale...")

        con2 = duckdb.connect(database=':memory:')
        total_authors = con2.execute(
            f"""
            SELECT COUNT(*)
            FROM read_csv_auto(
                '{src_vertex}',
                strict_mode=false,
                ignore_errors=true
            )
            """
        ).fetchone()[0]
        con2.close()

        target_authors = int(total_authors * sample_ratio)

        print(f"[INFO] Total source vertices: {total_authors}")
        print(f"[INFO] Target rows (~{sample_ratio*100:.0f}%): {target_authors}")

        if extracted >= target_authors:
            print("[INFO] Already reached target vertex scale.")
            print(f"[INFO] Final vertex number: {extracted}")
            print("Done.\n")
            return

        remaining_needed = target_authors - extracted
        print(f"[INFO] Need to append {remaining_needed} additional vertices.")

        np.random.seed(self.seed)

        appended = 0

        for chunk in pd.read_csv(src_vertex, chunksize=self.chunksize):
            candidates = chunk[~chunk[vertex_id].isin(written_vertex_ids)]

            if candidates.empty:
                continue

            sample_prob = remaining_needed / total_authors
            sampled = candidates[np.random.rand(len(candidates)) < sample_prob]

            if sampled.empty:
                continue

            if appended + len(sampled) > remaining_needed:
                sampled = sampled.iloc[: remaining_needed - appended]

            sampled.to_csv(
                dst_vertex,
                mode='a',
                index=False,
                header=False
            )

            written_vertex_ids.update(sampled[vertex_id])
            appended += len(sampled)

            print(f"[Progress] Appended vertices so far: {appended}")

            if appended >= remaining_needed:
                break

        print(f"Final vertex number: {extracted + appended}")
        print("Done.\n")


    # public tool: given a source table, sample subset from another joinable table
    def get_table(self, table1, src_table2, dst_table2, join_key, sample_ratio):

        os.makedirs(os.path.dirname(dst_table2), exist_ok=True)

        if os.path.exists(dst_table2):
            os.remove(dst_table2)

        con = duckdb.connect(database=':memory:')

        seed_str = str(self.seed)
        bucket_num = 1000 * 10**self.target_scale
        threshold = int(sample_ratio * bucket_num)

        def csv(path):
            return f"""
            read_csv_auto(
                '{path}',
                header=true,
                strict_mode=false,
                ignore_errors=true
            )
            """

        print("[Step 1] Sampling joinable and non-joinable tuples...")

        joinable_cte = f"""
            SELECT t2.*
            FROM {csv(src_table2)} t2
            SEMI JOIN {csv(table1)} t1
            ON t2.{join_key} = t1.{join_key}
            WHERE (
                abs(hash(CAST(t2.{join_key} AS VARCHAR) || '{seed_str}'))
                % {bucket_num}
            ) < {threshold}
        """

        non_joinable_cte = f"""
            SELECT t2.*
            FROM {csv(src_table2)} t2
            ANTI JOIN {csv(table1)} t1
            ON t2.{join_key} = t1.{join_key}
            WHERE (
                abs(hash(CAST(t2.{join_key} AS VARCHAR) || '{seed_str}'))
                % {bucket_num}
            ) < {threshold}
        """

        joinable_count = con.execute(
            f"SELECT COUNT(*) FROM ({joinable_cte})"
        ).fetchone()[0]

        non_joinable_count = con.execute(
            f"SELECT COUNT(*) FROM ({non_joinable_cte})"
        ).fetchone()[0]

        total_written = joinable_count + non_joinable_count

        print(f"[INFO] Joinable tuples     : {joinable_count}")
        print(f"[INFO] Non-joinable tuples : {non_joinable_count}")
        print(f"[INFO] Total to write      : {total_written}")

        print("[Step 2] Writing output...")

        con.execute(f"""
            COPY (
                {joinable_cte}
                UNION ALL
                {non_joinable_cte}
            )
            TO '{dst_table2}'
            (HEADER, DELIMITER ',');
        """)

        con.close()

        print(f"[INFO] Output written to: {dst_table2}")
        print("Done.\n")
